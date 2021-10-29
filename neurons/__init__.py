# Bittensor neurons
__version__ = '0.0.0'
version_split = __version__.split(".")
__version_as_int__ = (100 * int(version_split[0])) + (10 * int(version_split[1])) + (1 * int(version_split[2]))

from neurons.text import template_miner,template_server,advanced_server,template_validator

__all_neurons__ =  { 'text_template': template_miner.neuron }
__text_neurons__ =  { 'text_template': template_miner.neuron }