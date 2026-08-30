import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import sys
import json
import time
import argparse
from pathlib import Path
from fractions import Fraction
from collections import Counter
import numpy as np
from numpy.polynomial import chebyshev as cheb

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'participant' / 'workspace'))
import guard

ROTATION = np.array([[1, -2, -2, -4], [2, 1, -4, 2], [2, 4, 1, -2], [4, -2, 2, 1]], dtype=np.int64)
QUANTUM = 40_000_000_000

def candidate(point, decoy, scale, rscale, coupling, order=1, highscale=0.0, depth=1.02e-7, decoy_order=2):
    point = Fraction(round(point * 10**9), 10**9)
    center = 2 * float(point) - 1
    decoy = 2 * decoy - 1
    quadratic = cheb.chebmul([-center, 1], [-center, 1]) * scale
    if order > 1:
        oscillation = np.zeros(order + 1)
        oscillation[-1] = 1
        oscillation[0] = -cheb.chebval(center, oscillation)
        quadratic = cheb.chebadd(quadratic, highscale * cheb.chebmul(oscillation, oscillation))
    quadratic[0] -= depth
    decoy_factor = cheb.chebpow([-decoy, 1], decoy_order)
    decoy_poly = cheb.chebmul(decoy_factor, decoy_factor) * rscale
    decoy_poly[0] += 1e-10
    length = max(len(quadratic), len(decoy_poly))
    spectral = np.zeros((length, 4, 4))
    spectral[:len(quadratic), 0, 0] = quadratic
    spectral[:len(decoy_poly), 2, 2] = decoy_poly
    spectral[:len(decoy_factor), 2, 3] = coupling * decoy_factor
    spectral[:len(decoy_factor), 3, 2] = coupling * decoy_factor
    integer = np.rint(spectral * QUANTUM).astype(np.int64)
    for degree, matrix in enumerate(integer):
        matrix[3, 3] = (QUANTUM if degree == 0 else 0) - sum(int(matrix[index, index]) for index in range(3))
    numerator = np.array([ROTATION @ matrix @ ROTATION.T for matrix in integer])
    return {'schema_version': 1, 'denominator': 25 * QUANTUM, 'coefficients': numerator.tolist(), 'x': str(point), 'vector': [str(Fraction(int(entry), 5)) for entry in ROTATION[:, 0]]}

def quick_valid(document):
    coefficients = np.asarray(document['coefficients'], dtype=float) / document['denominator']
    point = float(Fraction(document['x']))
    value = guard.evaluate_matrices(coefficients, [point])[0]
    vector = ROTATION[:, 0] / 5
    quotient = float(vector @ value @ vector)
    if quotient > -1e-7 or np.min(value.diagonal()) < .02:
        return False
    for left in range(4):
        for right in range(left + 1, 4):
            if value[left,left] * value[right,right] - value[left,right]**2 < 1e-5:
                return False
    first, second = guard.evaluate_matrices(coefficients, [.25, .75])
    if np.sum((first @ second - second @ first)**2) < 1e-8:
        return False
    if np.max(np.abs(coefficients)) > 1 or np.max(np.abs(coefficients).sum(axis=(0,2))) > 4:
        return False
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--trials', type=int, default=1000)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--order', type=int, default=1)
    arguments = parser.parse_args()
    random = np.random.default_rng(arguments.seed)
    mesh = np.unique(np.concatenate([guard._mesh(profile) for profile in guard.PROFILES]))
    centers = (mesh[:-1] + mesh[1:]) / 2
    distances = np.diff(mesh) / 2
    eligible = (centers >= .08) & (centers <= .92)
    centers, distances = centers[eligible], distances[eligible]
    order = np.argsort(distances)[::-1]
    centers, distances = centers[order], distances[order]
    print('mesh gaps', list(zip(centers[:10], distances[:10])), flush=True)
    best = -1
    stages = Counter()
    start = time.monotonic()
    for trial in range(arguments.trials):
        index = int(random.integers(min(150, len(centers))))
        point = centers[index]
        center = 2 * point - 1
        decoy = random.uniform(.1,.35) if point > .5 else random.uniform(.65,.9)
        scale = random.uniform(.2,.6) / (1 + abs(center))**2
        rscale = random.uniform(.08, .25) / (1 + abs(2 * decoy - 1))**4
        coupling = random.uniform(.005, .045)
        highscale = random.uniform(.015, .05) if arguments.order > 1 else 0
        if arguments.order > 1:
            scale *= .2
        document = candidate(point, decoy, scale, rscale, coupling, arguments.order, highscale)
        if not quick_valid(document):
            stages['inadmissible'] += 1
            continue
        coefficients = np.asarray(document['coefficients'],dtype=float)/document['denominator']
        reports = guard.screen_all(coefficients)
        accepted = sum(report['accepted'] for report in reports)
        stages.update(report.get('last_stage', report.get('failure')) for report in reports if not report['accepted'])
        if accepted > best:
            best = accepted
            Path('witness.json').write_text(json.dumps(document, separators=(',', ':'))+'\n')
            Path('best_reports.json').write_text(json.dumps(reports,indent=2)+'\n')
            print('BEST', trial, accepted, 'params', point, decoy, scale, rscale, coupling, highscale, 'reports', reports, flush=True)
        if best == 3:
            break
        if trial % 100 == 0:
            print('progress',trial,'elapsed',time.monotonic()-start,'stages',dict(stages),flush=True)
    print('DONE', trial, best, 'elapsed',time.monotonic()-start,'stages',dict(stages),flush=True)

if __name__ == '__main__':
    main()
