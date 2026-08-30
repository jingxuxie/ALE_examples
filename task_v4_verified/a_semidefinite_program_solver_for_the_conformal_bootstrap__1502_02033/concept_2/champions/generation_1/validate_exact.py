import argparse
import itertools
import json
import re
from fractions import Fraction
from pathlib import Path


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, 'duplicate key'
        result[key] = value
    return result


def rational(text):
    assert isinstance(text, str)
    assert re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?', text)
    value = Fraction(text)
    assert str(value) == text
    assert abs(value.numerator) <= 10**12
    assert value.denominator <= 10**12
    return value


def evaluate(coefficients, denominator, point):
    coordinate = 2 * point - 1
    basis = [Fraction(1), coordinate]
    for degree in range(2, len(coefficients)):
        basis.append(2 * coordinate * basis[-1] - basis[-2])
    return [
        [sum(matrix[row][column] * weight for matrix, weight in zip(coefficients, basis)) / denominator
         for column in range(4)]
        for row in range(4)
    ]


def multiply(left, right):
    return [[sum(left[row][index] * right[index][column] for index in range(4))
             for column in range(4)] for row in range(4)]


def describe(value):
    return {'exact': str(value), 'approximate': float(value)}


def validate(path):
    data = path.read_bytes()
    assert len(data) <= 65536
    document = json.loads(data.decode('utf-8'), object_pairs_hook=strict_object)
    assert set(document) == {'schema_version', 'denominator', 'coefficients', 'x', 'vector'}
    assert type(document['schema_version']) is int and document['schema_version'] == 1
    denominator = document['denominator']
    assert type(denominator) is int and 1 <= denominator <= 10**12
    coefficients = document['coefficients']
    assert type(coefficients) is list and 3 <= len(coefficients) <= 25
    for degree, matrix in enumerate(coefficients):
        assert type(matrix) is list and len(matrix) == 4
        assert all(type(row) is list and len(row) == 4 for row in matrix)
        assert all(type(entry) is int and abs(entry) <= denominator for row in matrix for entry in row)
        assert all(matrix[row][column] == matrix[column][row] for row in range(4) for column in range(4))
        assert sum(matrix[index][index] for index in range(4)) == (denominator if degree == 0 else 0)
    assert any(entry != 0 for row in coefficients[-1] for entry in row)
    row_bounds = [sum(abs(matrix[row][column]) for matrix in coefficients for column in range(4))
                  for row in range(4)]
    assert all(bound <= 4 * denominator for bound in row_bounds)
    point = rational(document['x'])
    assert Fraction(1, 20) <= point <= Fraction(19, 20)
    assert type(document['vector']) is list and len(document['vector']) == 4
    vector = [rational(entry) for entry in document['vector']]
    assert all(abs(entry) <= 1 for entry in vector)
    norm_squared = sum(entry**2 for entry in vector)
    assert Fraction(1, 4) <= norm_squared <= 4
    assert all(entry**2 >= norm_squared / 100 for entry in vector)
    value = evaluate(coefficients, denominator, point)
    diagonals = [value[index][index] for index in range(4)]
    assert min(diagonals) >= Fraction(1, 50)
    principal_minors = {
        f'{left},{right}': value[left][left] * value[right][right] - value[left][right]**2
        for left, right in itertools.combinations(range(4), 2)
    }
    assert min(principal_minors.values()) >= Fraction(1, 100000)
    first = evaluate(coefficients, denominator, Fraction(1, 4))
    second = evaluate(coefficients, denominator, Fraction(3, 4))
    forward = multiply(first, second)
    backward = multiply(second, first)
    commutator_squared = sum((forward[row][column] - backward[row][column])**2
                             for row in range(4) for column in range(4))
    assert commutator_squared >= Fraction(1, 10**8)
    quotient = sum(vector[row] * value[row][column] * vector[column]
                   for row in range(4) for column in range(4)) / norm_squared
    assert quotient <= -Fraction(1, 10**7)
    null_vector = [Fraction(entry, 5) for entry in (-2, 1, 4, -2)]
    common_null_vector = all(
        sum(matrix[row][column] * null_vector[column] for column in range(4)) == 0
        for matrix in coefficients for row in range(4)
    )
    eigenvector_at_point = all(
        sum(value[row][column] * vector[column] for column in range(4)) == quotient * vector[row]
        for row in range(4)
    )
    return {
        'valid': True,
        'evidence_valid': True,
        'bytes': len(data),
        'degree': len(coefficients) - 1,
        'denominator': denominator,
        'x': str(point),
        'vector': document['vector'],
        'vector_norm_squared': describe(norm_squared),
        'normalized_rayleigh_quotient': describe(quotient),
        'negativity_margin_beyond_required': describe(-quotient - Fraction(1, 10**7)),
        'diagonals': [describe(entry) for entry in diagonals],
        'principal_minors': {key: describe(entry) for key, entry in principal_minors.items()},
        'commutator_squared_frobenius_norm': describe(commutator_squared),
        'coefficient_row_sums': [describe(Fraction(bound, denominator)) for bound in row_bounds],
        'common_null_vector': [str(entry) for entry in null_vector] if common_null_vector else None,
        'witness_is_exact_eigenvector': eigenvector_at_point,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('witness', nargs='?', default='witness.json')
    parser.add_argument('--output', default='exact_validation.json')
    arguments = parser.parse_args()
    report = validate(Path(arguments.witness))
    Path(arguments.output).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
