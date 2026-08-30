import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import sys
import json
import time
from fractions import Fraction
from pathlib import Path
import numpy as np
from numpy.polynomial import chebyshev as cheb
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'participant' / 'workspace'))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'participant' / 'workspace'))
import guard
from baseline_search import ROTATION_NUMERATORS

OUTPUT = Path(__file__).resolve().parent
QUANTUM = 40_000_000_000

def package(spectral, point, direction=None):
    integers = np.rint(spectral * QUANTUM).astype(np.int64)
    for degree, matrix in enumerate(integers):
        matrix[3, 3] = (QUANTUM if degree == 0 else 0) - sum(int(matrix[index, index]) for index in range(3))
    numerators = np.array([ROTATION_NUMERATORS @ matrix @ ROTATION_NUMERATORS.T for matrix in integers], dtype=np.int64)
    if direction is None:
        direction = ROTATION_NUMERATORS[:, 0] / 5
    return {
        'schema_version': 1,
        'denominator': 25 * QUANTUM,
        'coefficients': numerators.tolist(),
        'x': str(Fraction(float(point)).limit_denominator(10**10)),
        'vector': [str(Fraction(float(entry)).limit_denominator(10**10)) for entry in direction],
    }

def unpack(document):
    return np.asarray(document['coefficients'], dtype=float) / document['denominator']

def package_rotated(spectral, point, rotation):
    spectral = spectral.copy()
    spectral[:,3,3] = -np.trace(spectral[:,:3,:3],axis1=1,axis2=2)
    spectral[0,3,3] += 1
    coefficients = rotation @ spectral @ rotation.T
    integers = np.rint(coefficients*10**12).astype(np.int64)
    for degree, matrix in enumerate(integers):
        matrix[3,3] = (10**12 if degree == 0 else 0)-sum(int(matrix[index,index]) for index in range(3))
        for row in range(4):
            for column in range(row):
                matrix[row,column] = matrix[column,row]
    return dict(schema_version=1,denominator=10**12,coefficients=integers.tolist(),x=str(Fraction(float(point)).limit_denominator(10**10)),vector=[str(Fraction(float(entry)).limit_denominator(10**10)) for entry in rotation[:,0]])

def describe(document, full=True):
    coefficients = unpack(document)
    point = float(Fraction(document['x']))
    matrix = guard.evaluate_matrices(coefficients, [point])[0]
    print('point', point, 'eigs', np.linalg.eigvalsh(matrix), flush=True)
    start = time.perf_counter()
    candidates = guard.determinant_candidates(coefficients)
    print('roots', len(candidates), 'near', sorted(candidates, key=lambda value: abs(value-point))[:10], 'time', time.perf_counter()-start, flush=True)
    if full:
        print(json.dumps(guard.screen_all(coefficients)), flush=True)
    return candidates

def simple(point=.432145, depth=1.1e-7, plateau=1e-8, tail=0):
    center = 2*point-1
    spectral = np.zeros((25 if tail else 3, 4, 4))
    square = cheb.chebmul([-center, 1], [-center, 1]) * .3
    square[0] -= depth
    spectral[:3, 0, 0] = square
    spectral[0, 1, 1] = plateau
    spectral[0, 2, 2] = .3
    spectral[1, 2, 2] = .01
    if tail:
        spectral[-1, 0, 0] = tail
    return package(spectral, point)

if __name__ == '__main__':
    for tail in [0, 2.5e-11, 1e-10, 1e-9, 1e-8]:
        print('TAIL', tail)
        describe(simple(tail=tail))
