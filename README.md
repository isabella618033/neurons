<div align="center">

# **Neurons** <!-- omit in toc -->
[![Discord Chat](https://img.shields.io/discord/308323056592486420.svg)](https://discord.gg/3rUr6EcvbB)
[![PyPI version](https://badge.fury.io/py/bittensor.svg)](https://badge.fury.io/py/bittensor)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) 

---

### Opensource Bittensor Neurons <!-- omit in toc -->

[Discord](https://discord.gg/3rUr6EcvbB) • [Docs](https://app.gitbook.com/@opentensor/s/bittensor/) • [Network](https://www.bittensor.com/metagraph) • [Research](https://uploads-ssl.webflow.com/5cfe9427d35b15fd0afc4687/5fa940aea6a95b870067cf09_bittensor.pdf) • [Code](https://github.com/opentensor/neurons)

</div>

<div align="center">
Neurons is a set of fully contained p2p Bittensor neuron-miners which run seamlessly on any one of our core networks.
</div>

- [1. Install](#2-install)
- [3. Using Neurons](#3-using-bittensor)
  - [3.1. Bash](#31-bash)
  - [3.2. Python](#32-python)
  - [3.3. CLI](#33-cli)

## 1. Documentation

https://app.gitbook.com/@opentensor/s/bittensor/

## 2. Install
Through bittensor
```bash
$ python3 -m pip3 install bittensor
```
or from source
```bash
$ cd neurons
$ python3 -m pip3 install -e .
```

## 3. Using Neurons
From bash
```bash
$ python3 neurons/text/template_miner/main.py
```

From python
```python
>> import bittensor.neurons as neurons
>> neurons.text.template_miner.neuron().run()
```

From the cli.
```bash
$ btcli run 
```
