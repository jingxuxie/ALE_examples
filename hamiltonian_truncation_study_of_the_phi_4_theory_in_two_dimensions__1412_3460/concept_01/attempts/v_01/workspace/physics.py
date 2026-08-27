import math

import numpy as np
from scipy.special import k0, k1


def circle_constants(mass, length, boundary):
    images = np.arange(1, max(20, int(40 / (mass * length))) + 1)
    signs = (-1.0) ** images if boundary == 'antiperiodic' else np.ones_like(images)
    difference = np.sum(signs * k0(mass * length * images)) / np.pi
    casimir = -mass * np.sum(signs * k1(mass * length * images) / images) / np.pi
    return float(difference), float(casimir)


def physical_couplings(case):
    difference, constant = circle_constants(case['mass'], case['length'], case['boundary'])
    coefficients = {}
    for term in case['couplings']:
        degree, transfer, value = term['degree'], term.get('transfer', 0), term['value']
        for pairs in range(degree // 2 + 1):
            target = degree - 2 * pairs
            coefficient = math.factorial(degree) / (2 ** pairs * math.factorial(pairs) * math.factorial(target))
            key = (target, transfer)
            coefficients[key] = coefficients.get(key, 0.0) + value * coefficient * difference ** pairs
    constant += case['length'] * coefficients.pop((0, 0), 0.0)
    coefficients = {key: value for key, value in coefficients.items() if key[0] and abs(value) > 1e-15}
    return coefficients, constant


def gaussian_vacuum(case):
    quadratic = sum(term['value'] for term in case['couplings'] if term['degree'] == 2)
    mass_squared = case['mass'] ** 2 + 2 * quadratic
    physical_mass = math.sqrt(mass_squared)
    constant = circle_constants(physical_mass, case['length'], case['boundary'])[1]
    ratio = mass_squared / case['mass'] ** 2
    constant += case['length'] / (8 * np.pi) * (mass_squared - case['mass'] ** 2 - mass_squared * math.log(ratio))
    return physical_mass, constant
