import ctypes
import itertools
import json
import math
import time
from pathlib import Path
import numpy as np
import sympy as sp
from sympy.polys.matrices import DomainMatrix
from sympy.polys.domains import QQ, ZZ

root = Path(__file__).resolve().parent
expected = np.array(json.load(open(root.parent.parent / 'participant/input/target.json'))['cyclic_autocorrelation'], dtype=np.int64)
library = ctypes.CDLL(str(root / 'enumerate.so'))
integer_array = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
real_array = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
library.enumerate_basis.argtypes = [integer_array, real_array, real_array, ctypes.c_int, ctypes.c_int64, integer_array, integer_array, ctypes.c_int, ctypes.c_double]
started = time.monotonic()

def canonical(values):
    return min(tuple(np.roll(orientation, offset)) for orientation in [values, values[::-1]] for offset in range(len(values)) if orientation[-offset] == np.min(values))

def can_lift(lower):
    half = len(lower)
    if half == 4096: return True
    folded = expected.reshape(-1, 2 * half).sum(axis=0)
    rows = []
    for lag in range(half // 2):
        actual = sum(int(lower[index]) * int(lower[(index + lag) % half]) * (1 if index + lag < half else -1) for index in range(half))
        difference = int(folded[lag] - folded[lag + half]) - actual
        if difference % 2: return False
        mask = sum(((int(lower[(index + lag) % half]) + int(lower[(index - lag) % half])) % 2) << index for index in range(half))
        rows.append(mask | (((difference // 2) % 2) << half))
    pivot = 0
    for column in range(half):
        chosen = next((index for index in range(pivot, len(rows)) if (rows[index] >> column) & 1), None)
        if chosen is None: continue
        rows[pivot], rows[chosen] = rows[chosen], rows[pivot]
        for index in range(pivot + 1, len(rows)):
            if (rows[index] >> column) & 1: rows[index] ^= rows[pivot]
        pivot += 1
    return all(row != (1 << half) for row in rows[pivot:])

def root_lift(value, prime, exponent, half):
    modulus = prime
    for power in range(1, exponent):
        derivative = (half * pow(value, half - 1, prime)) % prime
        quotient = ((pow(value, half, modulus * prime) + 1) // modulus) % prime
        value += modulus * ((-quotient * pow(derivative, -1, prime)) % prime)
        modulus *= prime
    return value

def polynomial_value(coefficients, value, modulus):
    result = 0
    for coefficient in coefficients[::-1]: result = (result * value + int(coefficient)) % modulus
    return result

def lattice(half, constraints):
    basis = sp.eye(half)
    for prime, residue, exponent in constraints:
        modulus = int(prime ** exponent)
        powers = [pow(int(residue), index, modulus) for index in range(half)]
        values = [sum(int(basis[row, column]) * powers[column] for column in range(half)) % modulus for row in range(half)]
        common = math.gcd(modulus, *values)
        modulus //= common
        values = [value // common for value in values]
        if modulus == 1: continue
        pivot = next(index for index, value in enumerate(values) if math.gcd(value, modulus) == 1)
        pivot_row = basis.row(pivot)
        inverse = pow(values[pivot], -1, modulus)
        for row in range(half):
            if row == pivot: continue
            multiplier = (values[row] * inverse) % modulus
            if multiplier > modulus // 2: multiplier -= modulus
            basis[row, :] = basis.row(row) - multiplier * pivot_row
        basis[pivot, :] = modulus * pivot_row
        for reduction in range(3):
            basis = DomainMatrix.from_Matrix(basis).convert_to(ZZ).lll(delta=QQ(3, 4)).to_Matrix()
    return np.array(basis.tolist(), dtype=np.int64)

def enumerate_vectors(basis, wanted):
    half = len(basis)
    orthogonal = basis.astype(float)
    mu = np.zeros((half, half))
    norms = np.zeros(half)
    for row in range(half):
        for column in range(row):
            mu[row, column] = np.dot(basis[row], orthogonal[column]) / norms[column]
            orthogonal[row] -= mu[row, column] * orthogonal[column]
        norms[row] = orthogonal[row] @ orthogonal[row]
    output = np.zeros((8192, half), dtype=np.int64)
    count = library.enumerate_basis(basis, norms, mu, half, int(wanted[0]), wanted, output, len(output), 8.0)
    print('BASIS', half, int(np.max(np.abs(basis))), float(norms.min()), float(norms.max()), 'VECTORS', count, flush=True)
    return output[:count]

lower_candidates = [np.array(candidate, dtype=np.int64) for candidate in np.load(root / 'algebraic_64.npy')]
variable = sp.Symbol('x')
for size in [128, 256]:
    half = size // 2
    folded = expected.reshape(-1, size).sum(axis=0)
    wanted = np.ascontiguousarray(folded[:half] - folded[half:])
    polynomial = sum(int(value) * variable ** index for index, value in enumerate(wanted))
    norm_square = int(sp.resultant(polynomial, variable ** half + 1, variable))
    norm = math.isqrt(norm_square)
    factors = sp.factorint(norm, limit=10000)
    if size == 128:
        factors = {2: 2, 4993: 1, 199920257: 1, 3378967481473: 1, 681026113153: 1, 32847138371925861141170366532594422049303444804829592203393: 1}
    print('ALGEBRAIC SIZE', size, 'NORM', norm, 'FACTORS', factors, 'RADIUS2', wanted[0], 'ELAPSED', time.monotonic() - started, flush=True)
    if any(not sp.isprime(prime) for prime in factors):
        print('UNFACTORED', flush=True)
        break
    choices = []
    unsupported = False
    for prime, exponent in factors.items():
        prime, exponent = int(prime), int(exponent)
        if prime == 2: continue
        if (prime - 1) % size:
            print('UNSUPPORTED PRIME', prime, flush=True)
            unsupported = True
            break
        trial = 2
        while True:
            generator = pow(trial, (prime - 1) // size, prime)
            if pow(generator, half, prime) == prime - 1: break
            trial += 1
        zeros = set()
        for index in range(1, size, 2):
            value = pow(generator, index, prime)
            if polynomial_value(wanted, value, prime) == 0: zeros.add(value)
        accounted = 0
        while zeros:
            value = min(zeros)
            inverse = pow(value, -1, prime)
            zeros.remove(value)
            zeros.remove(inverse)
            lifted = root_lift(value, prime, exponent, half)
            evaluation = polynomial_value(wanted, lifted, prime ** exponent)
            valuation = 0
            while valuation < exponent and evaluation % prime == 0:
                valuation += 1
                evaluation //= prime
            accounted += valuation
            pair_choices = []
            for count in range(valuation + 1):
                constraints = []
                if count: constraints.append((prime, root_lift(value, prime, count, half), count))
                if valuation - count: constraints.append((prime, root_lift(inverse, prime, valuation - count, half), valuation - count))
                pair_choices.append(constraints)
            choices.append(pair_choices)
        if accounted != exponent:
            print('VALUATION ERROR', prime, accounted, exponent, flush=True)
            unsupported = True
    if unsupported: break
    candidates = set()
    primitive = set()
    configurations = list(itertools.product(*choices))
    for number, configuration in enumerate(configurations):
        constraints = sorted(sum(configuration, []), reverse=True)
        basis = lattice(half, constraints)
        vectors = enumerate_vectors(basis, wanted)
        for vector in vectors:
            key = tuple(vector)
            if key in primitive: continue
            primitive.add(key)
            for lower in lower_candidates:
                if np.any((lower + vector) % 2): continue
                candidate = np.r_[(lower + vector) // 2, (lower - vector) // 2]
                if np.min(candidate) < 0 or np.max(candidate) > 8192 // size: continue
                actual = np.rint(np.fft.irfft(np.abs(np.fft.rfft(candidate)) ** 2, n=size)).astype(np.int64)
                if not np.array_equal(actual, folded): raise RuntimeError('algebraic correlation error')
                key = canonical(candidate)
                if key not in candidates and can_lift(key): candidates.add(key)
        print('IDEAL', size, number + 1, len(configurations), 'VECTORS', len(vectors), 'PRIMITIVE', len(primitive), 'CANDIDATES', len(candidates), 'ELAPSED', time.monotonic() - started, flush=True)
        if candidates: break
    lower_candidates = [np.array(candidate, dtype=np.int64) for candidate in sorted(candidates)]
    np.save(root / f'algebraic_{size}.npy', np.array(lower_candidates))
    with open(root / 'algebraic_levels.txt', 'a') as output:
        for candidate in lower_candidates: output.write(str(size) + ' ' + ' '.join(map(str, candidate)) + '\n')
    if not lower_candidates:
        print('NO CANDIDATES', flush=True)
        break
