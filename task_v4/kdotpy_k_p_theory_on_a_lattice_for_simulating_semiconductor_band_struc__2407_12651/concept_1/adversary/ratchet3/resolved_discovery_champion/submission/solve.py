import argparse
from concurrent.futures import ThreadPoolExecutor
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['BLIS_NUM_THREADS'] = '1'

import numpy as np


def load_atlas(directory):
    try:
        from atlas import Atlas
    except ImportError:
        here = Path(__file__).resolve()
        locations = [here.parent / 'workspace', here.parent.parent / 'workspace',
                     here.parents[2] / 'participant' / 'workspace',
                     Path(directory).resolve().parent.parent / 'workspace']
        for location in locations:
            if (location / 'atlas.py').is_file():
                sys.path.insert(0, str(location))
                break
        from atlas import Atlas
    return Atlas.load(directory)


def solve(directory, seconds=78.0):
    started = time.monotonic()
    atlas = load_atlas(directory)
    with np.load(Path(directory) / 'arrays.npz', allow_pickle=False) as archive:
        baseline = np.asarray(archive['baseline_choices'], dtype=np.int32)
    native_path = Path(__file__).resolve().with_name('optimizer.so')
    source_path = native_path.with_suffix('.cpp')
    if not native_path.exists():
        temporary_path = native_path.with_suffix('.building.so')
        subprocess.run(['g++', '-std=c++17', '-O3', '-DNDEBUG', '-shared', '-fPIC',
                        str(source_path), '-o', str(temporary_path)], check=True)
        temporary_path.replace(native_path)
    native = ctypes.CDLL(str(native_path))
    vertices = atlas.vertices
    factors = np.full((4 * vertices, 4), -1, dtype=np.int32)
    factors[:vertices, 0] = np.arange(vertices)
    factors[vertices:3 * vertices, :2] = atlas.edges
    factors[3 * vertices:] = atlas.plaquettes
    arities = np.array([1] * vertices + [2] * (2 * vertices) + [4] * vertices, dtype=np.int32)
    offsets = np.concatenate(([0], np.cumsum(4 ** arities))).astype(np.int32)
    losses = np.ascontiguousarray(np.concatenate([
        (atlas.unary / atlas.normalizers[:, None, None]).reshape(4, -1),
        (atlas.pair / atlas.normalizers[:, None, None, None]).reshape(4, -1),
        (atlas.face / atlas.normalizers[:, None, None, None, None, None]).reshape(4, -1)
    ], axis=1).T)
    flux = np.zeros_like(losses)
    flux[offsets[3 * vertices]:] = atlas.flux.reshape(4, -1).T
    valid = np.concatenate([
        np.ones(vertices * 4, dtype=np.uint8),
        (atlas.link_magnitude.min(axis=0).reshape(-1) >= atlas.minimum_link).astype(np.uint8),
        (np.abs(atlas.flux).max(axis=0).reshape(-1) <= np.pi - atlas.branch_margin).astype(np.uint8)
    ])
    fixed = np.zeros(vertices, dtype=np.int32)
    for vertex in atlas.anchors:
        fixed[vertex] = 1
    costs = np.ascontiguousarray(atlas.costs, dtype=np.int32)
    seeds = np.ascontiguousarray(np.stack([baseline, atlas.seed]), dtype=np.int32)
    weights = np.ascontiguousarray(atlas.mean_weight * atlas.weights / atlas.weights.sum())
    output = baseline.copy()
    pointer = ctypes.c_void_p
    native.optimize.argtypes = [ctypes.c_int, ctypes.c_int] + [pointer] * 11 + [ctypes.c_double, ctypes.c_uint64, pointer]
    arguments = [fixed, costs, factors, arities, offsets, losses, flux, valid, seeds,
                 weights, np.ascontiguousarray(atlas.targets, dtype=np.float64)]
    pointers = [array.ctypes.data for array in arguments]
    complete = False
    if seconds - (time.monotonic() - started) > 5:
        try:
            from bounds import relaxation
            bound = relaxation(atlas, min(12.0, (seconds - (time.monotonic() - started)) * 0.25))
        except Exception:
            bound = None
        if bound is not None:
            lower_bound, reduced, marginal = bound
            rounded = marginal.argmax(axis=1).astype(np.int32)
            rounded_score = atlas.score(rounded)
            if rounded_score['feasible']:
                if rounded_score['objective'] < atlas.score(output)['objective']:
                    output[:] = rounded
                complete = rounded_score['objective'] <= lower_bound + 1e-9
            seeds[0] = output
            native.refine.argtypes = [ctypes.c_int, ctypes.c_int] + [pointer] * 12 + [ctypes.c_double, ctypes.c_double, pointer]
            native.refine.restype = ctypes.c_int
            if not complete:
                remaining = seconds - (time.monotonic() - started)
                complete = native.refine(vertices, atlas.budget, *pointers, reduced.ctypes.data, lower_bound,
                                         max(0.05, remaining * 0.65), output.ctypes.data)
    if not complete and time.monotonic() - started < seconds:
        seeds[0] = output

        def search(worker):
            candidate = output.copy()
            native.optimize(vertices, atlas.budget, *pointers,
                            max(0.05, seconds - (time.monotonic() - started)),
                            314159265 + worker * 1000003, candidate.ctypes.data)
            return candidate

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(search, worker) for worker in range(1, 4)]
            candidates = [search(0)]
            candidates.extend(future.result() for future in futures)
        candidates.append(output)
        values = atlas.evaluate_many(np.array(candidates))
        selected = np.argmin(np.where(values['feasible'], values['objective'], np.inf))
        output = candidates[selected]
    result = atlas.score(output)
    base_result = atlas.score(baseline)
    if not result['feasible'] or result['objective'] > base_result['objective']:
        output = baseline
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--seconds', type=float, default=78.0)
    arguments = parser.parse_args()
    choices = solve(arguments.input, arguments.seconds)
    Path(arguments.output).write_text(json.dumps({'choices': choices.tolist()}) + '\n')


if __name__ == '__main__':
    main()
