import sys
import json
from pathlib import Path

import numpy as np
from scipy.linalg import null_space
from scipy.optimize import linprog

ROOT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/numerical_evaluation_of_the_analytic_nlo_energy_energy_correlation__1801_03219/concept_2/participant')
sys.path.insert(0, str(ROOT / 'input'))
from problem import BINS, COLOR, FAMILIES, Kernel, basis, response, validate
from target import NODES, KWEIGHTS, GWEIGHTS, COMPANION_NODES, COMPANION_WEIGHTS
from local_api import measure

kernel = Kernel()
reference_nodes, reference_weights = np.polynomial.legendre.leggauss(80)


def quadrature(witness, left, right, nodes, weights):
    points = (left + right) / 2 + (right - left) / 2 * nodes
    lower, upper = BINS[witness['bin']]
    values = 2 * (upper - lower) * COLOR * kernel(lower + (upper - lower) * points)
    values *= response(points, witness)[:, None]
    return np.einsum('n,nc,nj->cj', (right - left) / 2 * weights, values, basis(points, witness))


def matrices(witness, index):
    left, right = index / 8, (index + 1) / 8
    coarse_left, coarse_right = (index // 2) / 4, (index // 2 + 1) / 4
    middle = (coarse_left + coarse_right) / 2
    kronrod = quadrature(witness, left, right, NODES, KWEIGHTS)
    embedded = kronrod - quadrature(witness, left, right, NODES, GWEIGHTS)
    guard = kronrod - quadrature(witness, left, right, COMPANION_NODES, COMPANION_WEIGHTS)
    discrepancy = (quadrature(witness, coarse_left, middle, NODES, KWEIGHTS)
                   + quadrature(witness, middle, coarse_right, NODES, KWEIGHTS)
                   - quadrature(witness, coarse_left, coarse_right, NODES, KWEIGHTS))
    actual = kronrod - quadrature(witness, left, right, reference_nodes, reference_weights)
    constraints = np.concatenate([embedded, guard, discrepancy])
    return constraints, actual


def integer_witness(witness, coefficients):
    coefficients = coefficients / np.abs(coefficients).sum()
    integers = np.rint(coefficients * (10**10 - 24)).astype(np.int64)
    result = dict(witness, cosine=integers[:12].tolist(), sine=integers[12:].tolist())
    validate(result)
    return result


def main():
    candidates = []
    for name in BINS:
        witness = dict(version=1, bin=name, band_start=53, tilt=-1, curvature=-4)
        for index in range(8):
            constraints, actual = matrices(witness, index)
            scaled = constraints / np.linalg.norm(constraints, axis=1)[:, None]
            null = null_space(scaled, rcond=1e-13)
            for family in range(3):
                coefficients = null @ (null.T @ actual[family])
                result = integer_witness(witness, coefficients)
                coefficients = np.array(result['cosine'] + result['sine']) / 1e10
                predicted = actual @ coefficients
                residual = constraints @ coefficients
                candidates.append((min(abs(predicted)), result, index, predicted, max(abs(residual))))
    candidates.sort(key=lambda entry: entry[0], reverse=True)
    best = -1
    for number, (score, witness, index, predicted, residual) in enumerate(candidates):
        report = measure(witness, trace=True, kernel=kernel)
        margin = report['worst_screen_margin']
        details = [(family, entry['target']['panels'], entry['screen_error'], entry['target']['estimated_error'], entry['screen_margin']) for family, entry in report['families'].items()]
        print(number, witness['bin'], index, 'pred', predicted, 'residual', residual, 'margin', margin, details, flush=True)
        if margin > best:
            best = margin
            Path('witness.json').write_text(json.dumps(witness, indent=2) + '\n')
            Path('report.json').write_text(json.dumps(report, indent=2) + '\n')
        if margin > 10:
            break


if __name__ == '__main__':
    main()
