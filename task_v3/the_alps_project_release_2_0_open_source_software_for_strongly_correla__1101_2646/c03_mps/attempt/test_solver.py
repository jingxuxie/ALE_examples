import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import itertools
import time
import unittest

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

from solve import solve
from dmrg import Measurements, make_model, run_dmrg


def make_case(family, length, seed=317):
    random = np.random.default_rng(seed)
    case = {'family': family, 'length': length, 'bonds': [], 'observables': []}
    if family == 'bose_hubbard':
        case.update(nmax=4, particles=length,
                    interaction=(4.1 + 0.4 * random.random(length)).tolist(),
                    potential=(0.8 * random.uniform(-1, 1, length)).tolist())
        case['bonds'] = [{'sites': [site, site + 1], 'hopping': float(random.uniform(0.9, 1.2))}
                         for site in range(length - 1)]
        kinds = ['one_body', 'density_connected']
    else:
        spin = 1 if family == 'spin1_chain' else 0.5
        case.update(spin=spin, ground_sector=0, excited_sector=2 if spin == 1 else 1,
                    single_ion=(random.uniform(-0.1, 0.4, length) if spin == 1 else np.zeros(length)).tolist(),
                    field=random.uniform(-0.08, 0.08, length).tolist())
        if spin == 1:
            pairs = [(site, site + 1) for site in range(length - 1)]
            kinds = ['zz', 'string']
        else:
            pairs = [(site, site + 1) for site in range(0, length, 2)]
            pairs += [(site, site + 2) for site in range(length - 2)]
            kinds = ['zz', 'xx']
        for left, right in pairs:
            exchange = float(random.uniform(0.8, 1.4))
            case['bonds'].append({'sites': [left, right], 'jxy': exchange,
                                  'jz': exchange * float(random.uniform(0.9, 1.1))})
    pairs = [(0, 1), (0, length - 1), (length // 3, length // 3 + 1),
             (length // 3, length - 2), (length // 2, length // 2 + 1)]
    case['observables'] = [{'kind': kind, 'sites': list(pair)} for kind in kinds for pair in pairs]
    return case


def exact(case):
    bosons = case['family'] == 'bose_hubbard'
    length = case['length']
    spin = case.get('spin', 0)
    dimension = case['nmax'] + 1 if bosons else int(2 * spin + 1)
    charges = np.arange(dimension, dtype=float) - (0 if bosons else spin)
    plus = np.diag(np.sqrt(np.arange(1, dimension)), -1) if bosons else np.diag(
        np.sqrt(spin * (spin + 1) - charges[:-1] * (charges[:-1] + 1)), -1)
    number = np.diag(charges)
    sectors = {}

    def sector_solution(target):
        if target in sectors:
            return sectors[target]
        configurations = [configuration for configuration in itertools.product(range(dimension), repeat=length)
                          if abs(sum(charges[local] for local in configuration) - target) < 1e-10]
        lookup = {configuration: index for index, configuration in enumerate(configurations)}
        rows, columns, values = [], [], []
        for column, configuration in enumerate(configurations):
            local_charges = np.array([charges[local] for local in configuration])
            if bosons:
                diagonal = np.dot(np.array(case['interaction']) / 2, local_charges * (local_charges - 1))
                diagonal += np.dot(case['potential'], local_charges)
            else:
                diagonal = np.dot(case['single_ion'], local_charges ** 2) - np.dot(case['field'], local_charges)
            for bond in case['bonds']:
                first, last = bond['sites']
                if not bosons:
                    diagonal += bond['jz'] * local_charges[first] * local_charges[last]
                coefficient = -bond['hopping'] if bosons else bond['jxy'] / 2
                for up, down in [(first, last), (last, first)]:
                    if configuration[up] < dimension - 1 and configuration[down] > 0:
                        other = list(configuration)
                        other[up] += 1
                        other[down] -= 1
                        rows.append(lookup[tuple(other)])
                        columns.append(column)
                        values.append(coefficient * plus[other[up], configuration[up]] * plus[configuration[down], other[down]])
            rows.append(column)
            columns.append(column)
            values.append(diagonal)
        matrix = sparse.csr_matrix((values, (rows, columns)), shape=(len(configurations), len(configurations)))
        if len(configurations) < 4:
            energies, vectors = np.linalg.eigh(matrix.toarray())
        else:
            energies, vectors = eigsh(matrix, k=1, which='SA', tol=2e-13,
                                     v0=np.random.default_rng(11).normal(size=len(configurations)))
        result = float(energies[0]), vectors[:, 0], configurations, lookup
        sectors[target] = result
        return result

    target = case['particles'] if bosons else case['ground_sector']
    energy, vector, configurations, lookup = sector_solution(target)
    if bosons:
        gap = sector_solution(target + 1)[0] + sector_solution(target - 1)[0] - 2 * energy
    else:
        gap = sector_solution(case['excited_sector'])[0] - energy

    def expectation(factors):
        value = 0.
        for column, configuration in enumerate(configurations):
            options = [(list(configuration), 1.)]
            for site, operator in factors.items():
                new_options = []
                for other, coefficient in options:
                    for local in np.flatnonzero(operator[:, configuration[site]]):
                        changed = other.copy()
                        changed[site] = int(local)
                        new_options.append((changed, coefficient * operator[local, configuration[site]]))
                options = new_options
            for other, coefficient in options:
                row = lookup.get(tuple(other))
                if row is not None:
                    value += coefficient * vector[row] * vector[column]
        return value

    measured = []
    for observable in case['observables']:
        first, last = observable['sites']
        kind = observable['kind']
        if kind == 'zz':
            value = expectation({first: number, last: number})
        elif kind == 'string':
            factors = {first: number, last: number}
            factors.update({site: np.diag(np.cos(np.pi * charges)) for site in range(first + 1, last)})
            value = -expectation(factors)
        elif kind == 'xx':
            local = (plus + plus.T) / 2
            value = expectation({first: local, last: local})
        elif kind == 'one_body':
            value = expectation({first: plus, last: plus.T})
        elif kind == 'density_connected':
            value = expectation({first: number, last: number})
            value -= expectation({first: number}) * expectation({last: number})
        measured.append(value)
    return {'energy': energy, 'gap': gap, 'correlations': measured}


class SolverTests(unittest.TestCase):
    def check_case(self, case):
        expected = exact(case)
        actual = solve(case)
        self.assertAlmostEqual(actual['energy'], expected['energy'], delta=2e-7)
        self.assertAlmostEqual(actual['gap'], expected['gap'], delta=2e-7)
        np.testing.assert_allclose(actual['correlations'], expected['correlations'], atol=3e-7, rtol=2e-6)

    def test_spin_one(self):
        self.check_case(make_case('spin1_chain', 8))

    def test_ladder(self):
        self.check_case(make_case('spinhalf_ladder', 10))

    def test_bosons(self):
        self.check_case(make_case('bose_hubbard', 6))

    def test_duplicate_and_reversed_bonds(self):
        case = make_case('spin1_chain', 6, 319)
        case['bonds'][0]['sites'].reverse()
        case['bonds'].append(case['bonds'][1].copy())
        self.check_case(case)

    def test_other_sectors(self):
        case = make_case('spinhalf_ladder', 8, 321)
        case['ground_sector'] = -1
        case['excited_sector'] = -2
        case['single_ion'] = np.linspace(-0.2, 0.3, case['length']).tolist()
        self.check_case(case)

    def test_odd_spin_one(self):
        self.check_case(make_case('spin1_chain', 7, 345))

    def test_odd_boson_cutoff_three(self):
        case = make_case('bose_hubbard', 5, 347)
        case['nmax'] = 3
        self.check_case(case)

    def test_spin_one_medium(self):
        self.check_case(make_case('spin1_chain', 10, 325))

    def test_bosons_medium(self):
        self.check_case(make_case('bose_hubbard', 8, 327))

    def test_ladder_medium(self):
        self.check_case(make_case('spinhalf_ladder', 16, 329))

    def test_single_rung(self):
        case = make_case('spinhalf_ladder', 2)
        case['observables'] = [{'kind': kind, 'sites': [0, 1]} for kind in ['zz', 'xx']]
        self.check_case(case)

    def test_uniform_field_shift(self):
        case = make_case('spin1_chain', 6, 331)
        reference = solve(case)
        case['field'] = [field + 0.1 for field in case['field']]
        shifted = solve(case)
        self.assertAlmostEqual(shifted['energy'], reference['energy'], delta=1e-10)
        self.assertAlmostEqual(shifted['gap'], reference['gap'] - 0.2, delta=1e-10)
        np.testing.assert_allclose(shifted['correlations'], reference['correlations'], atol=1e-9, rtol=1e-9)

    def test_parallel_sectors(self):
        case = make_case('bose_hubbard', 6, 333)
        reference = exact(case)
        actual = solve(case, parallel=True)
        self.assertAlmostEqual(actual['energy'], reference['energy'], delta=1e-8)
        self.assertAlmostEqual(actual['gap'], reference['gap'], delta=1e-8)
        np.testing.assert_allclose(actual['correlations'], reference['correlations'], atol=1e-8, rtol=1e-7)

    def test_easy_axis_staggered_field(self):
        case = make_case('spin1_chain', 10, 337)
        case['single_ion'] = [-0.25] * 10
        case['field'] = [0.08 * (-1) ** (site + 1) for site in range(10)]
        for bond in case['bonds']:
            bond['jxy'] = 0.5
            bond['jz'] = 0.6
        reference = exact(case)
        actual = solve(case, parallel=True)
        self.assertAlmostEqual(actual['energy'], reference['energy'], delta=1e-8)
        self.assertAlmostEqual(actual['gap'], reference['gap'], delta=1e-8)
        np.testing.assert_allclose(actual['correlations'], reference['correlations'], atol=1e-8, rtol=1e-7)

    def test_time_limited_state_consistency(self):
        case = make_case('bose_hubbard', 24, 339)
        model = make_model(case)
        energy, state, history = run_dmrg(model, 24, [16, 32, 64, 96, 128], time.monotonic() + 1.5)
        self.assertTrue(history)
        for tensor in state.tensors[1:]:
            matrix = tensor.reshape(tensor.shape[0], -1)
            np.testing.assert_allclose(matrix @ matrix.T, np.eye(matrix.shape[0]), atol=1e-10, rtol=1e-10)
        self.assertAlmostEqual(float(np.linalg.norm(state.tensors[0])), 1., delta=1e-10)
        measurements = Measurements(model, state)
        reconstructed = 0.
        population = 0.
        for site in range(model.length):
            reconstructed += measurements.measure(measurements.left[site], site, model.onsite[site])
            population += measurements.measure(measurements.left[site], site, model.operators['z'])
        for site, link in enumerate(model.links):
            for coefficient, left_name, right_name in link:
                environment = measurements.propagate(measurements.left[site], site, model.operators[left_name])
                reconstructed += coefficient * measurements.measure(environment, site + 1, model.operators[right_name])
        self.assertAlmostEqual(population, 24., delta=1e-9)
        self.assertAlmostEqual(reconstructed, energy, delta=1e-8)


if __name__ == '__main__':
    unittest.main()
