import argparse
import ctypes
import json
import time
from pathlib import Path
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('--seconds', type=float, default=600)
parser.add_argument('--beta', type=float, default=0.5)
parser.add_argument('--seed', type=int, default=10)
parser.add_argument('--mode', type=int, default=0)
parser.add_argument('--shift', type=float, default=0.0)
parser.add_argument('--restart', type=int, default=0)
parser.add_argument('--method', type=str, default='rrr')
parser.add_argument('--initial', type=str)
arguments = parser.parse_args()
root = Path(__file__).resolve().parent
participant = root.parent.parent / 'participant'
target = json.loads((participant / 'input/target.json').read_text())
expected = np.asarray(target['cyclic_autocorrelation'], dtype=np.int64)
size = len(expected)
mass = 1024
magnitudes = np.sqrt(np.maximum(np.fft.rfft(expected).real, 0))
library = ctypes.CDLL(str(root / 'projection.so'))
array_type = np.ctypeslib.ndpointer(dtype=np.float64, ndim=1, flags='C_CONTIGUOUS')
library.project.argtypes = [array_type, array_type, ctypes.c_int, ctypes.c_int, ctypes.c_double]
library.sparse_project.argtypes = [array_type, array_type, ctypes.c_int, ctypes.c_int, ctypes.c_double]
generator = np.random.default_rng(arguments.seed)
values = generator.normal(mass / size, 0.55, size)
if arguments.initial:
    values = np.load(arguments.initial).astype(float)
discrete = np.zeros(size)
started = time.monotonic()
last_report = started
best = float('inf')
recent_best = float('inf')
iteration = 0
prefix = root / f'run_{arguments.mode}_{arguments.beta}_{arguments.seed}'
def project_discrete(vector):
    vector = np.ascontiguousarray(vector)
    if arguments.mode >= 8:
        library.sparse_project(vector, discrete, size, 768, 2.0 if arguments.mode == 9 else 10.0)
    else:
        library.project(vector, discrete, size, arguments.mode, arguments.shift)
    return discrete

def project_fourier(vector):
    spectrum = np.fft.rfft(vector)
    spectrum *= magnitudes / np.maximum(np.abs(spectrum), 1e-30)
    spectrum[0] = mass
    return np.fft.irfft(spectrum, n=size)

while time.monotonic() - started < arguments.seconds:
    if arguments.method == 'swap':
        first = project_fourier(values)
        project_discrete(2 * first - values)
        difference = discrete - first
        values += arguments.beta * difference
    elif arguments.method == 'dm':
        first = project_fourier(values)
        first_discrete = project_discrete(values).copy()
        project_discrete((1 + 1 / arguments.beta) * first - values / arguments.beta)
        second = project_fourier((1 - 1 / arguments.beta) * first_discrete + values / arguments.beta)
        difference = discrete - second
        values += arguments.beta * difference
    else:
        project_discrete(values)
        second = project_fourier(2 * discrete - values)
        difference = second - discrete
        if arguments.method == 'raar':
            values = arguments.beta * (values + difference) + (1 - arguments.beta) * discrete
        else:
            values += arguments.beta * difference
    residual = float(difference @ difference)
    recent_best = min(recent_best, residual)
    if residual < best:
        best = residual
        np.save(str(prefix) + '_best.npy', values)
        np.save(str(prefix) + '_discrete.npy', discrete)
    if residual < 1e-6:
        candidate = np.rint(discrete).astype(np.int64)
        actual = np.rint(np.fft.irfft(np.abs(np.fft.rfft(candidate)) ** 2, n=size)).astype(np.int64)
        if np.array_equal(actual, expected) and not np.any(candidate * np.roll(candidate, 1)):
            (root / 'design.json').write_text(json.dumps({'schema_version': 1, 'a': candidate.tolist()}, separators=(',', ':')) + '\n')
            print('EXACT', iteration, time.monotonic() - started, flush=True)
            break
    iteration += 1
    now = time.monotonic()
    if now - last_report > 20:
        print(json.dumps({'iterations': iteration, 'seconds': now - started, 'best': best, 'recent': recent_best, 'residual': residual, 'mass': float(discrete.sum()), 'nonzero': int(np.count_nonzero(discrete)), 'mode': arguments.mode, 'beta': arguments.beta}), flush=True)
        np.save(str(prefix) + '_current.npy', values)
        last_report = now
        recent_best = float('inf')
    if arguments.restart and iteration % arguments.restart == 0:
        values = generator.normal(mass / size, 0.55, size)
print('FINISHED', iteration, best, time.monotonic() - started, flush=True)
