import argparse
import ctypes
import json
from pathlib import Path
import time

import numpy as np


parser = argparse.ArgumentParser()
parser.add_argument('--seconds', type=float, default=120)
parser.add_argument('--seed', type=int, default=1)
parser.add_argument('--beta', type=float, default=0.5)
parser.add_argument('--mode', type=int, default=3)
parser.add_argument('--name', default='run')
parser.add_argument('--start')
parser.add_argument('--algorithm',default='rrr')
parser.add_argument('--blend',type=float,default=0)
parser.add_argument('--occupied',type=int,default=0)
parser.add_argument('--library',default='projection.so')
parser.add_argument('--group')
arguments = parser.parse_args()
root = Path(__file__).resolve().parent
target = json.loads((root / '../../participant/input/target.json').read_text())
expected = np.array(target['cyclic_autocorrelation'], dtype=np.int64)
size = len(expected)
magnitudes = np.sqrt(np.maximum(np.fft.rfft(expected).real, 0))
library = ctypes.CDLL(str(root / arguments.library))
array_type = np.ctypeslib.ndpointer(dtype=np.float64, ndim=1, flags='C_CONTIGUOUS')
library.project.argtypes = [array_type, array_type, ctypes.c_int, ctypes.c_int, ctypes.c_double, ctypes.c_double]
group_totals=None
if arguments.group:
    group_totals=np.load(arguments.group).astype(np.int32)
    group_spectrum=np.fft.rfft(group_totals)
    library.project_groups.argtypes=[array_type,array_type,np.ctypeslib.ndpointer(dtype=np.int32,ndim=1),ctypes.c_int,ctypes.c_int]
values = np.random.default_rng(arguments.seed).normal(0.25, 0.55, size)
if arguments.start:
    values = np.load(arguments.start)
discrete = np.zeros(size)
started = time.monotonic()
last_log = started
best_residual = float('inf')
iterations = 0
penalty_one = arguments.blend
penalty_two = arguments.occupied
while time.monotonic() - started < arguments.seconds:
    if arguments.algorithm == 'rrr':
        if group_totals is not None:
            library.project_groups(values,discrete,group_totals,len(group_totals),size)
        else:
            library.project(values, discrete, size, arguments.mode, penalty_one, penalty_two)
        spectrum = np.fft.rfft(2 * discrete - values)
        spectrum *= magnitudes / np.maximum(np.abs(spectrum), 1e-20)
        spectrum[0] = 1024
        if group_totals is not None:
            spectrum[::size//len(group_totals)]=group_spectrum
        second = np.fft.irfft(spectrum, n=size)
        difference = second - discrete
    else:
        spectrum = np.fft.rfft(values)
        spectrum *= magnitudes / np.maximum(np.abs(spectrum), 1e-20)
        spectrum[0] = 1024
        second = np.fft.irfft(spectrum, n=size)
        if arguments.algorithm == 'reverse':
            intermediate = 2 * second - values
            library.project(intermediate, discrete, size, arguments.mode, penalty_one, penalty_two)
            difference = discrete - second
        elif arguments.algorithm == 'dm':
            intermediate = (1 + 1 / arguments.beta) * second - values / arguments.beta
            library.project(intermediate, discrete, size, arguments.mode, penalty_one, penalty_two)
            temporary = np.empty(size)
            library.project(values, temporary, size, arguments.mode, penalty_one, penalty_two)
            spectrum = np.fft.rfft((1 - 1 / arguments.beta) * temporary + values / arguments.beta)
            spectrum *= magnitudes / np.maximum(np.abs(spectrum), 1e-20)
            spectrum[0] = 1024
            second = np.fft.irfft(spectrum, n=size)
            difference = discrete - second
    values += arguments.beta * difference
    residual = float(difference @ difference)
    if residual < best_residual:
        best_residual = residual
        best_values = values.copy()
        best_discrete = discrete.copy()
    iterations += 1
    now = time.monotonic()
    if now - last_log >= 10 or residual < 1e-8:
        print(json.dumps({'run': arguments.name, 'iterations': iterations, 'seconds': round(now-started, 1), 'residual': round(residual, 5), 'best': round(best_residual, 5), 'ones': int(np.count_nonzero(discrete == 1)), 'twos': int(np.count_nonzero(discrete == 2))}), flush=True)
        np.save(root / (arguments.name + '_state.npy'), values)
        np.save(root / (arguments.name + '_best.npy'), best_values)
        last_log = now
    if residual < 1e-8:
        candidate = np.rint(discrete).astype(np.int64)
        actual = np.rint(np.fft.irfft(np.abs(np.fft.rfft(candidate)) ** 2, n=size)).astype(np.int64)
        if np.array_equal(actual, expected) and not np.any(candidate * np.roll(candidate, 1)) and np.array_equal(np.bincount(candidate,minlength=3),[3328,512,256]):
            (root / 'design.json').write_text(json.dumps({'schema_version': 1, 'a': candidate.tolist()}, separators=(',', ':')) + '\n')
            print('EXACT SOLUTION', flush=True)
            break
np.save(root / (arguments.name + '_state.npy'), values)
np.save(root / (arguments.name + '_best.npy'), best_values)
np.save(root / (arguments.name + '_discrete.npy'), best_discrete)
