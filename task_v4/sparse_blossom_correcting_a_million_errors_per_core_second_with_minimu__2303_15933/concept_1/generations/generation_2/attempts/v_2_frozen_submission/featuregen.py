import argparse
import ctypes
import os
import time
from pathlib import Path
import numpy as np
from models import load_model, sample_model
from submission import Decoder, _native, _ptr

parser = argparse.ArgumentParser()
parser.add_argument('--seed', type=int, default=0)
parser.add_argument('--shots', type=int, default=256)
parser.add_argument('--out', default='features')
args = parser.parse_args()
_native.run_features.argtypes = [_ptr, ctypes.c_int, _ptr, _ptr, _ptr, ctypes.c_int, ctypes.c_int, ctypes.c_int]
root = Path(os.environ['P'])
for path in sorted((root / 'input/cases').iterdir()):
    model = load_model(path)
    if args.seed:
        syndromes, labels, _ = sample_model(model, args.shots, args.seed)
    else:
        data = np.load(root/'input/calibration'/(path.name+'.npz'))
        syndromes, labels = data['syndromes'][:args.shots], data['labels'][:args.shots]
    start = time.process_time()
    decoder = Decoder(model)
    features = np.zeros((len(syndromes),16,12), dtype=np.float32)
    output = np.zeros((len(syndromes),4), dtype=np.uint8)
    _native.run_features(decoder.handle, len(syndromes), syndromes.ctypes.data, output.ctypes.data, features.ctypes.data,
                         decoder.iterations, decoder.order, decoder.trials)
    elapsed = time.process_time()-start
    np.savez(args.out+'_'+path.name+'.npz', features=features, labels=labels, predictions=output, cpu=elapsed)
    print(path.name, 'fail', np.any(output!=labels,axis=1).sum(), 'scored',np.any(features!=0,axis=(1,2)).sum(),'cpu',elapsed,flush=True)
