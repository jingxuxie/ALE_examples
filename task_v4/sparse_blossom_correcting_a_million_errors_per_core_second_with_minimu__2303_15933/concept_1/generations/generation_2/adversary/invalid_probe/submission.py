import numpy as np


class Decoder:
    def __init__(self, model):
        self.model = model

    def decode(self, syndromes):
        return np.full((len(syndromes), 4), 2, dtype=np.uint8)
