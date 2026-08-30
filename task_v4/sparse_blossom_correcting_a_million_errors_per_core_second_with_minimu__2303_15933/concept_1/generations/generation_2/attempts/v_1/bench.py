import os
import sys
import time
import importlib
from pathlib import Path
import numpy as np
from models import load_model, sample_model

module = importlib.import_module(sys.argv[1] if len(sys.argv)>1 else 'submission')
root = Path(os.environ['P'])
total = np.zeros(5)
for path in sorted((root/'input/calibration').glob('*.npz')):
    if os.getenv('CASE') and os.getenv('CASE') not in path.stem:
        continue
    model = load_model(root/'input/cases'/path.stem)
    if os.getenv('SEED'):
        cache = Path(f"data_{path.stem}_{os.getenv('SEED')}_{os.getenv('SHOTS','256')}.npz")
        if not cache.exists():
            syndromes, labels, _ = sample_model(model,int(os.getenv('SHOTS','256')),int(os.environ['SEED']))
            from baseline.submission import Decoder
            baseline = Decoder(model).decode(syndromes)
            np.savez(cache,syndromes=syndromes,labels=labels,baseline=baseline)
        data = np.load(cache)
    else:
        data = np.load(path)
    syndromes, labels, baseline = data['syndromes'],data['labels'],data['baseline']
    start = time.process_time()
    decoder = module.Decoder(model)
    pred = decoder.decode(syndromes)
    elapsed = time.process_time()-start
    bad = np.any(pred != labels,axis=1)
    old = np.any(baseline != labels,axis=1)
    row = [int(bad.sum()),int(old.sum()),int((old & ~bad).sum()),int((~old & bad).sum()),elapsed]
    print(path.stem, row, flush=True)
    total += row
    if os.getenv('SAVE'):
        np.savez(f"{os.environ['SAVE']}_{path.stem}.npz",pred=pred,**({'scores':decoder.scores} if hasattr(decoder,'scores') else {}))
print('TOTAL',total,flush=True)
