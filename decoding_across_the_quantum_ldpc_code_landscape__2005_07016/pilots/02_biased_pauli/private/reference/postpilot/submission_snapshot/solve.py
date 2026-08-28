import argparse
import ctypes
import os
from pathlib import Path
import subprocess

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import numpy as np


def native_library():
    directory = Path(__file__).resolve().parent
    library = directory / 'decoder.so'
    source = directory / 'decoder.cpp'
    if not library.exists() or library.stat().st_mtime < source.stat().st_mtime:
        temporary = directory / ('.decoder-%d.so' % os.getpid())
        try:
            subprocess.run(['g++', '-O3', '-std=c++17', '-shared', '-fPIC',
                            str(source), '-o', str(temporary)], check=True, cwd=directory)
            os.replace(temporary, library)
        finally:
            if temporary.exists():
                temporary.unlink()
    native = ctypes.CDLL(str(library))
    native.decode_batch.argtypes = [ctypes.c_int] * 4 + [ctypes.c_void_p] * 6 + [ctypes.c_int]
    native.decode_batch.restype = ctypes.c_int
    return native


def decode(case):
    hx = np.ascontiguousarray(case['base_hx'], dtype=np.uint8)
    hz = np.ascontiguousarray(case['base_hz'], dtype=np.uint8)
    frame = np.asarray(case['frame'], dtype=np.uint8)
    permutation = np.asarray(case['permutation'], dtype=np.int64)
    physical = np.asarray(case['pauli_probs'], dtype=np.float64)[permutation]
    size = len(frame)
    probabilities = np.empty((size, 4), dtype=np.float64)
    pauli_index = np.array([0, 1, 3, 2])
    for state in range(4):
        xbit, zbit = state & 1, state >> 1
        physical_x = (frame[:, 0, 0] * xbit) ^ (frame[:, 0, 1] * zbit)
        physical_z = (frame[:, 1, 0] * xbit) ^ (frame[:, 1, 1] * zbit)
        probabilities[:, state] = physical[np.arange(size), pauli_index[physical_x + 2 * physical_z]]
    syndromes = np.ascontiguousarray(case['syndrome'], dtype=np.uint8)
    canonical = np.zeros((len(syndromes), size), dtype=np.uint8)
    statistics = np.zeros(8, dtype=np.float64)
    native = native_library()
    mode = int(os.environ.get('DECODER_MODE', '100'))
    result = native.decode_batch(size, len(hx), len(hz), len(syndromes),
                                 hx.ctypes.data, hz.ctypes.data, probabilities.ctypes.data,
                                 syndromes.ctypes.data, canonical.ctypes.data,
                                 statistics.ctypes.data, mode)
    if result:
        raise RuntimeError('Native decoder failed: ' + str(result))
    canonical_x = canonical & 1
    canonical_z = canonical >> 1
    correction_x = np.empty_like(canonical)
    correction_z = np.empty_like(canonical)
    correction_x[:, permutation] = ((canonical_x * frame[:, 0, 0]) ^
                                    (canonical_z * frame[:, 0, 1]))
    correction_z[:, permutation] = ((canonical_x * frame[:, 1, 0]) ^
                                    (canonical_z * frame[:, 1, 1]))
    if os.environ.get('DECODER_STATS'):
        import sys
        print('decoder:', statistics.tolist(), file=sys.stderr)
    return correction_x, correction_z


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    with np.load(arguments.input, allow_pickle=False) as case:
        correction_x, correction_z = decode(case)
    with open(arguments.output, 'wb') as destination:
        np.savez_compressed(destination, correction_x=correction_x, correction_z=correction_z)


if __name__ == '__main__':
    main()
