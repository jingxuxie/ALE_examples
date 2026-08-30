import stim
import pymatching
class Decoder:
    def __init__(self,model):
        self.matcher=pymatching.Matching.from_detector_error_model(stim.DetectorErrorModel(model['dem_text']),enable_correlations=True)
    def decode(self,syndromes):
        return self.matcher.decode_batch(syndromes,enable_correlations=True)
