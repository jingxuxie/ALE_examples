import itertools
import json
import sys
import time
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'participant' / 'workspace'))
sys.path.insert(0, str(ROOT / 'evaluator'))
sys.path.insert(0, str(ROOT / 'adversary'))
from atlas import Atlas
from evaluate import aggregate, validate_result
from generate import direct_flux, reference_frames


def independent_score(metadata, arrays, choices):
    nx, ny = metadata['nx'], metadata['ny']
    losses, cherns, magnitudes, margins = [], [], [], []
    for scenario, specification in enumerate(metadata['scenarios']):
        bases = [np.linalg.qr(arrays['frames'][scenario, vertex, choice])[0] for vertex, choice in enumerate(choices)]
        energies = np.array([arrays['energies'][scenario, vertex, choice] for vertex, choice in enumerate(choices)])
        unary = np.mean((energies - arrays['guide'][scenario]) ** 2, axis=1).sum()
        overlap, dispersion, flux_loss, total_flux = 0.0, 0.0, 0.0, 0.0
        for vertical in range(ny):
            for horizontal in range(nx):
                vertex = vertical * nx + horizontal
                right = vertical * nx + (horizontal + 1) % nx
                top = ((vertical + 1) % ny) * nx + horizontal
                diagonal = ((vertical + 1) % ny) * nx + (horizontal + 1) % nx
                for neighbor in [right, top]:
                    magnitude = abs(np.linalg.det(bases[vertex].conj().T @ bases[neighbor]))
                    magnitudes.append(magnitude)
                    overlap -= np.log(max(magnitude * magnitude, 1e-30))
                    dispersion += np.mean((energies[vertex] - energies[neighbor]) ** 2)
                loop = np.eye(2, dtype=complex)
                corners = [vertex, right, diagonal, top, vertex]
                for source, destination in zip(corners[:-1], corners[1:]):
                    loop = loop @ (bases[source].conj().T @ bases[destination])
                flux = np.angle(np.linalg.det(loop))
                margins.append(np.pi - abs(flux))
                error = np.angle(np.exp(1j * (flux - arrays['target_flux'][scenario, vertex])))
                flux_loss += error ** 2
                total_flux += flux
        losses.append(float(np.dot(specification['loss_weights'], [unary, overlap, dispersion, flux_loss])))
        cherns.append(total_flux / (2 * np.pi))
    normalized = np.array(losses) / [row['normalizer'] for row in metadata['scenarios']]
    weights = np.array([row['weight'] for row in metadata['scenarios']])
    objective = normalized.max() + metadata['lambda_mean'] * np.dot(weights, normalized) / weights.sum()
    cost = sum(int(arrays['costs'][vertex, choice]) for vertex, choice in enumerate(choices))
    feasible = cost <= metadata['budget'] and min(magnitudes) >= metadata['minimum_link'] and min(margins) >= metadata['branch_margin']
    feasible &= all(abs(chern - row['target_chern']) <= metadata['chern_tolerance'] for chern, row in zip(cherns, metadata['scenarios']))
    feasible &= all(choices[int(vertex)] == choice for vertex, choice in metadata['anchors'].items())
    return float(objective), bool(feasible), cherns


class AtlasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = ROOT / 'participant' / 'input' / 'gap_hotspots_0'
        cls.metadata = json.loads((cls.directory / 'case.json').read_text())
        with np.load(cls.directory / 'arrays.npz', allow_pickle=False) as archive:
            cls.arrays = {name: archive[name] for name in archive.files}

    def test_independent_wilson_product(self):
        atlas = Atlas(self.metadata, self.arrays)
        random = np.random.default_rng(44)
        for choices in [self.arrays['seed_choices'], self.arrays['baseline_choices'], random.integers(0, 4, atlas.vertices)]:
            actual = atlas.score(choices)
            objective, feasible, chern = independent_score(self.metadata, self.arrays, choices)
            self.assertAlmostEqual(actual['objective'], objective, places=11)
            self.assertEqual(actual['feasible'], feasible)
            np.testing.assert_allclose(actual['chern'], chern, atol=1e-10)

    def test_nonunitary_frame_gauge(self):
        random = np.random.default_rng(95)
        changes = random.normal(size=self.arrays['frames'].shape[:3] + (2, 2)) + 1j * random.normal(size=self.arrays['frames'].shape[:3] + (2, 2))
        changes += 4 * np.eye(2)
        transformed = dict(self.arrays, frames=self.arrays['frames'] @ changes)
        original = Atlas(self.metadata, self.arrays).score(self.arrays['baseline_choices'])
        altered = Atlas(self.metadata, transformed).score(self.arrays['baseline_choices'])
        self.assertEqual(original['feasible'], altered['feasible'])
        self.assertAlmostEqual(original['objective'], altered['objective'], places=10)
        np.testing.assert_allclose(original['chern'], altered['chern'], atol=1e-10)

    def test_common_ambient_unitary(self):
        random = np.random.default_rng(57)
        unitary = np.linalg.qr(random.normal(size=(6, 6)) + 1j * random.normal(size=(6, 6)))[0]
        transformed = dict(self.arrays, frames=unitary @ self.arrays['frames'])
        original = Atlas(self.metadata, self.arrays).score(self.arrays['baseline_choices'])
        altered = Atlas(self.metadata, transformed).score(self.arrays['baseline_choices'])
        self.assertAlmostEqual(original['objective'], altered['objective'], places=11)
        np.testing.assert_allclose(original['chern'], altered['chern'], atol=1e-10)

    def test_small_complete_enumeration(self):
        random = np.random.default_rng(119)
        metadata = dict(self.metadata, nx=3, ny=2, budget=4, anchors={})
        metadata['scenarios'] = [dict(row, normalizer=1, target_chern=0) for row in self.metadata['scenarios'][:2]]
        frames = np.eye(4, 2) + 0.18 * (random.normal(size=(2, 6, 2, 4, 2)) + 1j * random.normal(size=(2, 6, 2, 4, 2)))
        arrays = {'frames': frames, 'energies': random.normal(size=(2, 6, 2, 2)), 'costs': np.tile([0, 1], (6, 1)),
                  'guide': np.zeros((2, 6, 2)), 'target_flux': np.zeros((2, 6)), 'seed_choices': np.zeros(6, dtype=int)}
        atlas = Atlas(metadata, arrays)
        selections = np.array(list(itertools.product(range(2), repeat=6)))
        batched = atlas.evaluate_many(selections)
        independent = [independent_score(metadata, arrays, choices) for choices in selections]
        np.testing.assert_allclose(batched['objective'], [row[0] for row in independent], atol=1e-10)
        np.testing.assert_array_equal(batched['feasible'], [row[1] for row in independent])
        selected = np.argmin(np.where(batched['feasible'], batched['objective'], np.inf))
        exact = min((row[0], index) for index, row in enumerate(independent) if row[1])[1]
        self.assertEqual(selected, exact)

    def test_all_frozen_starts_and_mesh_refinement(self):
        for split in ['participant/input', 'evaluator/hidden/cases']:
            base = ROOT / split
            for case in json.loads((base / 'manifest.json').read_text())['cases']:
                atlas = Atlas.load(base / case['directory'])
                self.assertTrue(atlas.score(atlas.seed)['feasible'])
                with np.load(base / case['directory'] / 'arrays.npz', allow_pickle=False) as archive:
                    self.assertTrue(atlas.score(archive['baseline_choices'])['feasible'])
                for scenario in range(atlas.scenarios):
                    frames = reference_frames(2 * atlas.metadata['nx'], 2 * atlas.metadata['ny'], atlas.metadata['parameters'], scenario)[0]
                    flux = direct_flux(frames, 2 * atlas.metadata['nx'], 2 * atlas.metadata['ny'])
                    self.assertAlmostEqual(float(flux.sum() / (2 * np.pi)), atlas.targets[scenario], places=10)

    def test_constraints_and_output_validation(self):
        atlas = Atlas(self.metadata, self.arrays)
        baseline = self.arrays['baseline_choices'].tolist()
        broken = dict(self.metadata, budget=atlas.score(baseline)['cost'] - 1)
        self.assertFalse(Atlas(broken, self.arrays).score(baseline)['feasible'])
        for result in [{'choices': [True] * atlas.vertices}, {'choices': baseline, 'objective': 0}, {'choices': [-1] * atlas.vertices}, {'choices': []}]:
            with self.assertRaises(ValueError):
                validate_result(result, atlas)

    def test_scoring_does_not_average_away_bad_family(self):
        policy = {'mean_gain_min': 0.12, 'worst_family_gain_min': 0.08, 'minimum_case_gain': 0}
        rows = [{'family': 'good', 'gain': 0.5, 'feasible': True}, {'family': 'bad', 'gain': 0.01, 'feasible': True}]
        self.assertFalse(aggregate(rows, policy)['passed'])
        rows[1]['gain'] = 0.10
        self.assertTrue(aggregate(rows, policy)['passed'])


if __name__ == '__main__':
    started = time.monotonic()
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    report = {'passed': result.wasSuccessful(), 'tests_run': result.testsRun,
              'failures': [str(test) for test, traceback in result.failures],
              'errors': [str(test) for test, traceback in result.errors],
              'runtime_seconds': time.monotonic() - started,
              'independent_enumeration_size': 64,
              'checks': ['direct matrix-Wilson-product scorer agrees with cached determinant factors',
                         'independent GL(2,C) frame changes preserve objective and topology',
                         'common ambient unitary preserves objective and topology',
                         'all 64 small-torus assignments independently enumerated',
                         'all public/hidden starts feasible and reference Chern stable at twice mesh density',
                         'budget/output-schema rejection and worst-family aggregation tested']}
    (ROOT / 'adversary' / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
