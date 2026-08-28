import unittest

import numpy as np

from cores import detect
from current import measure
from model import Model, imprint
from order import characterize
from propagate import Propagator


def make_model(nx=96, ny=80, length_x=14, length_y=12, **parameters):
    axis_x = (np.arange(nx) - nx / 2) * length_x / nx
    axis_y = (np.arange(ny) - ny / 2) * length_y / ny
    grid_x, grid_y = np.meshgrid(axis_x, axis_y)
    arrays = dict(x=axis_x, y=axis_y, potential=np.zeros_like(grid_x),
                  roi=(grid_x ** 2 + grid_y ** 2 < 25).astype(int),
                  bulk=grid_x ** 2 + grid_y ** 2 < 9)
    case = dict(g=0, omega=0, correlation_edges=[0, 2, 5, 30], spectrum_edges=[0, 1, 3, 100])
    case.update(parameters)
    return Model(case, arrays)


def phase_error(first, second, area):
    overlap = np.vdot(second, first)
    aligned = first * np.exp(-1j * np.angle(overlap))
    return float(np.sqrt(area * np.sum(np.abs(aligned - second) ** 2)))


class Validation(unittest.TestCase):
    def test_bilinear_winding_robustness(self):
        axis = np.array([0.0, 1.0])
        arrays = dict(x=axis, y=axis, roi=np.ones((2, 2), dtype=int),
                      bulk=np.ones((2, 2), dtype=bool), potential=np.zeros((2, 2)))
        model = Model(dict(g=0, omega=0, correlation_edges=[0, 10], spectrum_edges=[0, 100]), arrays)
        random = np.random.default_rng(813)
        for trial in range(300):
            psi = random.normal(size=(2, 2)) + 1j * random.normal(size=(2, 2))
            loop = [psi[0, 0], psi[0, 1], psi[1, 1], psi[1, 0], psi[0, 0]]
            winding = sum(np.angle(np.conj(first) * second) for first, second in zip(loop[:-1], loop[1:]))
            expected = int(np.rint(winding / (2 * np.pi)))
            if expected:
                cores = detect(psi, model)
                self.assertEqual(len(cores), 1)
                self.assertEqual(cores[0, 2], expected)

    def test_rectangular_plane_wave_and_shells(self):
        model = make_model()
        wave_x, wave_y = 4 * np.pi / 14, -2 * np.pi / 12
        psi = np.exp(1j * (wave_x * model.xx + wave_y * model.yy)) / np.sqrt(168)
        physics = measure(psi, model, 0)
        expected = (wave_x ** 2 + wave_y ** 2) / 2
        self.assertAlmostEqual(physics['norm'], 1, places=13)
        self.assertAlmostEqual(physics['energy'], expected, places=12)
        self.assertAlmostEqual(physics['Ei'], expected, places=12)
        self.assertLess(physics['Ec'], 1e-24)
        self.assertAlmostEqual(sum(physics['Ei_bins']), physics['Ei'], places=13)

    def test_longitudinal_flow(self):
        model = make_model()
        wave = 2 * np.pi / 14
        psi = np.exp(0.3j * np.sin(wave * model.xx)) / np.sqrt(168)
        physics = measure(psi, model, 0)
        self.assertAlmostEqual(physics['Ec'], 0.3 ** 2 * wave ** 2 / 4, places=13)
        self.assertLess(physics['Ei'], 1e-24)
        self.assertAlmostEqual(sum(physics['Ec_bins']), physics['Ec'], places=13)

    def test_real_amplitude_quantum_energy(self):
        model = make_model()
        psi = np.exp(-(model.xx ** 2 + model.yy ** 2)).astype(complex)
        physics = measure(psi, model, 0)
        self.assertAlmostEqual(physics['energy'], physics['Eq'], places=13)
        self.assertLess(physics['Ec'] + physics['Ei'], 1e-24)

    def test_signed_pair_and_density_dip(self):
        model = make_model()
        positive = [0.213, -0.427]
        negative = [-1.157, 0.339]
        psi = ((model.xx - positive[0] + 1j * (model.yy - positive[1]))
               * (model.xx - negative[0] - 1j * (model.yy - negative[1]))
               * np.exp(-(model.xx ** 2 + model.yy ** 2) / 4))
        cores = detect(psi, model)
        self.assertEqual(len(cores), 2)
        for expected, charge in [(positive, 1), (negative, -1)]:
            found = cores[cores[:, 2] == charge, :2]
            self.assertEqual(len(found), 1)
            self.assertLess(np.linalg.norm(found[0] - expected), 0.02)
        radius2 = model.xx ** 2 + model.yy ** 2
        real_dip = (0.001 + radius2 / (0.1 + radius2)) * np.exp(-radius2 / 4)
        self.assertEqual(len(detect(real_dip.astype(complex), model)), 0)

    def test_imprint_sum_and_no_density_edit(self):
        model = make_model()
        psi = (model.xx + 1j * model.yy) * np.exp(-(model.xx ** 2 + model.yy ** 2) / 2)
        erased = imprint(psi, model, [dict(x=0, y=0, charge=-1)])
        reversed_state = imprint(psi, model, [dict(x=0, y=0, charge=-2)])
        np.testing.assert_allclose(np.abs(erased), np.abs(psi), atol=1e-15)
        np.testing.assert_allclose(np.abs(reversed_state), np.abs(psi), atol=1e-15)
        self.assertEqual(len(detect(erased, model)), 0)
        self.assertEqual(detect(reversed_state, model)[0, 2], -1)

    def test_guarded_triangular_order(self):
        model = make_model(nx=160, ny=144)
        positions = np.asarray([(column + 0.5 * row, np.sqrt(3) * row / 2)
                                for row in range(-5, 6) for column in range(-7, 8)])
        positions = positions[model.sample(model.roi, positions) > 0]
        cores = np.column_stack((positions, np.ones(len(positions))))
        topology = characterize(cores, model)
        total = int(model.sample(model.bulk, positions).sum())
        self.assertEqual(topology['counts'][6], total)
        self.assertEqual(topology['defect_radius'], 0)
        for correlation, pairs in zip(topology['correlations'], topology['pair_counts']):
            if pairs:
                self.assertAlmostEqual(correlation, 1, places=13)
        self.assertEqual(sum(topology['pair_counts']), total * (total - 1) // 2)

    def test_annular_edges(self):
        model = make_model(nx=144, ny=128)
        radius2 = model.xx ** 2 + model.yy ** 2
        model.roi = ((radius2 > 2.75 ** 2) & (radius2 < 3.6 ** 2)).astype(int)
        model.bulk = model.roi > 0
        angles = np.arange(12) * 2 * np.pi / 12 + 0.03
        positions = 3 * np.column_stack((np.cos(angles), np.sin(angles)))
        topology = characterize(np.column_stack((positions, np.ones(len(positions)))), model)
        self.assertEqual(topology['counts'][2], 12)
        self.assertEqual(len(topology['edges']), 12)

    def test_cross_domain_correlation(self):
        model = make_model(nx=144, ny=128)
        model.roi = np.where(model.xx < -0.5, 1, np.where(model.xx > 0.5, 2, 0))
        model.bulk = model.roi > 0
        positions = np.array([[-3.2, -0.6], [-2.2, -0.6],
                              [2.2, -0.6], [2.2 + np.sqrt(3) / 2, -0.1]])
        topology = characterize(np.column_stack((positions, np.ones(4))), model)
        self.assertEqual(topology['counts'][1], 4)
        self.assertEqual(sum(topology['pair_counts']), 6)
        self.assertAlmostEqual(np.dot(topology['correlations'], topology['pair_counts']) / 6, -1 / 3, places=12)

    def test_exact_free_nonlinear_plane_wave(self):
        model = make_model(g=80)
        psi = 0.07 * np.exp(2j * np.pi * model.xx / 14)
        energy = (2 * np.pi / 14) ** 2 / 2 + 80 * 0.07 ** 2
        frames = Propagator(model).evolve(psi, [0, 0.017, 0.23], 0.008)
        np.testing.assert_allclose(frames[-1], psi * np.exp(-0.23j * energy), atol=2e-14)
        self.assertAlmostEqual(np.sum(abs(frames[-1]) ** 2), np.sum(abs(psi) ** 2), places=10)

    def test_rotating_coherent_state(self):
        model = make_model(nx=112, ny=96, length_x=18, length_y=16, omega=0.73)
        model.base = (model.xx ** 2 + model.yy ** 2) / 2
        center = np.array([0.7, -0.4])
        momentum = np.array([0.2, 0.6])
        psi = np.exp(-((model.xx - center[0]) ** 2 + (model.yy - center[1]) ** 2) / 2
                     + 1j * (momentum[0] * model.xx + momentum[1] * model.yy)) / np.sqrt(np.pi)
        time = 0.8
        angle = model.omega * time
        rotation = np.array([[np.cos(angle), np.sin(angle)], [-np.sin(angle), np.cos(angle)]])
        final_center = rotation @ (center * np.cos(time) + momentum * np.sin(time))
        final_momentum = rotation @ (momentum * np.cos(time) - center * np.sin(time))
        expected = np.exp(-((model.xx - final_center[0]) ** 2 + (model.yy - final_center[1]) ** 2) / 2
                          + 1j * (final_momentum[0] * model.xx + final_momentum[1] * model.yy)) / np.sqrt(np.pi)
        observed = Propagator(model).evolve(psi, [0, time], 0.008)[-1]
        self.assertLess(phase_error(observed, expected, model.area), 2e-8)

    def test_driven_temporal_order(self):
        drive = dict(amplitude=3, frequency=1.7, travel=0.8, center=[0.3, -0.2], width=0.9)
        model = make_model(nx=80, ny=72, g=80, omega=0.7, drive=drive)
        model.base = (0.8 * model.xx ** 2 + 1.3 * model.yy ** 2) / 2
        psi = np.exp(-(model.xx ** 2 + model.yy ** 2) / 2).astype(complex) / np.sqrt(np.pi)
        fine = Propagator(model).evolve(psi, [0, 0.16], 0.001)[-1]
        coarse = Propagator(model).evolve(psi, [0, 0.16], 0.008)[-1]
        medium = Propagator(model).evolve(psi, [0, 0.16], 0.004)[-1]
        self.assertGreater(phase_error(coarse, fine, model.area) / phase_error(medium, fine, model.area), 12)


if __name__ == '__main__':
    unittest.main(verbosity=2)
