import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from scipy.linalg import eigh, eigvalsh, solve

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))

import bdg


class PhysicsTests(unittest.TestCase):
    def setUp(self):
        self.scene = bdg.draw_scene(531, "crowded")
        self.actions = bdg.uniform_actions(12, 35)

    def test_hermiticity_and_particle_hole(self):
        identity = np.eye(64)
        zero = np.zeros((64, 64))
        conjugation = np.block([[zero, identity], [-identity, zero]])
        for vortices in ([], [4], [1, 8]):
            matrix = bdg.hamiltonian(bdg.potential_of(self.scene), vortices)
            np.testing.assert_allclose(matrix, matrix.conj().T, atol=1e-14)
            np.testing.assert_allclose(conjugation @ matrix.conj() @ conjugation.conj().T, -matrix, atol=1e-14)
            spectrum = eigvalsh(matrix)
            np.testing.assert_allclose(spectrum, -spectrum[::-1], atol=2e-13)

    def test_direct_resolvent_and_table(self):
        values = bdg.simulate(self.scene, self.actions)
        np.testing.assert_allclose(values, bdg.resolvent_ldos(self.scene, self.actions), atol=2e-12)
        table = bdg.ldos_table(self.scene)
        selected = [table[action["site"], action["energy_index"]] for action in self.actions]
        np.testing.assert_allclose(values, selected, atol=2e-12)
        self.assertTrue(np.all(table > 0))

    def test_normal_limit(self):
        potential = bdg.potential_of(self.scene)
        matrix = bdg.hamiltonian(potential, [], gap=0.0)
        normal = matrix[:64, :64]
        expected = np.sort(np.concatenate((eigvalsh(normal), -eigvalsh(normal))))
        np.testing.assert_allclose(eigvalsh(matrix), expected, atol=2e-13)
        for energy in (-1.4, 0.0, 0.83):
            broad = energy + 1j * bdg.SPEC["broadening"]
            normal_green = solve(broad * np.eye(64) - normal, np.eye(64))
            full_green = solve(broad * np.eye(128) - matrix, np.eye(128))
            np.testing.assert_allclose(np.diag(normal_green), np.diag(full_green)[:64], atol=2e-12)

    def test_uniform_analytic_limit(self):
        momenta = np.pi * np.arange(1, 9) / 9
        normal = (-2 * np.cos(momenta[:, None]) - 2 * np.cos(momenta[None, :]) - bdg.SPEC["chemical_potential"]).ravel()
        quasiparticle = np.sqrt(normal ** 2 + bdg.SPEC["gap"] ** 2)
        expected = np.sort(np.concatenate((quasiparticle, -quasiparticle)))
        matrix = bdg.hamiltonian(np.zeros(64), [])
        np.testing.assert_allclose(eigvalsh(matrix), expected, atol=2e-13)
        eta = bdg.SPEC["broadening"]
        for action, observed in zip(self.actions, bdg.simulate({"impurities": [], "vortices": []}, self.actions)):
            row, column = divmod(action["site"], 8)
            weight = (4 / 81 * (np.sin((row + 1) * momenta[:, None]) * np.sin((column + 1) * momenta[None, :])) ** 2).ravel()
            coherence = 0.5 * (1 + normal / quasiparticle)
            energy = bdg.SPEC["energies"][action["energy_index"]]
            expected_ldos = np.sum(weight * eta / np.pi * (coherence / ((energy - quasiparticle) ** 2 + eta ** 2)
                                                         + (1 - coherence) / ((energy + quasiparticle) ** 2 + eta ** 2)))
            self.assertAlmostEqual(observed, expected_ldos, places=12)

    def test_global_phase_and_time_reversal(self):
        potential = bdg.potential_of(self.scene)
        spectra = []
        for phase, winding in ((0, 1), (1.37, 1), (0, -1)):
            eigenvalues, eigenvectors = eigh(bdg.hamiltonian(potential, [1, 7], phase=phase, winding=winding))
            energy = np.asarray(bdg.SPEC["energies"])
            eta = bdg.SPEC["broadening"]
            spectra.append(abs(eigenvectors[:64]) ** 2 @ (eta / (np.pi * ((energy[None, :] - eigenvalues[:, None]) ** 2 + eta ** 2))))
        np.testing.assert_allclose(spectra[0], spectra[1], atol=3e-12)
        np.testing.assert_allclose(spectra[0], spectra[2], atol=3e-12)

    def test_jacobian(self):
        potential = bdg.potential_of(self.scene)
        _, gradient = bdg.predict_potential(potential, [1, 7], self.actions, jacobian=True)
        for column, site in enumerate(bdg.SPEC["impurity_sites"]):
            positive, negative = potential.copy(), potential.copy()
            positive[site] += 1e-5
            negative[site] -= 1e-5
            finite = (bdg.predict_potential(positive, [1, 7], self.actions)
                      - bdg.predict_potential(negative, [1, 7], self.actions)) / 2e-5
            np.testing.assert_allclose(gradient[:, column], finite, atol=3e-8, rtol=2e-6)

    def test_spectral_weight(self):
        _, eigenvectors = eigh(bdg.hamiltonian(bdg.potential_of(self.scene), [3]))
        np.testing.assert_allclose(np.sum(abs(eigenvectors[:64]) ** 2, axis=1), np.ones(64), atol=2e-13)

    def test_constraints(self):
        for action in ({"type": "query", "site": True, "energy_index": 1},
                       {"type": "query", "site": 64, "energy_index": 1},
                       {"type": "query", "site": 1.0, "energy_index": 1},
                       {"type": "query", "site": 0, "energy_index": 41},
                       {"type": "query", "site": 1, "energy_index": -1},
                       {"type": "query", "site": 1, "energy_index": 1, "batch": []}):
            with self.assertRaises(ValueError):
                bdg.validate_action(action)
        for mutation in ("duplicate", "edge", "nan", "small", "vortex_duplicate", "vortex_signed"):
            scene = json.loads(json.dumps(self.scene))
            if mutation == "duplicate":
                scene["impurities"][1]["site"] = scene["impurities"][0]["site"]
            elif mutation == "edge":
                scene["impurities"][0]["site"] = 0
            elif mutation == "nan":
                scene["impurities"][0]["strength"] = float("nan")
            elif mutation == "small":
                scene["impurities"][0]["strength"] = 0.1
            elif mutation == "vortex_duplicate":
                scene["vortices"] = [1, 1]
            else:
                scene["vortices"] = [-1]
            with self.assertRaises(ValueError):
                bdg.validate_scene(scene)
        with self.assertRaises(ValueError):
            bdg.hamiltonian(np.zeros(65), [])
        with self.assertRaises(ValueError):
            bdg.hamiltonian(np.full(64, np.nan), [])
        with self.assertRaises(ValueError):
            bdg.hamiltonian(np.zeros(64), [], gap=-0.1)

    def test_prior_and_frozen_assets(self):
        for family in bdg.SPEC["families"]:
            for seed in range(40):
                scene = bdg.draw_scene(seed, family)
                self.assertEqual(scene, bdg.draw_scene(seed, family))
                bdg.validate_scene(scene)
        self.assertEqual(len(bdg.sectors()), 46)
        public = ROOT / "participant" / "workspace" / "bdg.py"
        trusted = ROOT / "evaluator" / "hidden" / "forward_model.py"
        self.assertEqual(public.read_bytes(), trusted.read_bytes())
        self.assertEqual(json.loads((ROOT / "participant" / "input" / "model.json").read_text()), bdg.SPEC)
        manifest = json.loads((ROOT / "evaluator" / "hidden" / "frozen_manifest.json").read_text())
        for filename, expected in manifest["sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / filename).read_bytes()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
