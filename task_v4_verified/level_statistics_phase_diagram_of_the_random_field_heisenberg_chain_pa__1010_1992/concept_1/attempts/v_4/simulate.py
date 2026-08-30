import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[variable] = '1'
import concurrent.futures
import json
import time
import numpy as np
from physics import observables
from generators import sample_fields, FAMILIES


def simulate(item):
    index, case = item
    started = time.monotonic()
    case['f'] = observables(case['fields'])['f']
    case['seconds'] = time.monotonic() - started
    return index, case


def main():
    rng = np.random.default_rng(280820261951)
    cases = []
    for index in range(1800):
        family = FAMILIES[int(rng.choice(4, p=[0.32, 0.18, 0.15, 0.35]))]
        cases.append({'id': f'simulation_{index:05d}', 'L': 14,
                      'family': family, 'fields': sample_fields(rng, 14, family)})
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        pending = [executor.submit(simulate, item) for item in enumerate(cases)]
        with open('simulated.jsonl', 'a', buffering=1) as stream:
            for count, future in enumerate(concurrent.futures.as_completed(pending)):
                index, case = future.result()
                stream.write(json.dumps(case) + '\n')
                if count % 20 == 0:
                    print(count + 1, index, case['seconds'], flush=True)


if __name__ == '__main__':
    main()
