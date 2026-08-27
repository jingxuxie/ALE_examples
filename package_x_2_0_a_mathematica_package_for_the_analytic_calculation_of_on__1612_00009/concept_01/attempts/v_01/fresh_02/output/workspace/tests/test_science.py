import copy
import itertools
import json
import math
import unittest
from pathlib import Path

import mpmath as mp
import numpy as np
from scipy.integrate import quad

from loopaudit.backend import evaluate
from loopaudit.contract import decode


ROOT = Path(__file__).resolve().parents[1]
SETTINGS = json.loads((ROOT / 'profiles.json').read_text())['production']
CAMPAIGN = json.loads((ROOT / 'release.json').read_text())
CHECKS = []


def values(request):
    return {key: decode(value) for key, value in evaluate(request, SETTINGS)['coefficients'].items()}


def base(request):
    return next(iter(values(request).values()))


def permute(request, permutation):
    result = copy.deepcopy(request)
    for field in ['masses2', 'weights', 'moments']:
        if field in result:
            result[field] = np.asarray(result[field])[permutation].tolist()
    result['invariants'] = np.asarray(result['invariants'])[permutation][:, permutation].tolist()
    for direction in result.get('directions', []):
        if 'masses2' in direction:
            direction['masses2'] = np.asarray(direction['masses2'])[permutation].tolist()
        if 'invariants' in direction:
            direction['invariants'] = np.asarray(direction['invariants'])[permutation][:, permutation].tolist()
    return result


class Science(unittest.TestCase):
    def assertRelative(self, actual, expected, tolerance=2e-10):
        error = float(np.max(abs(actual - expected)) / max(np.max(abs(expected)), 1e-14))
        CHECKS.append({'test': self.id(), 'comparison': len(CHECKS), 'relative_error': error,
                       'tolerance': tolerance, 'passed': error <= tolerance})
        self.assertLessEqual(error, tolerance)

    def test_equal_mass_dirichlet_normalizations(self):
        for count, dimension, pairs in itertools.product(range(1, 5), [4, 6, 8], [0, 1, 2]):
            weights = [1 + index % 3 for index in range(count)]
            moments = [index % 2 for index in range(count)]
            request = dict(masses2=[1.9] * count, invariants=np.zeros((count, count)).tolist(),
                           weights=weights, moments=moments, metric_pairs=pairs, dimension=dimension, mu2=2.3)
            alpha = sum(weights) - dimension // 2 - pairs
            normalization = ((-1) ** (sum(weights) + sum(moments) + pairs) / 2 ** pairs
                             * math.prod(math.factorial(weight + moment - 1) / math.factorial(weight - 1)
                                         for weight, moment in zip(weights, moments))
                             / math.factorial(sum(weights) + sum(moments) - 1))
            expected = np.zeros(4, complex)
            if alpha > 0:
                expected[3] = normalization * math.factorial(alpha - 1) / 1.9 ** alpha
            else:
                degree = -alpha
                expected[0] = normalization * (-1) ** degree / math.factorial(degree) * 1.9 ** degree
                expected[3] = expected[0] * (sum(1 / index for index in range(1, degree + 1)) + math.log(2.3 / 1.9))
            self.assertRelative(base(request), expected, 3e-12)

    def test_routing_and_cache_independence(self):
        for case in CAMPAIGN['cases']:
            request = case['integrals'][0]
            permutation = list(reversed(range(len(request['masses2']))))
            first, second = values(request), values(permute(request, permutation))
            for key in first:
                self.assertRelative(first[key], second[key])

    def test_moment_partition_and_dimension_shift(self):
        request = copy.deepcopy(CAMPAIGN['cases'][0]['integrals'][0])
        reference = base(request)
        summed = np.zeros(4, complex)
        for index in range(4):
            term = copy.deepcopy(request)
            term['moments'][index] += 1
            summed += base(term)
        self.assertRelative(summed, -reference)
        first, second = copy.deepcopy(request), copy.deepcopy(request)
        first['metric_pairs'] = 1
        second['dimension'] = 6
        self.assertRelative(base(first), -base(second) / 2)

    def test_mass_derivative_and_mixed_factorials(self):
        request = copy.deepcopy(CAMPAIGN['cases'][0]['integrals'][0])
        request['directions'] = [{'masses2': [1, 0, 0, 0]}, {'masses2': [0, 1, 0, 0]}]
        request['orders'] = [[1, 0], [2, 0], [1, 1], [2, 1]]
        actual = values(request)
        for order in request['orders']:
            shifted = copy.deepcopy(request)
            shifted.pop('directions')
            shifted.pop('orders')
            factor = 1
            for index, power in enumerate(order):
                weight = shifted['weights'][index]
                factor *= math.factorial(weight + power - 1) / math.factorial(weight - 1) / math.factorial(power)
                shifted['weights'][index] += power
            self.assertRelative(actual[','.join(map(str, order))], factor * base(shifted))

    def test_uv_jets_and_pole_disappearance(self):
        for count, dimension, pairs in [(1, 4, 0), (2, 4, 0), (2, 8, 2)]:
            request = dict(masses2=[1.3] * count, invariants=np.zeros((count, count)).tolist(),
                           weights=[1] * count, dimension=dimension, metric_pairs=pairs,
                           directions=[{'masses2': [1] + [0] * (count - 1)}], orders=[[0], [1], [2], [3]])
            actual = values(request)
            for degree in range(4):
                shifted = copy.deepcopy(request)
                shifted.pop('directions')
                shifted.pop('orders')
                shifted['weights'][0] += degree
                self.assertRelative(actual[str(degree)], base(shifted), 3e-12)

    def test_scale_and_mu_covariance(self):
        for case in CAMPAIGN['cases']:
            request = copy.deepcopy(case['integrals'][0])
            reference = values(request)
            rescaled = copy.deepcopy(request)
            scale = 1700.0
            rescaled['masses2'] = (np.asarray(request['masses2']) * scale).tolist()
            rescaled['invariants'] = (np.asarray(request['invariants']) * scale).tolist()
            rescaled['mu2'] = request.get('mu2', 1) * scale
            for direction in rescaled.get('directions', []):
                for field in ['masses2', 'invariants']:
                    if field in direction:
                        direction[field] = (np.asarray(direction[field]) * scale).tolist()
            alpha = sum(request.get('weights', [1] * len(request['masses2']))) - request.get('dimension', 4) // 2 - request.get('metric_pairs', 0)
            changed = values(rescaled)
            for key in reference:
                self.assertRelative(changed[key] * scale ** alpha, reference[key])
            request['mu2'] = request.get('mu2', 1) * math.exp(0.7)
            changed = values(request)
            for key, coefficient in reference.items():
                expected = coefficient.copy()
                expected[2] += 0.7 * coefficient[1]
                expected[3] += 0.7 * (coefficient[0] + coefficient[2]) + 0.7 ** 2 / 2 * coefficient[1]
                self.assertRelative(changed[key], expected)

    def test_physical_bubble_independent_real_cut_integral(self):
        request = dict(masses2=[0.7, 1.4], invariants=[[0, 8], [8, 0]], mu2=1.7)
        roots = sorted(np.roots([8, 1.4 - 0.7 - 8, 0.7]))
        def denominator(coordinate):
            return 0.7 * (1 - coordinate) + 1.4 * coordinate - 8 * coordinate * (1 - coordinate)
        for moments, pairs in [([0, 0], 0), ([0, 2], 0), ([0, 0], 1)]:
            request.update(moments=moments, metric_pairs=pairs)
            sign = (-1) ** (sum(moments) + pairs) / 2 ** pairs
            uv = sign * (-1) ** pairs * quad(lambda coordinate: coordinate ** moments[1] * denominator(coordinate) ** pairs, 0, 1)[0]
            real = sign * (-1) ** pairs * quad(
                lambda coordinate: coordinate ** moments[1] * denominator(coordinate) ** pairs
                * (pairs + math.log(1.7 / abs(denominator(coordinate)))),
                0, 1, points=roots, epsabs=1e-12, epsrel=1e-12)[0]
            imaginary = sign * (-1) ** pairs * math.pi * quad(
                lambda coordinate: coordinate ** moments[1] * denominator(coordinate) ** pairs, roots[0], roots[1])[0]
            self.assertRelative(base(request), np.array([uv, 0, 0, complex(real, imaginary)]))

    def test_triangle_gamma_function_contour_extraction(self):
        with mp.workdps(55):
            for moments, invariant in [([0, 0, 0], -3.4), ([0, 2, 1], 5.1), ([2, 0, 2], 2.7), ([0, 3, 0], -1.2)]:
                request = dict(masses2=[0, 0, 0], invariants=[[0, 0, invariant], [0, 0, 0], [invariant, 0, 0]],
                               moments=moments, mu2=1.7)
                coefficients = []
                for power in [-2, -1, 0]:
                    total = 0
                    for index in range(32):
                        epsilon = mp.mpf('0.01') * mp.exp(2j * mp.pi * index / 32)
                        logarithm = mp.log(abs(invariant)) - (1j * mp.pi if invariant > 0 else 0)
                        value = ((-1) ** (3 + sum(moments)) * mp.gamma(1 + epsilon)
                                 * mp.gamma(moments[0] - epsilon) * mp.gamma(moments[2] - epsilon)
                                 * mp.gamma(moments[1] + 1) / mp.gamma(sum(moments) + 1 - 2 * epsilon)
                                 * mp.exp(mp.euler * epsilon + epsilon * mp.log(mp.mpf('1.7')) - (1 + epsilon) * logarithm))
                        total += value / epsilon ** power / 32
                    coefficients.append(complex(total))
                self.assertRelative(base(request), np.array([0] + coefficients), 3e-13)

    def test_box_independent_projective_endpoint_subtraction(self):
        with mp.workdps(55):
            for mass in [mp.mpf('1.3'), mp.mpf('0')]:
                first, second, mu = mp.mpf('4'), mp.mpf('3'), mp.mpf('1.7')
                endpoints = 1 + int(mass == 0)
                residue = -endpoints / (first * second)
                constant = (mp.log(first) + (mp.log(second) if mass == 0 else -mp.log(mass / second))) / (first * second)
                def derivative(coordinate):
                    left = first * coordinate
                    right = second * (1 - coordinate) + mass * coordinate
                    if abs(left - right) < mp.mpf('1e-45'):
                        value = (1 - mp.log(left)) / left ** 2
                    else:
                        value = (mp.log(left) / left - mp.log(right) / right) / (left - right)
                    value += mp.log(left) / (first * second * coordinate)
                    if mass == 0:
                        value += mp.log(right) / (first * second * (1 - coordinate))
                    return value
                linear = mp.quad(derivative, [0, mp.mpf('.2'), mp.mpf('.6'), 1])
                linear -= (mp.log(first) ** 2 + (mp.log(second) ** 2 if mass == 0 else 0)) / (2 * first * second)
                finite = -2 * (linear + mp.log(mu) * constant + (mp.log(mu) ** 2 / 2 - mp.pi ** 2 / 12) * residue)
                matrix = [[0, 0, -float(first), -float(mass)], [0, 0, 0, -float(second)],
                          [-float(first), 0, 0, 0], [-float(mass), -float(second), 0, 0]]
                actual = base(dict(masses2=[0] * 4, invariants=matrix, mu2=float(mu)))
                self.assertRelative(actual[3:], np.array([complex(finite)]), 3e-12)

    def test_box_causal_common_phase(self):
        for item in CAMPAIGN['cases'][4]['integrals']:
            reference = base(item)
            continued = copy.deepcopy(item)
            continued['invariants'] = (-np.asarray(item['invariants'])).tolist()
            expected = reference.copy()
            expected[2] += 1j * math.pi * reference[1]
            expected[3] += 1j * math.pi * reference[2] - math.pi ** 2 / 2 * reference[1]
            self.assertRelative(base(continued), expected, 3e-13)

    def test_observable_regulator_convolution(self):
        from loopaudit.service import run_cases
        item = copy.deepcopy(CAMPAIGN['cases'][3]['integrals'][0])
        item.pop('directions')
        item.pop('orders')
        request = {'cases': [{'id': 'convolution', 'integrals': [item],
                             'observables': [{'id': 'product', 'terms': [{'integral': item['id'],
                                                                        'epsilon_polynomial': [2, -3, 5]}]}]}]}
        result = run_cases(request, SETTINGS)['cases'][0]
        coefficient = decode(result['integrals'][item['id']]['coefficients']['base'])
        expected = 2 * coefficient
        expected[2] -= 3 * coefficient[1]
        expected[3] += -3 * (coefficient[0] + coefficient[2]) + 5 * coefficient[1]
        self.assertRelative(decode(result['observables']['product']['values']), expected, 2e-15)


if __name__ == '__main__':
    unittest.main()
