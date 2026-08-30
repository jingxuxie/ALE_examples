import argparse
import os
from pathlib import Path
import time
import numpy as np
from models import load_model, sample_model
from submission import Decoder
if os.getenv('BASELINE'):
    from baseline.submission import Decoder

parser = argparse.ArgumentParser()
parser.add_argument('--shots', type=int, default=256)
parser.add_argument('--seed', type=int, default=0)
parser.add_argument('--case', default='')
parser.add_argument('--save', default='')
args = parser.parse_args()
root = Path(os.environ['P'])
total = np.zeros(4)
for path in sorted((root / 'input/cases').iterdir()):
    if args.case not in path.name:
        continue
    model = load_model(path)
    if args.seed:
        syndromes, labels, faults = sample_model(model, args.shots, args.seed)
        baseline = None
    else:
        data = np.load(root / 'input/calibration' / (path.name + '.npz'))
        syndromes, labels, baseline = [data[key][:args.shots] for key in ['syndromes', 'labels', 'baseline']]
    start = time.process_time()
    predictions = Decoder(model).decode(syndromes)
    elapsed = time.process_time() - start
    wrong = np.any(predictions != labels, axis=1)
    if baseline is not None:
        old_wrong = np.any(baseline != labels, axis=1)
        fixed = int((old_wrong & ~wrong).sum())
        spoiled = int((~old_wrong & wrong).sum())
    else:
        fixed = spoiled = 0
    print(path.name, 'fail', int(wrong.sum()), 'fixed', fixed, 'spoiled', spoiled, 'cpu', round(elapsed, 3), flush=True)
    total += [wrong.sum(), fixed, spoiled, elapsed]
    if args.save:
        np.savez(args.save + '_' + path.name + '.npz', predictions=predictions, labels=labels, syndromes=syndromes)
print('TOTAL', total, flush=True)
