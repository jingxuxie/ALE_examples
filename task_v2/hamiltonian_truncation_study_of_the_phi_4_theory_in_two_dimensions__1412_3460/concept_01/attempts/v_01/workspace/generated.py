import subprocess
import time
import os
from pathlib import Path

import numpy as np
from scipy import sparse


def generate(case, sector, cutoff, keys, directory, executable=None, momentum_window=1000000):
    started = time.perf_counter()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    prefix = directory / 'generated'
    config = directory / 'config.txt'
    executable = executable or os.environ.get('GENERATOR_EXE', Path(__file__).with_name('generate'))
    momentum = sector['momentum'] if sector['momentum'] is not None else 1000000
    parity = sector['parity'] if sector['parity'] is not None else -1
    config.write_text(f"{case['length']} {case['mass']} {int(case['boundary'] == 'antiperiodic')} {cutoff} "
                      f"{momentum} {parity} {len(keys)}\n" + ''.join(f'{degree} {transfer}\n' for degree, transfer in keys)
                      + f'{momentum_window}\n')
    subprocess.run([str(executable), str(config), str(prefix)], check=True, capture_output=True)
    with open(str(prefix) + '_basis.bin', 'rb') as handle:
        dimension, count_modes = np.fromfile(handle, dtype=np.int64, count=2)
        modes = np.fromfile(handle, dtype=np.int32, count=count_modes)
        energy = np.fromfile(handle, dtype=np.float64, count=dimension)
        occupations = np.fromfile(handle, dtype=np.uint8).reshape(dimension, count_modes)
    operators = {}
    for degree, transfer in keys:
        filename = Path(str(prefix) + f'_v{degree}_q{transfer}.bin')
        with filename.open('rb') as handle:
            nonzero = int(np.fromfile(handle, dtype=np.int64, count=1)[0])
            rows = np.fromfile(handle, dtype=np.int32, count=nonzero)
            columns = np.fromfile(handle, dtype=np.int32, count=nonzero)
            values = np.fromfile(handle, dtype=np.float64, count=nonzero)
        operators[(degree, transfer)] = sparse.coo_matrix((values, (rows, columns)), shape=(dimension, dimension)).tocsr()
        filename.unlink()
    return {'energy': energy, 'modes': modes, 'occupations': occupations, 'operators': operators,
            'generation_seconds': time.perf_counter() - started, 'generated_cutoff': cutoff}


def restrict(sector, cutoff):
    keep = np.flatnonzero(sector['energy'] <= cutoff + 1e-9)
    return {'energy': sector['energy'][keep], 'modes': sector['modes'],
            'occupations': sector['occupations'][keep],
            'operators': {key: operator[keep][:, keep] for key, operator in sector['operators'].items()}}
