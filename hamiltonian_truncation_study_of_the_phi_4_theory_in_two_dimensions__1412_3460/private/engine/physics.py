import math

import numpy as np
from scipy.special import kv


def finite_volume(length, mass, boundary):
    images = np.arange(1, int(max(40, 40 / (length * mass))) + 1)
    signs = (-1.0)**images if boundary == 'antiperiodic' else np.ones(len(images))
    contraction = float(np.sum(signs * kv(0, mass * length * images)) / math.pi)
    casimir = float(-mass * np.sum(signs * kv(1, mass * length * images) / images) / math.pi)
    return contraction, casimir


def circle_couplings(case):
    contraction, casimir = finite_volume(case['length'], case['mass'], case['boundary'])
    result = {}
    for term in case['couplings']:
        degree, transfer, coupling = term['degree'], term.get('transfer', 0), term['value']
        for pairs in range(degree // 2 + 1):
            remaining = degree - 2 * pairs
            factor = math.factorial(degree) / (math.factorial(remaining) * math.factorial(pairs) * 2**pairs)
            key = (remaining, transfer)
            result[key] = result.get(key, 0.0) + coupling * factor * contraction**pairs
    return result, contraction, casimir


def spectral_coefficients(couplings, contraction):
    result = {}
    for (degree_a, transfer_a), coupling_a in couplings.items():
        for (degree_b, transfer_b), coupling_b in couplings.items():
            for count in range(2, min(degree_a, degree_b) + 1):
                factor = math.comb(degree_a, count) * math.comb(degree_b, count) * math.factorial(count)
                remaining = degree_a + degree_b - 2 * count
                key = (remaining, transfer_a + transfer_b)
                vector = result.setdefault(key, np.zeros(3))
                for power in range(2, count + 1):
                    vector[power - 2] += coupling_a * coupling_b * factor * math.comb(count, power) * contraction**(count - power)
    return result
