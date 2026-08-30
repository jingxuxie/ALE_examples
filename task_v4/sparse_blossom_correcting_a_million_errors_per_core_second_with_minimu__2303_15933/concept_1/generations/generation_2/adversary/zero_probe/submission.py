import numpy as np


class Decoder:
    def __init__(self, model):
        self.model = model

    def decode(self, syndromes):
        return np.zeros((len(syndromes), 4), dtype=np.uint8)
