import csv
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'concept_01/solution/v_01'))
from qualification.model import load_case, MU0
from certified import solve


def main():
    case = load_case(ROOT / 'concept_01/evaluator/public_input/dev_ring.npz')
    material = case.lambdas > 0
    inner, outer = 0.7, 2.4
    rows = list(csv.reader((ROOT / 'source/supplement/examples/data/brandt_clem_2005_fig2.csv').open()))[2:]
    records = []
    for column, ratio in [(2, 0.01), (4, 0.03), (6, 0.10), (8, 0.30)]:
        data = np.array([[float(row[column]), float(row[column + 1])] for row in rows if row[column] and row[column + 1]])
        data = data[np.argsort(data[:, 0])]
        target = np.interp(inner / outer, data[:, 0], data[:, 1])
        case.lambdas[material] = ratio * outer
        prediction = solve(case)['inductance'][0, 0] / (MU0 * inner)
        records.append({'Lambda_over_b': ratio, 'a_over_b': inner / outer,
                        'digitized_L_over_mu0a': float(target), 'resolved_L_over_mu0a': float(prediction),
                        'relative_error': float(abs(prediction - target) / target)})
    case.lambdas[material] = 1000
    analytic = 2 * np.pi * MU0 * 1000 / np.log(outer / inner)
    result = solve(case)['inductance'][0, 0]
    output = {'paper_inductance_digitized_comparison': records,
              'kinetic_annulus_limit': {'analytic_pH': float(analytic), 'resolved_pH': float(result),
                                       'relative_error': float(abs(result - analytic) / analytic)},
              'interpretation': 'Independent continuum checks; coarse P1 mesh error is separate from hidden quadrature/operator error.'}
    (ROOT / 'concept_01/solution/v_01/paper_limit_checks.json').write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
