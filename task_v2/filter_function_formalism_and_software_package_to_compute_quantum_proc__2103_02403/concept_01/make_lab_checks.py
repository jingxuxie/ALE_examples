import csv
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / 'participant' / 'v_01'
WORKSPACE = PUBLIC / 'workspace'
sys.path[:0] = [str(WORKSPACE), str(WORKSPACE / 'deps')]
os.environ['OPENBLAS_NUM_THREADS'] = '1'

from diagnose import ensemble_check
from pipeline.physics import load_case


def main():
    rows = []
    for case_id in ('calibration_static', 'driven_static', 'switching_echo'):
        case, arrays = load_case(PUBLIC / 'input' / 'cases' / f'{case_id}.json')
        result = ensemble_check(case, arrays, batches=24, batch_size=512, max_step=0.015, seed=1907)
        rows.append(result)
        print(result, flush=True)
    with (PUBLIC / 'input' / 'lab_checks.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == '__main__':
    main()
