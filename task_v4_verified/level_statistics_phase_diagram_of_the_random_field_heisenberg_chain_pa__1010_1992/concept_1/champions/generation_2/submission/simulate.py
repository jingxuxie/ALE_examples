import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'
import json
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from generators import sample_fields, FAMILIES
from physics import observables


def simulate(index):
    rng = np.random.default_rng(72942301 + index * 771)
    family = FAMILIES[index % 4]
    fields = sample_fields(rng, 14, family)
    started = time.monotonic()
    result = observables(fields)
    return {'id': 'sim_' + str(index), 'L': 14, 'family': family,
            'fields': fields, 'f': result['f'],
            'seconds': time.monotonic() - started}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=1600)
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--offset', type=int, default=0)
    args = parser.parse_args()
    started = time.monotonic()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        with open('simulated.jsonl', 'a', buffering=1) as stream:
            for done, case in enumerate(pool.map(simulate, range(args.offset, args.offset + args.count))):
                stream.write(json.dumps(case) + '\n')
                if done % 8 == 0:
                    print(done + 1, round(time.monotonic() - started, 2), case['seconds'], flush=True)
