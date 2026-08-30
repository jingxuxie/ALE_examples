import numpy as np
from scipy.optimize import least_squares
from models import OMEGA


def spectrum_multi(parameters, bands):
    centers = -4.8 + 9.6 * parameters[:bands]
    widths = .45 + 1.05 * parameters[bands:2 * bands]
    skews = -1.5 + 3 * parameters[2 * bands:3 * bands]
    shapes = .2 + 1.4 * parameters[3 * bands:4 * bands]
    logits = np.r_[6 * (parameters[4 * bands:] - .5), 0.]
    weights = np.exp(logits - logits.max())
    weights /= weights.sum()
    scaled = (OMEGA[:, None] - centers) / widths
    inside = np.abs(scaled) < 1
    base = np.maximum(1 - scaled**2, 1e-100)
    profile = np.where(inside, base**shapes * np.exp(skews * np.clip(scaled, -1, 1)), 0)
    factor = np.where(inside, 1 / base, 0)
    localjac = profile[:, :, None] * np.stack((
        (2 * shapes * scaled * factor - skews) / widths * 9.6,
        (2 * shapes * scaled**2 * factor - skews * scaled) / widths * 1.05,
        scaled * 3, np.log(base) * 1.4), axis=2)
    total = profile.sum(axis=0)
    components = profile / total
    localjac = (localjac - components[:, :, None] * localjac.sum(axis=0)) / total[None, :, None]
    mass = components @ weights
    jacobian = np.column_stack([localjac[:, :, index] * weights for index in range(4)] + [6 * weights[:-1] * (components[:, :-1] - mass[:, None])])
    return mass, jacobian


class MultiObjective:
    def __init__(self, design, target, bands, strength):
        self.design = design
        self.target = target
        self.bands = bands
        self.prior = np.r_[np.zeros(bands), np.full(3 * bands, strength), np.full(bands - 1, strength * 2)]
        self.previous = None

    def calculate(self, parameters):
        if self.previous is None or not np.array_equal(parameters, self.previous):
            self.mass, derivative = spectrum_multi(parameters, self.bands)
            self.residual = np.r_[self.design @ self.mass - self.target, self.prior * (parameters - .5)]
            self.jacobian = np.vstack((self.design @ derivative, np.diag(self.prior)))
            self.previous = parameters.copy()

    def fun(self, parameters):
        self.calculate(parameters)
        return self.residual

    def jac(self, parameters):
        self.calculate(parameters)
        return self.jacobian


def initial_parameters(mass, bands, random, attempt):
    weights = np.ones(bands) / bands if attempt == 0 else random.dirichlet(np.full(bands, 5.))
    cumulative = np.cumsum(mass)
    quantiles = np.cumsum(weights) - weights / 2
    centers = np.interp(quantiles, cumulative, OMEGA)
    for iteration in range(8):
        partition = np.argmin((OMEGA[:, None] - centers)**2, axis=1)
        centers = np.array([np.sum(mass[partition == band] * OMEGA[partition == band]) / max(mass[partition == band].sum(), 1e-20) for band in range(bands)])
    weights = np.array([max(mass[partition == band].sum(), .005) for band in range(bands)])
    widths = np.array([np.sqrt(np.sum(mass[partition == band] * (OMEGA[partition == band] - centers[band])**2) / weights[band]) * 2.3 for band in range(bands)])
    logits = np.log(weights[:-1] / weights[-1])
    parameters = np.r_[(centers + 4.8) / 9.6, (widths - .45) / 1.05, np.full(2 * bands, .5), .5 + logits / 6]
    return np.clip(parameters, .001, .999)


def fit_multi(design, target, initialmass, strength=2, starts=3, max_nfev=120):
    random = np.random.default_rng(50)
    masses, criteria, chis = [], [], []
    for bands in [3, 4, 5]:
        objective = MultiObjective(design, target, bands, strength)
        for attempt in range(starts):
            initial = initial_parameters(initialmass, bands, random, attempt)
            fit = least_squares(objective.fun, initial, jac=objective.jac, bounds=(np.zeros(len(initial)), np.ones(len(initial))), max_nfev=max_nfev, ftol=1e-5, xtol=1e-5, gtol=1e-5)
            objective.calculate(fit.x)
            chi = np.sum((design @ objective.mass - target)**2)
            masses.append(objective.mass.copy())
            chis.append(chi)
            criteria.append(2 * fit.cost + 2 * bands)
    criteria = np.array(criteria)
    weights = np.exp(-.5 * (criteria - criteria.min()))
    weights /= weights.sum()
    return weights @ np.array(masses), np.array(masses), np.array(chis), criteria
