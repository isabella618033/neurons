#!/bin/python3
# The MIT License (MIT)
# Copyright © 2021 Yuma Rao

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
""" The Exodus base validator

Example:
    $ python miners/text/template_validator.py --logging.debug

"""
import argparse
import yaml
from types import SimpleNamespace
import bittensor
import math
import torch
import wandb
import datetime
import os
from termcolor import colored
from torch.nn.utils import clip_grad_norm_
import torch.nn.functional as F
from qqdm import qqdm, format_str
from torch.nn import TransformerEncoder, TransformerEncoderLayer
from loguru import logger; logger = logger.opt(colors=True)


def main( config , validator, subtensor, wallet, metagraph, dataset, device, uid,dendrite):
    config.to_defaults()

    # Subscribe validator.
    subtensor.serve (
        wallet = wallet,
        ip = bittensor.utils.networking.get_external_ip(),
        port = 8080,
        modality = 0,
        wait_for_inclusion = True,
        wait_for_finalization = False 
    )
    
    optimizer = torch.optim.SGD(
        [ {'params': validator.peer_weights, 'lr': config.miner.learning_rate_chain} ],
        lr = config.miner.learning_rate,
        momentum = config.miner.momentum,
    )
    if config.wandb.api_key != 'default':
        # Create wandb for telemetry.
        bittensor.wandb(
            config = config,
            cold_pubkey = wallet.coldkeypub.ss58_address,
            hot_pubkey = wallet.hotkey.ss58_address,
            root_dir = config.miner.full_path
        )

        wandb.watch( validator, log = 'all', log_freq = 50 )

    # Optionally resume.
    if config.miner.resume:
        try:
            validator.load_state_dict( torch.load("{}/validator.torch".format( config.miner.full_path ))['validator'], strict=False )
        except Exception as e:
            logger.error('Error reloading model: {} '.format(e))
    torch.save( { 'validator': validator.state_dict() }, "{}/validator.torch".format( config.miner.full_path ))

    # --- Run Forever.
    epoch = 0
    global_step = 0
    best_loss = math.inf
    ema_score_decay = 0.995
    ema_scores = torch.ones_like( validator.peer_weights ) * (1 / metagraph.n.item()) 

    while True:
    
        # --- Sync + reshape.      
        metagraph.sync().save()
        chain_growth = metagraph.n.item() - torch.numel( validator.peer_weights )
        validator.peer_weights = torch.nn.Parameter(torch.cat( [validator.peer_weights, torch.ones([chain_growth], dtype=torch.float32, requires_grad=True)])).to(device)
        ema_scores = torch.nn.Parameter(torch.cat( [ema_scores, torch.ones([chain_growth], dtype=torch.float32, requires_grad=True)])).to(device)

        # --- Run epoch.
        start_block = subtensor.get_current_block() + 1
        end_block = start_block + config.miner.blocks_per_epoch
        blocks = [ block for block in range(start_block, end_block) ]
        progress = qqdm( blocks, total=len(blocks), desc=format_str('white', f'Epoch'))

        # --- Reset the epoch logs
        total_epoch_score = torch.zeros(metagraph.n.item())
        total_epoch_loss = 0
        batch_count = 0
        
        for block in progress:
            
            # --- Training step.
            while block >= subtensor.get_current_block():
                loss, _ = validator( next( dataset ) )
                val_score = validator.scores()
                scores = torch.nn.functional.normalize ( torch.relu( val_score ), p=1, dim = 0 )
                loss.backward()
                clip_grad_norm_(validator.parameters(), config.miner.clip_gradients)
                optimizer.step()
                optimizer.zero_grad() 
                global_step += 1
                batch_count += 1
                total_epoch_score += scores.detach()
                total_epoch_loss += loss.item()
                ema_scores = ema_score_decay * ema_scores.detach() + (1 - ema_score_decay) * scores.detach()


            # --- Step logs.
            info = { 
                'epoch': epoch,
                'global_step': global_step,
                'start': start_block,
                'current': block,
                'end': start_block + config.miner.blocks_per_epoch,
                'loss': colored('{:.4f}'.format(loss.item()), 'green'), 
                'best': colored('{:.4f}'.format(best_loss), 'green'), 
                'stake': colored('{:.4f}'.format(metagraph.S[ uid ].item()), 'green'),
                'dividends': colored('{:.4f}'.format(metagraph.S[ uid ].item()), 'green')
            }
            
            for uid_i, score_i in enumerate(scores.tolist()):
                if score_i != 0:
                    color =  'green' if score_i - ema_scores[ uid_i ] > 0 else 'red'
                    info[ 'fi_' + str(uid_i) ] = colored('{:.4f}'.format( score_i ), color)
                    
                    weight_wo_norm = validator.peer_weights[uid_i]
                    info[ 'pw_' + str(uid_i) ] = colored('{:.4f}'.format( weight_wo_norm ), color)
            
            
            progress.set_infos( info )
        
        # --- End of epoch
        # --- Set mechanism weights.
        topk_scores, topk_uids = torch.topk( ema_scores.detach(), k = min(config.miner.n_topk_peer_weights, metagraph.n.item())  )
        subtensor.set_weights (
            uids = topk_uids,
            weights = topk_scores,
            wallet = wallet,
            wait_for_inclusion = False,
        )    

        # --- Log.
        metagraph.sync().save()
        epoch_loss = total_epoch_loss / batch_count
        epoch_score = total_epoch_score / batch_count
        
        wandb_data = {
            'stake': metagraph.S[ uid ].item(),
            'dividends': metagraph.D[ uid ].item(),
            'epoch_loss': epoch_loss
        } 

        norm_weights = F.softmax( validator.peer_weights.detach(), dim=0 )
        
        for uid_j in topk_uids.tolist():
            uid_str = str(uid_j).zfill(3)
            wandb_data[ f'fisher_ema uid: {uid_str}' ] = ema_scores[uid_j]
            wandb_data[ f'fisher_epoch_score uid: {uid_str}' ] = epoch_score[uid_j]
            wandb_data[ f'peer_norm_weight uid:{uid_str}' ] = norm_weights[uid_j]
            wandb_data[ f'peer_wo_norm_weight uid:{uid_str}' ] = validator.peer_weights.detach()[uid_j]
        
        
        if config.wandb.api_key != 'default':
            wandb_data_dend = dendrite.to_wandb()
            wandb.log( {**wandb_data, **wandb_data_dend} )

        # --- Save.
        if best_loss > epoch_loss : 
            best_loss = epoch_loss
            torch.save( { 'validator': validator.state_dict() }, "{}/validator.torch".format( config.miner.full_path ))
        epoch += 1

