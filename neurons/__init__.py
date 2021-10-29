# Bittensor neurons
__version__ = '0.0.0'
version_split = __version__.split(".")
__version_as_int__ = (100 * int(version_split[0])) + (10 * int(version_split[1])) + (1 * int(version_split[2]))

from neurons.text import template_miner,template_server,advanced_server,template_validator

__all_neurons__ =  { 'text_template_miner': template_miner.neuron, 
                     'text_template_validator': template_validator.neuron,
                     'text_template_server':template_server.neuron,
                     'text_advanced_server':advanced_server.neuron,}
__text_neurons__ =  { 'template_miner': template_miner.neuron, 
                     'template_validator': template_validator.neuron,
                     'template_server':template_server.neuron,
                     'advanced_server':advanced_server.neuron,}