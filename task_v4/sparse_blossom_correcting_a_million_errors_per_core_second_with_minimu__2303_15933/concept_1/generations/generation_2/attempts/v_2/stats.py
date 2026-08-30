import os
import time
from pathlib import Path
import numpy as np
from models import load_model, sample_model
from submission import Decoder, _native, _ptr
import ctypes
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--case', default='')
parser.add_argument('--shots', type=int, default=256)
parser.add_argument('--seed', type=int, default=0)
parser.add_argument('--out', default='stats')
args = parser.parse_args()
_native.run_stats.argtypes = [_ptr, ctypes.c_int, _ptr, _ptr, ctypes.c_int, ctypes.c_int, ctypes.c_int]
root = Path(os.environ['P'])
for path in sorted((root / 'input/cases').iterdir()):
    if args.case not in path.name:
        continue
    model = load_model(path)
    decoder = Decoder(model)
    if args.seed:
        syndromes, labels, _ = sample_model(model, args.shots, args.seed)
    else:
        data = np.load(root / 'input/calibration' / (path.name + '.npz'))
        syndromes, labels = data['syndromes'][:args.shots], data['labels'][:args.shots]
    stats = np.zeros((len(syndromes), decoder.trials, 33), dtype=np.float32)
    mc = np.zeros((len(syndromes), 16), dtype=np.float32)
    start = time.process_time()
    if os.getenv('MC'):
        _native.run_mc.argtypes = [_ptr, ctypes.c_int, _ptr, _ptr, _ptr, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        _native.run_mc(decoder.handle, len(syndromes), syndromes.ctypes.data, stats.ctypes.data, mc.ctypes.data,
                       decoder.iterations, decoder.order, decoder.trials)
    elif decoder.matcher is None:
        _native.run_stats(decoder.handle, len(syndromes), syndromes.ctypes.data, stats.ctypes.data,
                          decoder.iterations, decoder.order, decoder.trials)
    else:
        seeds = np.ascontiguousarray(decoder.matcher.decode_batch(syndromes, enable_correlations=True)[:, decoder.match_selected])
        output = np.empty((len(syndromes), 4), dtype=np.uint8)
        _native.run_seed.argtypes = [_ptr, ctypes.c_int, _ptr, _ptr, _ptr, _ptr, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        _native.run_seed(decoder.handle, len(syndromes), syndromes.ctypes.data, seeds.ctypes.data, output.ctypes.data, stats.ctypes.data,
                         decoder.iterations, decoder.order, decoder.trials)
    elapsed = time.process_time() - start
    truth = labels @ np.array([1,2,4,8])
    print(path.name, 'cpu', round(elapsed,2), 'sum', (stats[:,:,:16].argmax(axis=2) != truth[:,None]).sum(axis=0),
          'min', (stats[:,:,16:32].argmax(axis=2) != truth[:,None]).sum(axis=0), flush=True)
    if os.getenv('MC'):
        print('MC', (mc.argmax(1) != truth).sum(), flush=True)
    np.savez(args.out + '_' + path.name + '.npz', stats=stats, labels=labels, syndromes=syndromes, cpu=elapsed, mc=mc)
