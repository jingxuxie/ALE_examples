import json
import math
import os
import sys
from fractions import Fraction
from functools import reduce
from decimal import Decimal

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import mpmath as mp


def trim(polynomial):
    first = 0
    while first < len(polynomial) and polynomial[first] == 0:
        first += 1
    return polynomial[first:]


def primitive(polynomial):
    polynomial = trim(polynomial)
    if not polynomial:
        return []
    content = reduce(math.gcd, polynomial)
    if polynomial[0] < 0:
        content = -content
    return [coefficient // content for coefficient in polynomial]


def multiply(first, second):
    if not first or not second:
        return []
    result = [0] * (len(first) + len(second) - 1)
    for index, coefficient in enumerate(first):
        if coefficient:
            for offset, other in enumerate(second):
                result[index + offset] += coefficient * other
    return trim(result)


def subtract(first, second):
    size = max(len(first), len(second))
    result = [0] * size
    for index, coefficient in enumerate(first):
        result[index + size - len(first)] += coefficient
    for index, coefficient in enumerate(second):
        result[index + size - len(second)] -= coefficient
    return trim(result)


def modular_gcd(first, second, modulus):
    if first[0] % modulus == 0 or second[0] % modulus == 0:
        return None
    first = [coefficient % modulus for coefficient in first]
    second = [coefficient % modulus for coefficient in second]
    while second:
        inverse = pow(second[0], modulus - 2, modulus)
        remainder = first[:]
        for index in range(len(first) - len(second) + 1):
            factor = remainder[index] * inverse % modulus
            if factor:
                for offset, coefficient in enumerate(second):
                    remainder[index + offset] = (remainder[index + offset]
                                                  - factor * coefficient) % modulus
        first, second = second, trim(remainder)
    inverse = pow(first[0], modulus - 2, modulus)
    return [coefficient * inverse % modulus for coefficient in first]


PRIMES = [1000000007]


def is_prime(candidate):
    odd = candidate - 1
    powers = 0
    while odd % 2 == 0:
        powers += 1
        odd //= 2
    for base in (2, 3, 5, 7, 11):
        residue = pow(base, odd, candidate)
        if residue in (1, candidate - 1):
            continue
        for repeat in range(powers - 1):
            residue = residue * residue % candidate
            if residue == candidate - 1:
                break
        else:
            return False
    return True


def prime_at(index):
    while len(PRIMES) <= index:
        candidate = PRIMES[-1] - 2
        while not is_prime(candidate):
            candidate -= 2
        PRIMES.append(candidate)
    return PRIMES[index]


def polynomial_gcd(first, second):
    first, second = primitive(first), primitive(second)
    if len(first) < len(second):
        first, second = second, first
    if not second:
        return first
    if len(second) == 1:
        return [1]
    leading = math.gcd(first[0], second[0])
    residues = None
    modulus_product = 1
    best_degree = len(second)
    prime_index = 0
    while True:
        modulus = prime_at(prime_index)
        prime_index += 1
        modular = modular_gcd(first, second, modulus)
        if modular is None:
            continue
        degree = len(modular) - 1
        if degree == 0:
            return [1]
        if degree > best_degree:
            continue
        modular = [coefficient * leading % modulus for coefficient in modular[1:]]
        if degree < best_degree:
            best_degree = degree
            residues = modular
            modulus_product = modulus
        else:
            inverse = pow(modulus_product % modulus, modulus - 2, modulus)
            residues = [previous + modulus_product * ((value - previous) * inverse % modulus)
                        for previous, value in zip(residues, modular)]
            modulus_product *= modulus
        if modulus_product.bit_length() >= leading.bit_length() and prime_index % 3 == 0:
            midpoint = modulus_product // 2
            candidate = primitive([leading] + [value if value <= midpoint else value - modulus_product
                                                for value in residues])
            try:
                exact_quotient(first, candidate)
                exact_quotient(second, candidate)
                return candidate
            except ArithmeticError:
                pass


def exact_quotient(first, second):
    remainder = first[:]
    result = []
    for index in range(len(first) - len(second) + 1):
        coefficient, residue = divmod(remainder[index], second[0])
        if residue:
            raise ArithmeticError('Nonintegral polynomial division')
        result.append(coefficient)
        for offset, value in enumerate(second):
            remainder[index + offset] -= coefficient * value
    if any(remainder):
        raise ArithmeticError('Inexact polynomial division')
    return trim(result)


def power_matrix(rows):
    rational_rows = [[Fraction(value) for value in row] for row in rows]
    denominator = 1
    for row in rational_rows:
        for value in row:
            denominator = math.lcm(denominator, value.denominator)
    integer_rows = [[value.numerator * (denominator // value.denominator)
                     for value in row] for row in rational_rows]
    size = len(rows)
    result = [[0] * size for channel in range(3)]
    previous = []
    current = [1]
    for row in integer_rows:
        for channel, coefficient in enumerate(row):
            for index, value in enumerate(current):
                result[channel][index] += coefficient * value
        following = [0] + [2 * value for value in current]
        for index, value in enumerate(previous):
            following[index] -= value
        if not previous:
            following = [0, 1]
        previous, current = current, following
    content = reduce(math.gcd, (value for channel in result for value in channel)) or 1
    return [trim([value // content for value in reversed(channel)]) for channel in result]


def evaluate(polynomial, position):
    result = 0
    for coefficient in polynomial:
        result = result * position + coefficient
    return result


def derivative(polynomial):
    degree = len(polynomial) - 1
    return [coefficient * (degree - index)
            for index, coefficient in enumerate(polynomial[:-1])]


def bernstein_coefficients(polynomial):
    degree = len(polynomial) - 1
    shifted = [0] * (degree + 1)
    for index, coefficient in enumerate(reversed(polynomial)):
        for offset in range(index + 1):
            shifted[offset] += (coefficient * math.comb(index, offset)
                                * (-1) ** (index - offset) * 2 ** offset)
    denominator = reduce(math.lcm, (math.comb(degree, index)
                                   for index in range(degree + 1)), 1)
    result = []
    for index in range(degree + 1):
        result.append(sum(shifted[offset] * math.comb(index, offset)
                          * (denominator // math.comb(degree, offset))
                          for offset in range(index + 1)))
    content = reduce(math.gcd, result)
    return [value // content for value in result]


def variations(coefficients):
    previous = 0
    count = 0
    for coefficient in coefficients:
        if coefficient:
            sign = 1 if coefficient > 0 else -1
            if previous and sign != previous:
                count += 1
            previous = sign
    return count


def split_bernstein(coefficients):
    degree = len(coefficients) - 1
    left = [coefficients[0] << degree]
    right = [coefficients[-1] << degree]
    row = coefficients
    for level in range(1, degree + 1):
        row = [first + second for first, second in zip(row, row[1:])]
        left.append(row[0] << (degree - level))
        right.append(row[-1] << (degree - level))
    return left, list(reversed(right))


def isolate_roots(polynomial):
    roots = []
    for endpoint in (-1, 1):
        if evaluate(polynomial, endpoint) == 0:
            roots.append(Fraction(endpoint))
            polynomial = exact_quotient(polynomial, [1, -endpoint])
    if len(polynomial) <= 1:
        return polynomial, roots, []
    intervals = []
    pending = [(bernstein_coefficients(polynomial), Fraction(-1), Fraction(1))]
    while pending:
        coefficients, left, right = pending.pop()
        count = variations(coefficients)
        if count == 0:
            continue
        if count == 1 and coefficients[0] and coefficients[-1]:
            intervals.append((left, right, coefficients))
            continue
        lower, upper = split_bernstein(coefficients)
        middle = (left + right) / 2
        if lower[-1] == 0:
            roots.append(middle)
        if variations(lower):
            pending.append((lower, left, middle))
        if variations(upper):
            pending.append((upper, middle, right))
    return polynomial, roots, intervals


def mp_fraction(value):
    return mp.mpf(value.numerator) / value.denominator


def refine_root(interval):
    lower, upper, bernstein = interval
    degree = len(bernstein) - 1
    power = []
    differences = bernstein
    for index in range(degree + 1):
        power.append(math.comb(degree, index) * differences[0])
        differences = [second - first for first, second in zip(differences, differences[1:])]
    coefficients = [mp.mpf(value) for value in reversed(power)]
    slope = derivative(coefficients)
    left, right = mp.mpf(0), mp.mpf(1)
    left_value = evaluate(coefficients, left)
    position = (left + right) / 2
    tolerance = mp.power(10, -mp.mp.dps + 30)
    for iteration in range(4 * mp.mp.prec):
        value = evaluate(coefficients, position)
        if value == 0:
            break
        if (value > 0) == (left_value > 0):
            left, left_value = position, value
        else:
            right = position
        gradient = evaluate(slope, position)
        if gradient:
            correction = value / gradient
            if abs(correction) < tolerance:
                position -= correction
                break
            candidate = position - correction
        else:
            candidate = (left + right) / 2
        if not left < candidate < right:
            candidate = (left + right) / 2
        if abs(candidate - position) < tolerance:
            position = candidate
            break
        position = candidate
    return mp_fraction(lower) + mp_fraction(upper - lower) * position


def chebyshev_values(position, degree):
    values = [mp.mpf(1)]
    if degree:
        values.append(position)
    while len(values) <= degree:
        values.append(2 * position * values[-1] - values[-2])
    return values


def solve(case):
    matrices = {block['id']: power_matrix(block['matrix']) for block in case['blocks']}
    coefficient_bits = max(abs(value).bit_length() for matrix in matrices.values()
                           for channel in matrix for value in channel)
    mp.mp.dps = max(300, int(coefficient_bits * 0.30103) + 260)
    geometries = []
    prepared = {}
    for block in case['blocks']:
        matrix = matrices[block['id']]
        determinant = primitive(subtract(multiply(matrix[0], matrix[2]),
                                         multiply(matrix[1], matrix[1])))
        if block['kind'] == 'point':
            positions = [mp.mpf(0)] if evaluate(determinant, 0) == 0 else []
        elif len(determinant) <= 1:
            positions = []
        else:
            common = polynomial_gcd(determinant, derivative(determinant))
            squarefree = primitive(exact_quotient(determinant, common))
            repeated = polynomial_gcd(squarefree, common)
            endpoints = [Fraction(endpoint) for endpoint in (-1, 1)
                         if evaluate(squarefree, endpoint) == 0
                         and evaluate(repeated, endpoint) != 0]
            polynomial, rational_roots, intervals = isolate_roots(repeated)
            rational_roots.extend(endpoints)
            positions = [mp_fraction(value) for value in rational_roots]
            positions.extend(refine_root(interval) for interval in intervals)
        for position in sorted(positions):
            diagonal_first, off_diagonal, diagonal_second = [
                evaluate(channel, position) for channel in matrix]
            if abs(diagonal_first) >= abs(diagonal_second):
                vector_first, vector_second = -off_diagonal, diagonal_first
            else:
                vector_first, vector_second = diagonal_second, -off_diagonal
            norm_squared = vector_first ** 2 + vector_second ** 2
            projector = [vector_first ** 2 / norm_squared,
                         vector_first * vector_second / norm_squared,
                         vector_second ** 2 / norm_squared]
            geometries.append((block, position, projector))
        if positions:
            prepared[block['id']] = [
                [[mp.mpf(value) for value in coefficient] for coefficient in row]
                for row in block['moments']]
    if not geometries:
        return {'version': 1, 'atoms': []}
    target = mp.matrix([mp.mpf(value) for value in case['rhs']])
    design = mp.matrix(len(target), len(geometries))
    for column, (block, position, projector) in enumerate(geometries):
        moments = prepared[block['id']]
        values = chebyshev_values(position, max(map(len, moments)) - 1)
        for row, kernel in enumerate(moments):
            design[row, column] = mp.fsum(
                values[index] * (coefficient[0] * projector[0]
                                 + 2 * coefficient[1] * projector[1]
                                 + coefficient[2] * projector[2])
                for index, coefficient in enumerate(kernel))
    for row in range(len(target)):
        scale = max(1, abs(target[row]))
        target[row] /= scale
        for column in range(len(geometries)):
            design[row, column] /= scale
    weights, residual = mp.qr_solve(design, target)
    atoms = []
    for (block, position, projector), weight in zip(geometries, weights):
        origin_decimal = Decimal(block['origin'])
        origin_order = origin_decimal.adjusted()
        scale_order = Decimal(block['scale']).adjusted()
        offset_digits = max(0, origin_order - scale_order) if origin_decimal else 0
        digits = min(2025, max(240, mp.mp.dps - 40) + offset_digits)
        with mp.workdps(digits + 20):
            physical = mp.mpf(block['origin']) + mp.mpf(block['scale']) * position
            coordinate = mp.nstr(physical, digits)
        atoms.append({'block': block['id'], 'x': coordinate,
                      'projector': [mp.nstr(value, 240) for value in projector],
                      'weight': mp.nstr(max(weight, mp.mpf('1e-100')), 240)})
    return {'version': 1, 'atoms': atoms}


if __name__ == '__main__':
    json.dump(solve(json.load(sys.stdin)), sys.stdout, allow_nan=False,
              separators=(',', ':'))
    sys.stdout.write('\n')
