import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[variable] = '1'
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import time
import numpy as np
from benchmark_physics import exact


def refine(case):
    previous = case['f']
    case['f'] = exact(case['fields'], driver='evd', precision='float64')
    return case, case['f'] - previous


def main():
    cases = []
    for path in ('independent_validation10.jsonl', 'independent_validation.jsonl'):
        cases.extend(json.loads(line) for line in Path(path).read_text().splitlines())
    refined, differences = [], []
    started = time.monotonic()
    with ProcessPoolExecutor(max_workers=4) as executor:
        for index, (case, difference) in enumerate(executor.map(refine, cases, chunksize=8)):
            refined.append(case)
            differences.append(difference)
            if (index + 1) % 100 == 0:
                print(index + 1, time.monotonic() - started, flush=True)
    Path('fresh_validation.jsonl').write_text(''.join(json.dumps(case) + '\n' for case in refined))
    rng = np.random.default_rng(68411)
    for batch in range(5):
        selected = []
        for length in (10, 12):
            for family in sorted({case['family'] for case in refined}):
                group = [case for case in refined if case['L'] == length and case['family'] == family]
                selected.extend(group[batch * 40:(batch + 1) * 40])
        rng.shuffle(selected)
        assert len(selected) == 320
        Path(f'fresh_validation_{batch}.jsonl').write_text(''.join(json.dumps(case) + '\n' for case in selected))
    report = dict(cases=len(refined), single_precision_label_rmse=float(np.sqrt(np.mean(np.asarray(differences) ** 2))),
                  maximum_single_precision_label_error=float(np.max(np.abs(differences))),
                  seconds=time.monotonic() - started)
    Path('validation_precision.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
