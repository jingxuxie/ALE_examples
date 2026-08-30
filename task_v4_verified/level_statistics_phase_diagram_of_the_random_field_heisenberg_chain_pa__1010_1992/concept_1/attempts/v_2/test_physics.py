import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[variable] = '1'
import json
from pathlib import Path
import time
import numpy as np
from fast_physics import prepare_sector, solve_fraction
from physics import observables


def main():
    cases = [json.loads(line) for line in Path('../../participant/input/validation.jsonl').read_text().splitlines()]
    cases = [case for case in cases if case['L'] == 10]
    sector = prepare_sector()
    started = time.monotonic()
    predictions = np.array([solve_fraction(case['fields'], sector) for case in cases])
    errors = predictions - [case['f'] for case in cases]
    report = dict(rmse=float(np.sqrt(np.mean(errors ** 2))), maximum_error=float(np.max(np.abs(errors))),
                  seconds=time.monotonic() - started)
    assert report['rmse'] < 0.001
    assert report['maximum_error'] < 0.003
    symmetry_errors = []
    for case in cases[:16]:
        fields = np.array(case['fields'])
        expected = observables(fields)['f']
        for transformed in (fields + 7.5, -fields, fields[::-1], np.roll(fields, 3)):
            original = transformed.copy()
            symmetry_errors.append(abs(solve_fraction(transformed, sector) - expected))
            assert np.array_equal(transformed, original)
    report['maximum_symmetry_error'] = max(symmetry_errors)
    assert report['maximum_symmetry_error'] < 0.003
    print(json.dumps(report, indent=2))
    Path('physics_checks.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
