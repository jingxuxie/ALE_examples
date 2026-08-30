import json
import math

import sympy as sp


def gram_lll(gram):
    dimension = gram.rows
    basis = sp.eye(dimension)

    def orthogonalize():
        current = basis.T * gram * basis
        mu = sp.zeros(dimension)
        norms = []
        for row in range(dimension):
            for column in range(row):
                mu[row, column] = (current[row, column] - sum(
                    mu[row, earlier] * mu[column, earlier] * norms[earlier]
                    for earlier in range(column))) / norms[column]
            norms.append(current[row, row] - sum(
                mu[row, earlier] ** 2 * norms[earlier] for earlier in range(row)))
        return mu, norms

    active = 1
    while active < dimension:
        mu, norms = orthogonalize()
        for earlier in reversed(range(active)):
            multiple = round(mu[active, earlier])
            if multiple:
                basis[:, active] -= multiple * basis[:, earlier]
                mu, norms = orthogonalize()
        if norms[active] >= (sp.Rational(3, 4) - mu[active, active - 1] ** 2) * norms[active - 1]:
            active += 1
        else:
            basis.col_swap(active, active - 1)
            active = max(1, active - 1)
    return basis


if __name__ == '__main__':
    instance = json.load(open('../../participant/input/instances.json'))['instances'][2]
    coefficients = [sp.Matrix(matrix) * 64 * 2 ** power
                    for power, matrix in enumerate(instance['coefficients'])]
    gram = sum(coefficients, sp.zeros(4))
    transform = gram_lll(gram)
    diagonal = (transform.T * gram * transform).diagonal()
    scales = [sp.Rational(2) ** round(math.log2(math.sqrt(200 / float(entry))))
              for entry in diagonal]
    transform *= sp.diag(*scales)
    print('T', transform)
    normalized = [transform.T * matrix * transform for matrix in coefficients]
    print('denominator', sp.ilcm(*[entry.q for matrix in normalized for entry in matrix]))
    print('max', max(abs(entry) for matrix in normalized for entry in matrix))
    print('P0', normalized[0])
    print('Pl', normalized[-1])
    print('Tinv', transform.inv())
    json.dump({'T': [[str(entry) for entry in row] for row in transform.tolist()],
               'coefficients': [[[str(entry) for entry in row] for row in matrix.tolist()]
                                for matrix in normalized]}, open('normalized3.json', 'w'))
