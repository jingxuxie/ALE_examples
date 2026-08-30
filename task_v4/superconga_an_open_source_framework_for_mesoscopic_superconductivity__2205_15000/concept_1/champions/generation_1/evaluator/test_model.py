import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/input"))
from gl_model import GLModel, load_case
from independent import checked_field, energy_gradient, lower_bound


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = load_case(ROOT / "participant/input/cases/dev_perforated.json")

    def test_directional_derivatives(self):
        generator = np.random.default_rng(8991)
        model = self.model
        vector = generator.normal(size=2 * model.size) * 0.65
        energy, gradient = model.objective(vector)
        errors = []
        for unused in range(8):
            direction = generator.normal(size=vector.size)
            direction /= np.linalg.norm(direction)
            exact = float(np.dot(gradient, direction))
            numeric = (model.objective(vector + 1e-5 * direction)[0] - model.objective(vector - 1e-5 * direction)[0]) / 2e-5
            errors.append(abs(numeric - exact) / max(1, abs(exact)))
        self.assertLess(max(errors), 2e-7)

    def test_coordinate_derivatives(self):
        model = self.model
        generator = np.random.default_rng(81)
        vector = generator.normal(size=model.size * 2) * 0.7
        unused, gradient = model.objective(vector)
        for coordinate in generator.choice(vector.size, 20, replace=False):
            plus, minus = vector.copy(), vector.copy()
            plus[coordinate] += 2e-5
            minus[coordinate] -= 2e-5
            numeric = (model.objective(plus)[0] - model.objective(minus)[0]) / 4e-5
            self.assertAlmostEqual(numeric, gradient[coordinate], delta=2e-7)

    def test_independent_energy_and_gradient(self):
        generator = np.random.default_rng(9201)
        for case_path in sorted((ROOT / "participant/input/cases").glob("*.json")):
            model = load_case(case_path)
            field = (generator.normal(size=model.shape) + 1j * generator.normal(size=model.shape)) * model.mask
            expected, gradient = model.energy_gradient(field)
            actual, other, rms = energy_gradient(model.case, field)
            self.assertAlmostEqual(expected, actual, delta=1e-9)
            np.testing.assert_allclose(gradient, other, atol=4e-14, rtol=1e-13)
            self.assertAlmostEqual(rms, model.gradient_rms(field), places=12)
            self.assertGreaterEqual(actual + 1e-8, lower_bound(model.case))

    def test_local_gauge_covariance(self):
        model = self.model
        generator = np.random.default_rng(1123)
        field = model.unpack(generator.normal(size=model.size * 2))
        gauge = generator.uniform(-4 * np.pi, 4 * np.pi, size=model.shape)
        transformed = copy.deepcopy(model.case)
        transformed["ax"] = (model.ax + gauge[:, 1:] - gauge[:, :-1]).tolist()
        transformed["ay"] = (model.ay + gauge[1:, :] - gauge[:-1, :]).tolist()
        other = GLModel(transformed)
        energy, gradient = model.energy_gradient(field)
        result, result_gradient = other.energy_gradient(field * np.exp(1j * gauge))
        self.assertAlmostEqual(energy, result, delta=1e-9)
        np.testing.assert_allclose(result_gradient, gradient * np.exp(1j * gauge), atol=2e-12)
        independent_energy = energy_gradient(transformed, field * np.exp(1j * gauge))[0]
        self.assertAlmostEqual(energy, independent_energy, delta=1e-9)

    def test_uniform_zero_field_with_holes(self):
        case = copy.deepcopy(self.model.case)
        shape = self.model.shape
        case["alpha"] = (-np.ones(shape)).tolist()
        case["beta"] = np.ones(shape).tolist()
        case["ax"] = np.zeros_like(self.model.ax).tolist()
        case["ay"] = np.zeros_like(self.model.ay).tolist()
        model = GLModel(case)
        field = model.mask * np.exp(0.73j)
        energy, gradient = model.energy_gradient(field)
        self.assertAlmostEqual(energy, -0.5 * model.h**2 * model.size, places=10)
        self.assertAlmostEqual(energy, lower_bound(case), places=10)
        self.assertLess(np.max(np.abs(gradient)), 1e-14)
        self.assertEqual(model.energy(np.zeros(shape, dtype=complex)), 0)

    def test_inactive_sites_do_not_create_links(self):
        model = self.model
        field = model.initial.copy()
        expected, gradient = model.energy_gradient(field)
        field[~model.mask] = 20 + 13j
        actual, other = model.energy_gradient(field)
        self.assertEqual(expected, actual)
        np.testing.assert_array_equal(gradient, other)

    def test_physical_flux_and_positive_stiffness(self):
        specifications = json.loads((ROOT / "evaluator/hidden/generation.json").read_text())
        for details in specifications:
            directory = ROOT / ("participant/input/cases" if details["development"] else "evaluator/hidden/cases")
            model = load_case(directory / (details["case_id"] + ".json"))
            ny, nx = model.shape
            columns = np.arange(nx, dtype=float) - (nx - 1) / 2
            modulation = details["magnetic_field"] * 0.12 * model.h**2 * nx / (2 * np.pi) * np.sin(2 * np.pi * columns / nx)
            expected = details["magnetic_field"] * model.h**2 + np.diff(modulation)
            actual = model.ax[:-1] + model.ay[:, 1:] - model.ax[1:] - model.ay[:, :-1]
            full = model.mask[:-1, :-1] & model.mask[1:, :-1] & model.mask[:-1, 1:] & model.mask[1:, 1:]
            np.testing.assert_allclose(actual[full], np.broadcast_to(expected, actual.shape)[full], atol=2e-14)
            self.assertGreater(np.min(np.asarray(model.case["kx"])), 0)
            self.assertGreater(np.min(np.asarray(model.case["ky"])), 0)

    def test_safe_output_validation(self):
        model = self.model
        with tempfile.TemporaryDirectory(dir=ROOT / "attempts") as directory:
            path = Path(directory) / "result.npz"
            np.savez_compressed(path, psi=model.initial)
            np.testing.assert_array_equal(checked_field(path, model.case), model.initial)
            for invalid in [model.initial.real, model.initial.ravel(), np.full(model.shape, np.nan + 1j)]:
                np.savez(path, psi=invalid)
                with self.assertRaises(ValueError):
                    checked_field(path, model.case)
            np.savez(path, psi=model.initial, energy=0)
            with self.assertRaises(ValueError):
                checked_field(path, model.case)
            np.savez(path, psi=np.full(model.shape, object()))
            with self.assertRaises(ValueError):
                checked_field(path, model.case)
            path.unlink()
            path.symlink_to(ROOT / "participant/input/cases/dev_pinning.json")
            with self.assertRaises(OSError):
                checked_field(path, model.case)


if __name__ == "__main__":
    unittest.main(verbosity=2)
