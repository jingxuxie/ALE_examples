import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import concurrent.futures
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.optimize import linprog
from search import ROOT, SPEC, witness, waveforms, compare, compute_validation


def evaluate_angles(angles):
    result = compare(angles)
    return [result['mps'][str(chi)]['zz1'] for chi in (4, 8, 16)] + [result['exact']['zz1']]


def full_check(candidate):
    return compute_validation(candidate, workers=1)


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else 'witness.json'
    candidate = json.loads((ROOT / input_path).read_text())
    knots = np.asarray(candidate['knots'])
    depth = candidate['depth']
    increment = 2e-5
    reuse = '--reuse' in sys.argv
    cached = '--cached' in sys.argv
    if cached:
        data = np.load(ROOT / 'linear_data.npz')
        knots = data['knots']
        depth = int(data['depth'])
        candidate = witness(depth, knots)
    variants = [candidate]
    for index in range(0 if reuse else 6):
        perturbed = knots.copy()
        perturbed[index] += increment
        variants.append(witness(depth, perturbed))
    jobs = [] if cached else [angles for variant in variants for angles in waveforms(variant, SPEC).values()]
    start = time.time()
    outputs = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
        for index, output in enumerate(pool.map(evaluate_angles, jobs)):
            outputs.append(output)
            if (index + 1) % 325 == 0:
                print('gradient', (index + 1) // 325, 'elapsed', time.time()-start, flush=True)
    outputs = np.load(ROOT / 'linear_data.npz')['outputs'] if cached else np.asarray(outputs).reshape(len(variants), 325, 4)
    if reuse:
        previous = np.load(ROOT / 'linear_data.npz')
        old_outputs = previous['outputs']
        jacobian = np.moveaxis((old_outputs[1:] - old_outputs[0]) / previous['increment'], 0, -1)
        displacement = knots - previous['knots']
        if np.linalg.norm(displacement) > 1e-12:
            residual = outputs[0] - old_outputs[0] - np.einsum('fok,k->fo', jacobian, displacement)
            jacobian += residual[:, :, None] * displacement / np.dot(displacement, displacement)
        outputs = np.concatenate((outputs, outputs + increment * np.moveaxis(jacobian, -1, 0)))
    else:
        jacobian = np.moveaxis((outputs[1:] - outputs[0]) / increment, 0, -1)
    np.savez(ROOT / 'linear_data.npz', outputs=outputs, knots=knots, depth=depth, increment=increment)
    values = outputs[0]
    matrix, bounds = [], []
    for index in range(325):
        for bond in range(2):
            difference = values[index, bond+1] - values[index, bond]
            gradient = jacobian[index, bond+1] - jacobian[index, bond]
            for sign in (-1, 1):
                matrix.append(np.r_[sign * gradient, 0.008])
                bounds.append(0.008 - sign * difference)
        error = values[index, 2] - values[index, 3]
        error_gradient = jacobian[index, 2] - jacobian[index, 3]
        sign = np.sign(error)
        matrix.append(np.r_[-sign * error_gradient, 0.15])
        bounds.append(abs(error) - 0.15)
    proposals = []
    radii = (0.003, 0.006, 0.012, 0.02) if cached else ((0.00003, 0.0001, 0.0003, 0.0007) if reuse else (0.0001, 0.0003, 0.0007, 0.0015))
    for radius in radii:
        result = linprog(np.r_[np.zeros(6), -1], A_ub=np.asarray(matrix), b_ub=np.asarray(bounds),
                         bounds=[(-radius, radius)]*6 + [(-10, 1)], method='highs', options={'threads': 1})
        if result.success:
            proposal = witness(depth, knots + result.x[:6])
            proposals.append(proposal)
            print(json.dumps(dict(radius=radius, predicted_margin=result.x[-1], proposal=proposal)), flush=True)
    (ROOT / 'linear_proposals.json').write_text(json.dumps(proposals))
    if '--propose-only' in sys.argv:
        return
    if '--single' in sys.argv:
        reports = [compute_validation(proposals[-1], workers=4)]
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
            reports = list(pool.map(full_check, proposals))
    reports.sort(key=lambda report: report['worst']['margin'], reverse=True)
    (ROOT / 'linear_validation.json').write_text(json.dumps(reports[0], indent=2) + '\n')
    (ROOT / 'linear_results.json').write_text(json.dumps(reports))
    (ROOT / 'witness.json').write_text(json.dumps(reports[0]['witness']) + '\n')
    for report in reports:
        print(json.dumps({key: value for key, value in report.items() if key != 'worst_cases'}), flush=True)


if __name__ == '__main__':
    main()
