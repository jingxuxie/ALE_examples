from pathlib import Path
import os
import time
import numpy as np
import stim
import pymatching
from models import load_model

root = Path(os.environ['P'])
for path in sorted((root / 'input/cases').iterdir()):
    model = load_model(path)
    data = np.load(root / 'input/calibration' / (path.name + '.npz'))
    matcher = pymatching.Matching.from_detector_error_model(stim.DetectorErrorModel(model['dem_text']), enable_correlations=True)
    start = time.process_time()
    predictions = matcher.decode_batch(data['syndromes'], enable_correlations=True)
    wrong = np.any(predictions != data['labels'],axis=1)
    basewrong = np.any(data['baseline'] != data['labels'], axis=1)
    print(path.name, wrong.sum(), 'fix', (basewrong & ~wrong).sum(), 'spoil', (~basewrong & wrong).sum(), 'cpu',time.process_time()-start,flush=True)
