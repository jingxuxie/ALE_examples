import argparse
import json
import time
from pathlib import Path
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('--seconds', type=float, default=1200)
parser.add_argument('--seed', type=int, default=100)
parser.add_argument('--start', type=int, default=8)
parser.add_argument('--beta', type=float, default=0.5)
parser.add_argument('--level-seconds', type=float, default=60)
parser.add_argument('--initial', type=str)
parser.add_argument('--restart-iterations', type=int, default=10000)
arguments = parser.parse_args()
root = Path(__file__).resolve().parent
expected = np.asarray(json.loads((root.parent.parent / 'participant/input/target.json').read_text())['cyclic_autocorrelation'])
generator = np.random.default_rng(arguments.seed)
started = time.monotonic()
levels = {}
best_global = {}

def correlation(candidate):
    return np.rint(np.fft.irfft(np.abs(np.fft.rfft(candidate)) ** 2, n=len(candidate))).astype(np.int64)

def solve_level(size, lower):
    wanted = expected.reshape(-1, size).sum(axis=0)
    magnitudes = np.sqrt(np.maximum(np.fft.rfft(wanted).real, 0))
    upper = 8192 // size
    values = generator.normal(1024 / size, np.sqrt(1280 / size), size)
    if lower is not None:
        lower_spectrum = np.fft.rfft(lower)
        half = size // 2
        values[:half] += (lower - values[:half] - values[half:]) / 2
        values[half:] = lower - values[:half]
        lower_bound = np.maximum(0, lower - upper)
        upper_bound = np.minimum(upper, lower)
    best = float('inf')
    level_start = time.monotonic()
    iterations = 0
    while time.monotonic() - level_start < arguments.level_seconds and time.monotonic() - started < arguments.seconds:
        if lower is None:
            discrete = np.clip(np.rint(values), 0, upper)
        else:
            first = np.clip(np.rint((values[:half] - values[half:] + lower) / 2), lower_bound, upper_bound)
            discrete = np.concatenate([first, lower - first])
        spectrum = np.fft.rfft(2 * discrete - values)
        spectrum *= magnitudes / np.maximum(np.abs(spectrum), 1e-20)
        spectrum[0] = 1024
        if lower is not None:
            spectrum[::2] = lower_spectrum
        second = np.fft.irfft(spectrum, n=size)
        difference = second - discrete
        values += arguments.beta * difference
        residual = float(difference @ difference)
        if residual < best:
            best = residual
        iterations += 1
        if arguments.restart_iterations and iterations % arguments.restart_iterations == 0:
            values = generator.normal(1024 / size, np.sqrt(1280 / size), size)
            if lower is not None:
                values[:half] += (lower - values[:half] - values[half:]) / 2
                values[half:] = lower - values[:half]
        if residual < 1e-8:
            candidate = discrete.astype(np.int64)
            if np.array_equal(correlation(candidate), wanted):
                print('LEVEL EXACT', size, iterations, time.monotonic() - level_start, candidate.tolist() if size <= 16 else '', flush=True)
                np.save(root / f'fold_{size}_{arguments.seed}.npy', candidate)
                return candidate
        if iterations % 200000 == 0:
            print('LEVEL PROGRESS', size, iterations, best, time.monotonic() - level_start, flush=True)
    print('LEVEL FAILED', size, iterations, best, time.monotonic() - level_start, flush=True)
    return None

trial = 0
while time.monotonic() - started < arguments.seconds:
    trial += 1
    print('TRIAL', trial, time.monotonic() - started, flush=True)
    size = arguments.start
    lower = None
    if arguments.initial:
        candidates = np.load(arguments.initial)
        lower = candidates[generator.integers(len(candidates))].copy()
        size = len(lower) * 2
    while size <= 4096:
        candidate = solve_level(size, lower)
        if candidate is None:
            break
        levels[size] = candidate
        lower = candidate
        if size == 4096:
            if not np.any(candidate * np.roll(candidate, 1)):
                (root / 'design.json').write_text(json.dumps({'schema_version': 1, 'a': candidate.tolist()}, separators=(',', ':')) + '\n')
                print('EXACT DESIGN', flush=True)
                raise SystemExit
        size *= 2
print('FINISHED', time.monotonic() - started, flush=True)
