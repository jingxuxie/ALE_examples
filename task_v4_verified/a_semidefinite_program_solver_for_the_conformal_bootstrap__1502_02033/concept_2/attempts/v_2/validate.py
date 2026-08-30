import argparse
import itertools
import json
import re
from fractions import Fraction
from pathlib import Path

def evaluate(coefficients, denominator, point):
    coordinate = 2*point-1
    basis = [Fraction(1), coordinate]
    for degree in range(2, len(coefficients)):
        basis.append(2*coordinate*basis[-1]-basis[-2])
    return [[sum(Fraction(matrix[row][column], denominator)*basis[degree] for degree, matrix in enumerate(coefficients)) for column in range(4)] for row in range(4)]

def product(left, right):
    return [[sum(left[row][inner]*right[inner][column] for inner in range(4)) for column in range(4)] for row in range(4)]

def rational(value):
    assert isinstance(value, str)
    parsed = Fraction(value)
    assert str(parsed) == value
    assert abs(parsed.numerator) <= 10**12 and parsed.denominator <= 10**12
    return parsed

def validate(path):
    raw = Path(path).read_bytes()
    assert len(raw) <= 65536
    document = json.loads(raw)
    assert set(document) == {'schema_version', 'denominator', 'coefficients', 'x', 'vector'}
    assert type(document['schema_version']) is int and document['schema_version'] == 1
    denominator = document['denominator']
    assert type(denominator) is int and 1 <= denominator <= 10**12
    coefficients = document['coefficients']
    assert isinstance(coefficients, list) and 3 <= len(coefficients) <= 25
    for degree, matrix in enumerate(coefficients):
        assert isinstance(matrix, list) and len(matrix) == 4
        assert all(isinstance(row, list) and len(row) == 4 for row in matrix)
        for row in range(4):
            for column in range(4):
                assert type(matrix[row][column]) is int
                assert abs(matrix[row][column]) <= denominator
                assert matrix[row][column] == matrix[column][row]
        assert sum(matrix[index][index] for index in range(4)) == (denominator if degree == 0 else 0)
    assert any(entry for row in coefficients[-1] for entry in row)
    row_bounds = [sum(abs(matrix[row][column]) for matrix in coefficients for column in range(4)) for row in range(4)]
    assert max(row_bounds) <= 4*denominator
    point = rational(document['x'])
    assert Fraction(1, 20) <= point <= Fraction(19, 20)
    assert isinstance(document['vector'], list) and len(document['vector']) == 4
    vector = [rational(value) for value in document['vector']]
    norm = sum(value**2 for value in vector)
    assert all(abs(value) <= 1 for value in vector)
    assert Fraction(1, 4) <= norm <= 4
    assert all(value**2 >= norm/100 for value in vector)
    matrix = evaluate(coefficients, denominator, point)
    diagonal_min = min(matrix[index][index] for index in range(4))
    principal_min = min(matrix[left][left]*matrix[right][right]-matrix[left][right]**2 for left,right in itertools.combinations(range(4), 2))
    assert diagonal_min >= Fraction(1, 50), float(diagonal_min)
    assert principal_min >= Fraction(1, 100000), float(principal_min)
    first = evaluate(coefficients, denominator, Fraction(1, 4))
    second = evaluate(coefficients, denominator, Fraction(3, 4))
    forward = product(first, second)
    reverse = product(second, first)
    commutator = sum((forward[row][column]-reverse[row][column])**2 for row in range(4) for column in range(4))
    assert commutator >= Fraction(1, 10**8), float(commutator)
    quotient = sum(vector[row]*matrix[row][column]*vector[column] for row in range(4) for column in range(4))/norm
    result = dict(valid=True, evidence_valid=quotient <= -Fraction(1, 10**7), quotient=str(quotient), quotient_float=float(quotient), diagonal_min=float(diagonal_min), principal_two_min=float(principal_min), commutator_squared=float(commutator), row_bounds=[value/denominator for value in row_bounds], degree=len(coefficients)-1, bytes=len(raw))
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('witness')
    arguments = parser.parse_args()
    print(json.dumps(validate(arguments.witness), indent=2))
