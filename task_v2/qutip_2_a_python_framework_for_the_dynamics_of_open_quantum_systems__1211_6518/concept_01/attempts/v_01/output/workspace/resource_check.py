import json
import sys
from pathlib import Path

import numpy as np

from oqs.diagnostics import distance
from oqs.experiment import isolated_run, write_table
from oqs.studies import oscillator, random_basis, rotate


def main():
    destination = Path(sys.argv[1])
    configurations = json.loads((Path(__file__).parent / 'configs.json').read_text())
    dimension = 112
    case = oscillator(dimension)
    basis = random_basis(dimension)
    rotated = rotate(case, basis)
    rows = []
    reference, metrics = isolated_run(case, destination / 'unrotated_refined', configurations['refined'], 'unrotated_refined')
    variants = [('original', dict(configurations['production'], frobenius_atol=False)),
                ('scaled_atol', configurations['production']),
                ('step_limit', dict(configurations['production'], frobenius_atol=False, max_step=0.025)),
                ('refined', configurations['refined'])]
    for label, options in variants:
        raw, metrics = isolated_run(rotated, destination / label, options, label)
        unrotated = dict(raw, states=basis.conj().T @ raw['states'] @ basis)
        errors = np.linalg.norm(unrotated['states'] - reference['states'], axis=(1, 2))
        rows.append({'row_id': label, **metrics, 'distance_to_reference': distance(unrotated, reference),
                     'worst_time': float(case['times'][np.argmax(errors)]), 'final_error': float(errors[-1])})
    write_table(destination / 'comparison.csv', rows)
    for row in rows:
        print(row['row_id'], row['distance_to_reference'], row['wall_seconds'], row['hermiticity_error'])


if __name__ == '__main__':
    main()
