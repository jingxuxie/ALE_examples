import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[variable] = '1'
import argparse
import json
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from benchmark_physics import exact
from generators import FAMILIES, sample_fields
from physics import sector


def initialize():
    sector(10)
    sector(12)


def label(case):
    case['f'] = exact(case['fields'], driver='evd', precision='float32')
    return case


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=6000)
    parser.add_argument('--seed', type=int, default=864290)
    parser.add_argument('--length', type=int, choices=(10, 12), default=12)
    parser.add_argument('--output', default='generated.jsonl')
    arguments = parser.parse_args()
    rng = np.random.default_rng(arguments.seed)
    cases = []
    for index in range(arguments.count):
        family = FAMILIES[index % len(FAMILIES)]
        cases.append(dict(id=f'generated_{arguments.seed}_{index}', L=arguments.length, family=family,
                          fields=sample_fields(rng, arguments.length, family)))
    started = time.monotonic()
    with Path(arguments.output).open('w') as stream, ProcessPoolExecutor(max_workers=4, initializer=initialize) as executor:
        for index, case in enumerate(executor.map(label, cases, chunksize=8)):
            stream.write(json.dumps(case) + '\n')
            if (index + 1) % 100 == 0:
                stream.flush()
                print(index + 1, 'seconds', time.monotonic() - started, flush=True)


if __name__ == '__main__':
    main()
