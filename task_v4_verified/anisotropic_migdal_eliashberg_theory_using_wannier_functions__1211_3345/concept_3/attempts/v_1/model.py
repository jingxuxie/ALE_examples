import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.optimize import least_squares
from scipy.linalg import qr


RANGES = np.array([[[.65, 1.25], [1.8, 3.1], [0, 0]],
                   [[1., 1.8], [1.55, 2.6], [0, 0]],
                   [[.8, 1.5], [1.8, 2.9], [0, 0]],
                   [[.6, 1.2], [1.35, 2.1], [2.35, 3.2]]])
EDGES = np.array([0, .75, 1.25, 1.75, 2.25, 2.75, 3.5, 4.5, 6, 8, 10, 13, 17, 23, np.inf])


class Physics:
    def __init__(self, omega, nodes=12):
        self.omega = np.asarray(omega)[:, None]
        nodes, weights = leggauss(nodes)
        self.xi = (nodes[None, :] + 1) / 2
        self.measure = np.broadcast_to(weights[None, :] / 16, (8, len(nodes)))
        theta = 2 * np.pi * (np.arange(8) + .5) / 16
        self.cos2 = np.cos(2 * theta)[:, None]
        self.cos4 = np.cos(4 * theta)[:, None]
        self.coswidth = np.cos(2 * theta + .7)[:, None]
        self.cosrep = np.cos(2 * theta[None, :] + .3 * np.arange(3)[:, None])[:, :, None]

    def band_components(self, parameters, family, band, jacobian=False):
        latent = parameters[6 + 8 * band:14 + 8 * band]
        gap_range = RANGES[family, band]
        gap_scale = gap_range[1] - gap_range[0]
        gap_center = gap_range[0] + gap_scale * latent[0]
        anis_scale = .30 if family == 1 else .18
        anis = (.04 if family == 1 else .015) + anis_scale * latent[1]
        fourth = -.09 + .18 * latent[2]
        gap_shape = 1 + anis * self.cos2 + fourth * self.cos4
        gap = gap_center * gap_shape
        life_scale = .13 if family == 1 else .075
        life = .025 + life_scale * latent[3]
        angular_width = life * (1 + .55 * latent[4] * self.coswidth)
        bandwidth = 4.5 + 2.5 * latent[5]
        energy = np.sqrt(gap ** 2 + (bandwidth * self.xi) ** 2)
        coherence = gap / energy
        shifts = np.array([0, 3.2 + 2.3 * parameters[2], 6.7 + 3.3 * parameters[3]])
        dispersions = np.array([0, .1 + .5 * parameters[4], .15 + .75 * parameters[5]])
        centers = energy[None, :, :] + shifts[:, None, None] + dispersions[:, None, None] * self.cosrep[band]
        widths = angular_width[None, :, :] + .025 * self.xi ** 2 + .13 * np.arange(3)[:, None, None]
        first_scale, second_scale = (.18, .11) if family == 2 else (.13, .09)
        first = (.15 if family == 2 else .025) + first_scale * latent[6]
        second = (.07 if family == 2 else .01) + second_scale * latent[7]
        replicas = np.array([1 - first - second, first, second])
        measure = replicas[:, None, None] * self.measure
        coherences = np.broadcast_to(coherence, centers.shape)
        if not jacobian:
            return centers.ravel(), widths.ravel(), coherences.ravel(), measure.ravel()
        deriv_energy = np.zeros((12,) + centers.shape)
        deriv_width = np.zeros_like(deriv_energy)
        deriv_coherence = np.zeros_like(deriv_energy)
        deriv_measure = np.zeros_like(deriv_energy)
        deriv_energy[0, 1] = 2.3
        deriv_energy[1, 2] = 3.3
        deriv_energy[2, 1] = .5 * self.cosrep[band]
        deriv_energy[3, 2] = .75 * self.cosrep[band]
        gap_derivatives = [gap_scale * gap_shape, gap_center * anis_scale * self.cos2, gap_center * .18 * self.cos4]
        for index, derivative in enumerate(gap_derivatives):
            deriv_energy[4 + index] = coherence * derivative
            deriv_coherence[4 + index] = (1 - coherence ** 2) / energy * derivative
        deriv_width[7] = life_scale * (1 + .55 * latent[4] * self.coswidth)
        deriv_width[8] = life * .55 * self.coswidth
        deriv_energy[9] = 2.5 * bandwidth * self.xi ** 2 / energy
        deriv_coherence[9] = -coherence / energy * deriv_energy[9]
        deriv_measure[10, 0] = -first_scale * self.measure
        deriv_measure[10, 1] = first_scale * self.measure
        deriv_measure[11, 0] = -second_scale * self.measure
        deriv_measure[11, 2] = second_scale * self.measure
        return (centers.ravel(), widths.ravel(), coherences.ravel(), measure.ravel(),
                deriv_energy.reshape(12, -1).T, deriv_width.reshape(12, -1).T,
                deriv_coherence.reshape(12, -1).T, deriv_measure.reshape(12, -1).T)

    def forward(self, parameters, family, jacobian=True):
        bands = 3 if family == 3 else 2
        size = 6 + 8 * bands
        if bands == 2:
            first = .25 + .5 * parameters[0]
            mixture = np.array([first, 1 - first])
            deriv_mixture = np.array([[.5, 0], [-.5, 0]])
        else:
            first = .18 + .3 * parameters[0]
            fraction = .3 + .4 * parameters[1]
            mixture = np.array([first, (1 - first) * fraction, (1 - first) * (1 - fraction)])
            deriv_mixture = np.array([[.3, 0], [-.3 * fraction, .4 * (1 - first)], [-.3 * (1 - fraction), -.4 * (1 - first)]])
        projection = np.array([[1., 1., 1.], [.45, 1., 1.65]])[:, :bands]
        weight = projection * mixture
        totals = weight.sum(axis=1)
        weight /= totals[:, None]
        deriv_weight = projection[:, :, None] * deriv_mixture[None, :, :]
        deriv_weight = (deriv_weight - weight[:, :, None] * deriv_weight.sum(axis=1)[:, None, :]) / totals[:, None, None]
        values = np.zeros((2, 2, len(self.omega)))
        jac = np.zeros(values.shape + (size,))
        for band in range(bands):
            components = self.band_components(parameters, family, band, jacobian)
            energy, width, coherence, measure = components[:4]
            frequency = self.omega + width
            inverse = 1 / (frequency ** 2 + energy ** 2)
            diagonal = self.omega * frequency * inverse
            anomalous = self.omega * coherence * energy * inverse
            sheet = np.stack([diagonal @ measure, anomalous @ measure])
            values += weight[:, band, None, None] * sheet[None, :, :]
            if jacobian:
                deriv_energy, deriv_width, deriv_coherence, deriv_measure = components[4:]
                energy_weight = deriv_energy * measure[:, None]
                width_weight = deriv_width * measure[:, None]
                coherence_weight = deriv_coherence * measure[:, None]
                diagonal_jac = ((-2 * diagonal * energy * inverse) @ energy_weight
                                + (self.omega * (energy ** 2 - frequency ** 2) * inverse ** 2) @ width_weight
                                + diagonal @ deriv_measure)
                anomalous_jac = ((self.omega * coherence * (frequency ** 2 - energy ** 2) * inverse ** 2) @ energy_weight
                                 + (-2 * anomalous * frequency * inverse) @ width_weight
                                 + (self.omega * energy * inverse) @ coherence_weight + anomalous @ deriv_measure)
                band_jac = np.stack([diagonal_jac, anomalous_jac])
                locations = list(range(2, 6)) + list(range(6 + band * 8, 14 + band * 8))
                for probe in range(2):
                    jac[probe][:, :, locations] += weight[probe, band] * band_jac
                jac[..., :2] += sheet[None, :, :, None] * deriv_weight[:, band, None, None, :]
        return (values, jac) if jacobian else values

    def target(self, parameters, family):
        result = np.zeros((3, 14))
        for band in range(3 if family == 3 else 2):
            energy, width, coherence, measure = self.band_components(parameters, family, band)
            cumulative = (np.arctan((EDGES[:, None] - energy) / (width + .06))
                          + np.arctan((EDGES[:, None] + energy) / (width + .06))) / np.pi
            result[band] = np.diff(cumulative, axis=0) @ measure
        return result


def whiten(values, sigma, jacobian=False):
    if jacobian:
        standardized = values / sigma[..., None]
        result = standardized.copy()
        result[..., 1:, :] = (standardized[..., 1:, :] - .4 * standardized[..., :-1, :]) / np.sqrt(.84)
    else:
        standardized = values / sigma
        result = standardized.copy()
        result[..., 1:] = (standardized[..., 1:] - .4 * standardized[..., :-1]) / np.sqrt(.84)
    return result


class InterpolatedPhysics(Physics):
    def __init__(self, omega, nodes=10, frequencies=20):
        frequency = np.asarray(omega)[:, None]
        energies = np.geomspace(.28, 24., 100)
        widths = np.array([.015, .06, .15, .3, .5])
        energy = np.tile(energies, len(widths))
        width = np.repeat(widths, len(energies))
        shifted = frequency + width
        inverse = 1 / (shifted ** 2 + energy ** 2)
        kernels = np.concatenate([frequency * shifted * inverse, frequency * energy * inverse], axis=1)
        basis, singular, right = np.linalg.svd(kernels, full_matrices=False)
        basis = basis[:, :frequencies]
        selected = qr(basis.T, mode='economic', pivoting=True)[2][:frequencies]
        self.interpolation = basis @ np.linalg.inv(basis[selected])
        self.selected = selected
        super().__init__(np.asarray(omega)[selected], nodes)

    def forward(self, parameters, family, jacobian=True):
        if jacobian:
            values, derivatives = super().forward(parameters, family, True)
            values = values @ self.interpolation.T
            derivatives = np.einsum('ij,pcjk->pcik', self.interpolation, derivatives)
            return values, derivatives
        return super().forward(parameters, family, False) @ self.interpolation.T


class Fit:
    def __init__(self, physics, observed, sigma, family, penalty=3.):
        self.physics = physics
        self.observed = observed
        self.sigma = sigma
        self.family = family
        self.penalty = penalty
        self.active = np.arange(30 if family == 3 else 22)
        if family != 3:
            self.active = self.active[self.active != 1]
        self.last = None

    def evaluate(self, active):
        if self.last is not None and np.array_equal(active, self.last):
            return
        self.last = active.copy()
        parameters = np.full(32, .5)
        parameters[self.active] = active
        values, jacobian = self.physics.forward(parameters, self.family)
        self.residual = np.concatenate([whiten(values - self.observed, self.sigma).ravel(), self.penalty * (active - .5)])
        self.jacobian = np.concatenate([whiten(jacobian, self.sigma, True).reshape(-1, jacobian.shape[-1])[:, self.active], self.penalty * np.eye(len(active))])

    def fun(self, active):
        self.evaluate(active)
        return self.residual

    def jac(self, active):
        self.evaluate(active)
        return self.jacobian

    def run(self, initial=None, max_nfev=45):
        if initial is None:
            initial = np.full(len(self.active), .5)
        fit = least_squares(self.fun, initial, jac=self.jac, bounds=(0., 1.), max_nfev=max_nfev, ftol=2e-5, gtol=1e-4, xtol=1e-5)
        parameters = np.full(32, .5)
        parameters[self.active] = fit.x
        return parameters, fit
