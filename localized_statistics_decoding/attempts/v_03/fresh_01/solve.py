import argparse
import ctypes
import os
from pathlib import Path
import subprocess

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import numpy as np


def solve(data):
    root = Path(__file__).resolve().parent
    source = root / 'decoder.cpp'
    library = root / 'decoder.so'
    if not library.exists() or library.stat().st_mtime < source.stat().st_mtime:
        subprocess.run(['g++', '-O3', '-std=c++17', '-shared', '-fPIC', str(source),
                        '-o', str(library)], check=True)
    native = ctypes.CDLL(str(library))
    pointer = ctypes.c_void_p
    native.decode_batch.argtypes = [ctypes.c_int] * 4 + [pointer] * 7 + [ctypes.c_int] * 4 + [ctypes.c_double, ctypes.c_int]
    native.decode_batch.restype = ctypes.c_int
    matrix = np.ascontiguousarray(data['H'], dtype=np.uint8)
    logical = np.ascontiguousarray(data['L'], dtype=np.uint8)
    prior = np.ascontiguousarray(data['prior'], dtype=np.float64)
    syndromes = np.ascontiguousarray(data['syndrome'], dtype=np.uint8)
    soft = np.ascontiguousarray(data['soft_llr'], dtype=np.float64)
    frames, rows = syndromes.shape
    columns = matrix.shape[1]
    original_matrix = matrix
    original_syndromes = syndromes
    original_columns = columns
    signatures = np.packbits(np.concatenate((matrix, logical), axis=0).T, axis=1)
    duplicate_groups = {}
    for column, signature in enumerate(signatures):
        duplicate_groups.setdefault(signature.tobytes(), []).append(column)
    representatives = np.array([max(indices, key=lambda index: prior[index])
                                for indices in duplicate_groups.values()], dtype=np.int64)
    if len(representatives) < columns:
        effective_prior = np.array([-.5 * np.expm1(np.log1p(-2 * prior[indices]).sum())
                                    for indices in duplicate_groups.values()])
        matrix = np.ascontiguousarray(matrix[:, representatives])
        logical = np.ascontiguousarray(logical[:, representatives])
        soft = np.ascontiguousarray(soft[:, representatives])
        prior = effective_prior
        columns = len(representatives)
    _, unique_rows = np.unique(np.packbits(matrix, axis=1), axis=0, return_index=True)
    if len(unique_rows) < rows:
        unique_rows.sort()
        matrix = np.ascontiguousarray(matrix[unique_rows])
        syndromes = np.ascontiguousarray(syndromes[:, unique_rows])
        rows = len(unique_rows)
    output = np.zeros((frames, columns), dtype=np.uint8)
    diagnostics = np.zeros((frames, 5), dtype=np.float64)
    arrays = [matrix, logical, prior, syndromes, soft, output, diagnostics]
    groups = native.decode_batch(rows, columns, logical.shape[0], frames,
                                 *[array.ctypes.data for array in arrays],
                                 int(os.environ.get('DECODER_GROUPED', '1')),
                                 int(os.environ.get('DECODER_ATTEMPTS', '256')),
                                 int(os.environ.get('DECODER_ITERATIONS', '80')),
                                 int(os.environ.get('DECODER_DEPTH', '60')),
                                 float(os.environ.get('DECODER_SECONDS', str(min(1.85, 46.0 / max(1, frames))))),
                                 int(os.environ.get('DECODER_MODE', '3')))
    if groups < 0:
        raise RuntimeError('Native decoder failed')
    expanded = np.zeros((frames, original_columns), dtype=np.uint8)
    expanded[:, representatives] = output
    if not np.array_equal((expanded @ original_matrix.T) % 2, original_syndromes):
        raise RuntimeError('Decoder produced a nonzero syndrome residual')
    return {'correction': expanded, 'diagnostics': diagnostics,
            'groups': np.array(groups, dtype=np.int64)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    with np.load(arguments.input, allow_pickle=False) as data:
        predictions = solve(data)
    np.savez_compressed(arguments.output, **predictions)
