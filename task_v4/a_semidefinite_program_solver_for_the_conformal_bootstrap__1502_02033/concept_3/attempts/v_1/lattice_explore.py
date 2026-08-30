import json
import math
from fractions import Fraction

import numpy as np


def form(coefficients, degree, shift=0, samples=150):
    dimension = coefficients.shape[1]
    result = np.zeros((dimension * (degree + 1),) * 2)
    nodes = (np.arange(samples) + 0.5) / samples
    points = (np.tan(np.pi * nodes / 2)) ** 2
    for point in points:
        matrix = sum(matrix * point ** power for power, matrix in enumerate(coefficients))
        inverse = np.linalg.inv(matrix)
        monomials = point ** np.arange(degree + 1)
        result += np.kron(np.outer(monomials, monomials), inverse) * point ** shift / samples
    return result


if __name__ == '__main__':
    inputs = json.load(open('../../participant/input/instances.json'))['instances']
    for instance in inputs[:2]:
        columns = instance['dimension']
        coefficients = np.array([[[64 * float(Fraction(entry)) for entry in row]
                                  for row in matrix] for matrix in instance['coefficients']])
        if columns == 4:
            columns = 3
            coefficients = coefficients[:11, :3, :3]
        for degree, shift in [(len(coefficients)//2, 0), (len(coefficients)//2-1, 1)]:
            gram = form(coefficients, degree, shift)
            if shift == 0:
                gram = gram[columns:-columns, columns:-columns]
            sign, logdet = np.linalg.slogdet(gram)
            dimension = len(gram)
            logvolume = dimension/2*math.log(math.pi)-math.lgamma(dimension/2+1)-logdet/2
            print(instance['id'], degree, shift, 'dim', dimension,
                  'eig', np.linalg.eigvalsh(gram), 'log10count', logvolume/math.log(10), flush=True)
