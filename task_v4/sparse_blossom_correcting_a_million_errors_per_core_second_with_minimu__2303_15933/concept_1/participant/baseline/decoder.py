import numpy as np
import pymatching
import stim


class Decoder:
    def __init__(self, model):
        self.matching = pymatching.Matching.from_detector_error_model(
            stim.DetectorErrorModel(model["dem_text"]), enable_correlations=True
        )

    def decode(self, syndromes):
        return np.asarray(self.matching.decode_batch(syndromes, enable_correlations=True), dtype=np.uint8)
