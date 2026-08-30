import sys
from pathlib import Path

import numpy as np
import pymatching
import stim


def main():
    request = Path(sys.argv[1])
    model = stim.DetectorErrorModel.from_file(request / "model.dem")
    decoder = pymatching.Matching.from_detector_error_model(model, enable_correlations=True)
    syndromes = np.load(request / "syndromes.npy", allow_pickle=False)
    predictions = decoder.decode_batch(syndromes, enable_correlations=True)
    np.save(sys.argv[2], predictions[:, 0].astype(np.uint8), allow_pickle=False)


if __name__ == "__main__":
    main()
