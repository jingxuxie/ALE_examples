import numpy as np


class Decoder:
    def __init__(self, model):
        self.observables = model["num_observables"]

    def decode(self, syndromes):
        return np.zeros((len(syndromes), self.observables), dtype=np.uint8)
