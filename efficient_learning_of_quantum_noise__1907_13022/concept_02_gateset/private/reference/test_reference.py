import ast
import hashlib
import itertools
import json
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace

import numpy as np
from scipy.linalg import null_space

from generate import ROOT, build_case, gate_set, physical_rates, topology
from metrics import WEIGHTS, losses, score_components
from solver import Model, membership, row_basis, solve
from weak_baseline import ideal_signs


PAULIS = [np.eye(2), np.array([[0, 1], [1, 0]]), np.array([[0, -1j], [1j, 0]]),
          np.diag([1, -1])]


def tensor_operator(pauli):
    result = np.ones((1, 1), dtype=complex)
    for axis in pauli:
        result = np.kron(result, PAULIS[axis])
    return result


def dense_gate(model, gate):
    size = 2 ** model.qubits
    total = np.eye(size, dtype=complex)
    for opcode, first, second in model.operations[gate]:
        primitive = np.zeros((size, size), dtype=complex)
        for column in range(size):
            bits = [(column >> (model.qubits - site - 1)) & 1 for site in range(model.qubits)]
            if opcode == 1:
                for output_bit in (0, 1):
                    changed = bits.copy()
                    changed[first] = output_bit
                    row = sum(bit << (model.qubits - site - 1) for site, bit in enumerate(changed))
                    primitive[row, column] = (-1) ** (bits[first] * output_bit) / np.sqrt(2)
            else:
                amplitude = 1
                if opcode == 2:
                    amplitude = 1j ** bits[first]
                elif opcode == 3:
                    bits[second] ^= bits[first]
                elif opcode == 4:
                    amplitude = (-1) ** (bits[first] * bits[second])
                elif opcode == 5:
                    bits[first], bits[second] = bits[second], bits[first]
                row = sum(bit << (model.qubits - site - 1) for site, bit in enumerate(bits))
                primitive[row, column] = amplitude
        total = primitive @ total
    return total


def physical_channel(model, channel, rates, state):
    for position in model.indices[channel]:
        rate = rates[position]
        if channel >= 0:
            operator = tensor_operator(model.labels[position])
            probability = -np.expm1(-2 * rate) / 2
            state = (1 - probability) * state + probability * operator @ state @ operator
        else:
            sites = np.flatnonzero(model.supports[position])
            twirled = np.zeros_like(state)
            for local in itertools.product(range(4), repeat=len(sites)):
                label = np.zeros(model.qubits, dtype=int)
                label[sites] = local
                operator = tensor_operator(label)
                twirled += operator @ state @ operator / 4 ** len(sites)
            state = np.exp(-rate) * state + (-np.expm1(-rate)) * twirled
    return state


def independent_feature(model, channel, pauli):
    values = np.zeros(model.parameter_count)
    for position in model.indices[channel]:
        if channel < 0:
            values[position] = any(pauli[site] != 0 for site in np.flatnonzero(model.supports[position]))
        else:
            anticommutes = sum(first != 0 and second != 0 and first != second
                               for first, second in zip(model.labels[position], pauli)) % 2
            values[position] = 2 * anticommutes
    return values


def forward_label(model, gate, pauli):
    coordinates_x = ((pauli == 1) | (pauli == 2)).astype(np.int8)
    coordinates_z = ((pauli == 2) | (pauli == 3)).astype(np.int8)
    for opcode, first, second in model.operations[gate]:
        if opcode == 1:
            coordinates_x[first], coordinates_z[first] = coordinates_z[first], coordinates_x[first]
        elif opcode == 2:
            coordinates_z[first] ^= coordinates_x[first]
        elif opcode == 3:
            coordinates_x[second] ^= coordinates_x[first]
            coordinates_z[first] ^= coordinates_z[second]
        elif opcode == 4:
            coordinates_z[first] ^= coordinates_x[second]
            coordinates_z[second] ^= coordinates_x[first]
        elif opcode == 5:
            coordinates_x[first], coordinates_x[second] = coordinates_x[second], coordinates_x[first]
            coordinates_z[first], coordinates_z[second] = coordinates_z[second], coordinates_z[first]
    return np.where(coordinates_x, np.where(coordinates_z, 2, 1), np.where(coordinates_z, 3, 0))


def graph_constraints(model):
    embedding, incidence = [], []
    patterns = 2 ** model.qubits - 1

    def pattern(pauli):
        return sum(1 << site for site in np.flatnonzero(pauli))

    def edge(channel, pauli, source, destination):
        embedding.append(independent_feature(model, channel, pauli))
        boundary = np.zeros(patterns)
        if source:
            boundary[source - 1] -= 1
        if destination:
            boundary[destination - 1] += 1
        incidence.append(boundary)

    for mask in range(1, patterns + 1):
        pauli = np.array([3 if mask & (1 << site) else 0 for site in range(model.qubits)])
        edge(-2, pauli, 0, mask)
        edge(-1, pauli, mask, 0)
    for gate in np.flatnonzero(model.noise >= 0):
        for label in itertools.product(range(4), repeat=model.qubits):
            if not any(label):
                continue
            pauli = np.array(label)
            output = forward_label(model, gate, pauli)
            edge(int(model.noise[gate]), pauli, pattern(pauli), pattern(output))
    embedding, incidence = np.array(embedding), np.array(incidence)
    return embedding - incidence @ np.linalg.lstsq(incidence, embedding, rcond=None)[0]


class ReferenceTests(unittest.TestCase):
    def test_dense_born_rule_and_physicality(self):
        random = np.random.default_rng(91)
        for qubits, family in ((2, 'local_edges'), (4, 'parallel_crosstalk')):
            data, _ = gate_set(qubits, family, 1, random)
            model = Model(data)
            rates = physical_rates(model, random, 1)
            labels = list(itertools.product(range(4), repeat=qubits))
            operators = [tensor_operator(label) for label in labels]
            gates = [dense_gate(model, gate) for gate in range(len(model.noise))]
            for _ in range(6):
                sequence = random.integers(len(gates), size=7)
                observable = random.integers(1, 4, size=qubits)
                total = np.eye(2 ** qubits, dtype=complex)
                for gate in sequence:
                    total = gates[gate] @ total
                inverse = total.conj().T @ tensor_operator(observable) @ total
                overlaps = np.array([np.trace(operator @ inverse).real / 2 ** qubits
                                     for operator in operators])
                initial = labels[int(np.argmax(np.abs(overlaps)))]
                state = np.ones((1, 1), dtype=complex)
                for axis in initial:
                    state = np.kron(state, (PAULIS[0] + (PAULIS[axis] if axis else 0)) / 2)
                state = physical_channel(model, -2, rates, state)
                for gate in sequence:
                    channel = int(model.noise[gate])
                    if channel >= 0:
                        state = physical_channel(model, channel, rates, state)
                    state = gates[gate] @ state @ gates[gate].conj().T
                state = physical_channel(model, -1, rates, state)
                expectation = np.trace(tensor_operator(observable) @ state).real
                row, sign, _ = model.trace(sequence, observable)
                self.assertAlmostEqual(expectation, sign * np.exp(-row @ rates), places=11)
                self.assertAlmostEqual(np.trace(state).real, 1, places=11)
                self.assertGreater(np.linalg.eigvalsh(state).min(), -1e-12)

    def test_independent_cut_space_equals_rooted_space(self):
        for qubits, family in ((3, 'local_edges'), (4, 'parallel_crosstalk'),
                               (4, 'restricted_components')):
            data, _ = gate_set(qubits, family, 1, np.random.default_rng(12))
            model = Model(data)
            graph_basis = row_basis(graph_constraints(model))
            rooted_basis = model.structural_basis()
            self.assertEqual(len(graph_basis), len(rooted_basis))
            np.testing.assert_allclose(graph_basis.T @ graph_basis,
                                       rooted_basis.T @ rooted_basis, atol=2e-10)
            if family == 'local_edges':
                self.assertEqual(len(rooted_basis), model.parameter_count - qubits)

    def test_compressed_roots_span_all_paulis(self):
        data, _ = gate_set(4, 'parallel_crosstalk', 1, np.random.default_rng(8))
        model = Model(data)
        exhaustive = [model.trace(sequence, np.array(label))[0]
                      for sequence in [[]] + [[gate] for gate in np.flatnonzero(model.noise >= 0)]
                      for label in itertools.product(range(4), repeat=4) if any(label)]
        basis = model.structural_basis()
        self.assertTrue(np.all(membership(np.array(exhaustive), basis)))
        self.assertEqual(len(row_basis(np.array(exhaustive))), len(basis))

    def test_gauge_orbits_preserve_experiments_not_atoms(self):
        data, _ = gate_set(3, 'local_edges', 0, np.random.default_rng(72))
        model = Model(data)
        gauge = null_space(graph_constraints(model), rcond=1e-10)
        self.assertEqual(gauge.shape[1], 3)
        rates = np.full(model.parameter_count, 0.02)
        displacement = gauge @ np.arange(1, gauge.shape[1] + 1)
        displacement *= 0.005 / np.max(np.abs(displacement))
        changed = rates + displacement
        self.assertTrue(np.all(changed > 0))
        random = np.random.default_rng(111)
        for _ in range(50):
            sequence = random.integers(len(model.noise), size=12)
            pauli = random.integers(1, 4, size=3)
            row, _, _ = model.trace(sequence, pauli)
            self.assertAlmostEqual(row @ rates, row @ changed, places=11)
        self.assertGreater(np.max(np.abs(displacement)), 0.004)
        atoms = np.array([independent_feature(model, channel, np.array(label))
                          for channel in model.indices for label in itertools.product(range(4), repeat=3)])
        self.assertGreater(np.max(np.abs(atoms @ displacement)), 0.001)

    def test_original_notebook_embedding_functions(self):
        source = ROOT.parent / 'private/sources/PauliGST/PauliGST_published_250514.ipynb'
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),
                         '81a63ad79a43c3d7640d10f5671a392c13727970ce76428f75e46bcecb41047d')
        notebook = json.loads(source.read_text())
        module = ast.parse(''.join(notebook['cells'][10]['source']))
        functions = ast.Module(body=[node for node in module.body if isinstance(node, ast.FunctionDef)],
                               type_ignores=[])
        data, _ = gate_set(4, 'parallel_crosstalk', 1, np.random.default_rng(15))
        model = Model(data)
        rates = physical_rates(model, np.random.default_rng(99), 1)
        factors = sorted(model.factors[-2])
        inverse, cumulants = {}, []
        for channel, label in ((-2, 'S'), (-1, 'M'), (0, 'layer1'), (1, 'layer2')):
            for factor in factors:
                choices = [(3,) * len(factor)] if channel < 0 else itertools.product((1, 2, 3), repeat=len(factor))
                for choice in choices:
                    key = (label, factor) if channel < 0 else (label, factor, tuple('IXYZ'[axis] for axis in choice))
                    inverse[key] = len(cumulants)
                    value = 0.0
                    for mask in range(2 ** len(factor)):
                        pauli = np.zeros(4, dtype=int)
                        for position, site in enumerate(factor):
                            if mask & (1 << position):
                                pauli[site] = choice[position]
                        value += (-1) ** (len(factor) - mask.bit_count()) * (
                            independent_feature(model, channel, pauli) @ rates)
                    cumulants.append(value)
        namespace = {'faclist': factors, 'param': SimpleNamespace(inverse=inverse),
                     'pt': lambda pauli: [int(axis != 'I') for axis in pauli]}
        exec(compile(functions, str(source), 'exec'), namespace)
        for channel in (-2, -1, 0, 1):
            for label in itertools.product(range(4), repeat=4):
                equation = np.zeros(len(cumulants))
                text = ''.join('IXYZ'[axis] for axis in label)
                if channel < 0:
                    namespace['add_S_noise' if channel == -2 else 'add_M_noise'](equation, text)
                else:
                    namespace['add_G_noise'](equation, ('layer' + str(channel + 1),), text)
                self.assertAlmostEqual(equation @ cumulants,
                                       independent_feature(model, channel, np.array(label)) @ rates,
                                       places=11)

    def test_seeded_generation_and_coverage_gap(self):
        first, oracle, details = build_case(7788, 6, 'restricted_components', 0)
        second, second_oracle, _ = build_case(7788, 6, 'restricted_components', 0)
        for key in first:
            np.testing.assert_array_equal(first[key], second[key])
            self.assertFalse(first[key].dtype.hasobject)
        for key in oracle:
            np.testing.assert_array_equal(oracle[key], second_oracle[key])
        self.assertLess(details['calibration_rank'], details['structural_rank'])
        self.assertTrue(np.any(oracle['structural_identifiable'] > oracle['calibration_identifiable']))
        self.assertEqual(set(first), {'schema_version', 'n_qubits', 'gate_ptr', 'gate_ops',
                                     'gate_noise', 'factor_channel', 'factor_mask', 'train_ptr',
                                     'train_gates', 'train_observable', 'train_shots', 'train_plus',
                                     'holdout_ptr', 'holdout_gates', 'holdout_observable', 'query_ptr',
                                     'query_channel', 'query_pauli', 'query_coeff'})

    def test_independent_binary_signs(self):
        data, _, _ = build_case(8181, 6, 'parallel_crosstalk', 1)
        model = Model(data)
        for prefix in ('train', 'holdout'):
            _, signs = model.experiments(prefix)
            np.testing.assert_array_equal(signs, ideal_signs(data, prefix))

    def test_reference_only_uses_input(self):
        data, oracle, _ = build_case(123, 2, 'local_edges', 0, small=True)
        output, diagnostic = solve(data, diagnostics=True)
        np.testing.assert_array_equal(output['structural_identifiable'], oracle['structural_identifiable'])
        np.testing.assert_array_equal(output['calibration_identifiable'], oracle['calibration_identifiable'])
        self.assertTrue(diagnostic['success'])
        self.assertTrue(diagnostic['heldout_estimable'])
        self.assertLess(np.sqrt(np.mean((output['holdout_mean'] - oracle['holdout_mean']) ** 2)), 0.04)

    def test_arbitrary_unidentified_gauge_values_never_scored(self):
        data, oracle, _ = build_case(431, 2, 'local_edges', 0, small=True)
        output = solve(data)
        changed = {key: value.copy() for key, value in oracle.items()}
        changed['query_log'][~changed['calibration_identifiable'].astype(bool)] += 1000
        self.assertEqual(losses(output, oracle), losses(output, changed))

    def test_largest_system_fresh_seed(self):
        data, oracle, details = build_case(72631229, 24, 'parallel_crosstalk', 4)
        output, diagnostic = solve(data, diagnostics=True)
        self.assertEqual(details['parameters'], 672)
        self.assertTrue(diagnostic['success'])
        np.testing.assert_array_equal(output['structural_identifiable'], oracle['structural_identifiable'])
        self.assertLess(np.sqrt(np.mean((output['holdout_mean'] - oracle['holdout_mean']) ** 2)), 0.04)

    def test_large_restricted_sector_is_connected(self):
        data, oracle, details = build_case(841619, 16, 'restricted_components', 3)
        geometry = topology(data)
        self.assertEqual(geometry['ideal_graph_component_sizes'], [16])
        self.assertEqual(geometry['noise_graph_component_sizes'], [16])
        self.assertLess(details['calibration_rank'], details['structural_rank'])
        self.assertGreater(np.sum(oracle['calibration_identifiable']), 20)
        self.assertTrue(np.all(np.isin(data['train_observable'], [0, 3])))

    def test_scoring_strictly_decreases_without_clipping(self):
        baseline = {key: 1.0 for key in WEIGHTS}
        reference = {key: 0.001 for key in WEIGHTS}
        scores = [score_components({key: loss for key in WEIGHTS}, baseline, reference)[1]
                  for loss in (0, 1e-12, 1e-7, 0.001, 0.5, 1, 2, 100, 1e8)]
        self.assertTrue(all(first > second for first, second in zip(scores[:-1], scores[1:])))
        self.assertGreater(scores[-1], 0)
        self.assertLess(scores[1], 1)

    def test_precomputed_pools_quality_and_disjointness(self):
        seeds = set()
        hashes = set()
        for pool, expected in (('reference/core', 9), ('challenge_pool', 6)):
            manifest = json.loads((ROOT / 'private' / pool / 'manifest.json').read_text())
            self.assertEqual(len(manifest['cases']), expected)
            self.assertEqual(len({entry['family'] for entry in manifest['cases']}), 3)
            for entry in manifest['cases']:
                if entry['qubits'] >= 16:
                    self.assertEqual(entry['ideal_graph_component_sizes'], [entry['qubits']])
                    self.assertEqual(entry['noise_graph_component_sizes'], [entry['qubits']])
                    self.assertLessEqual(entry['maximum_dependency_scope'], 4)
                if pool == 'challenge_pool':
                    self.assertGreaterEqual(entry['qubits'], 20)
                self.assertNotIn(entry['seed'], seeds)
                self.assertNotIn(entry['input_sha256'], hashes)
                seeds.add(entry['seed'])
                hashes.add(entry['input_sha256'])
                self.assertTrue(entry['fit']['success'])
                self.assertTrue(entry['fit']['heldout_estimable'])
                self.assertLess(entry['reference_loss']['heldout_prediction'], 0.0016)
                _, score = score_components(entry['reference_loss'], entry['baseline_loss'], entry['reference_loss'])
                self.assertGreater(score, 0.9)
            for family in {entry['family'] for entry in manifest['cases']}:
                self.assertGreaterEqual(max(entry['qubits'] for entry in manifest['cases']
                                            if entry['family'] == family), 20)

    def test_landlock_denies_private_aliases_and_allows_temp(self):
        sys.path.insert(0, str(ROOT / 'private'))
        from evaluator import run_case
        with np.load(ROOT / 'participant/input/example.npz', allow_pickle=False) as sample:
            queries = len(sample['query_ptr']) - 1
            heldout = len(sample['holdout_observable'])
        output, _ = run_case(Path(__file__).with_name('sandbox_probe.py'),
                             ROOT / 'participant/input/example.npz', queries, heldout)
        self.assertEqual(output['holdout_mean'].shape, (heldout,))


if __name__ == '__main__':
    unittest.main(verbosity=2)
