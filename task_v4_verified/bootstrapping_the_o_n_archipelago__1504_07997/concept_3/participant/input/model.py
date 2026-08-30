"""Public reduced positive matrix Laplace measure; not full CFT crossing."""

from dataclasses import dataclass
import math

import numpy as np


VERSION = "radial-design-v1"
BUDGET = 72
TIME_RANGE = (0.25, 6.0)
FAMILIES = (
    "regular", "dark_state", "near_degenerate", "aligned_residues",
    "weak_low", "tail_nuisance",
)
TARGETS = ("delta0", "log_gap", "log_a0", "theta0")
SCALES = np.array([0.05, 0.35, 0.25, 0.15])
TAIL_EDGE = 3.0


def canonical_angle(angle):
    return (angle + math.pi / 2) % math.pi - math.pi / 2


def direction(angle):
    return np.array([math.cos(angle), math.sin(angle)])


def noise_std(time):
    return 1.2e-5 + 2.5e-4 * np.exp(-1.1 * np.asarray(time))


@dataclass
class Instance:
    family: str
    delta0: float
    gap: float
    a0: float
    a1: float
    theta0: float
    theta1: float
    tail_energies: np.ndarray
    tail_vectors: np.ndarray
    continuum_matrix: np.ndarray
    continuum_scale: float
    continuum_shape: int

    def matrix(self, time):
        low0 = direction(self.theta0)
        low1 = direction(self.theta1)
        result = self.a0 * np.exp(-self.delta0 * time) * np.outer(low0, low0)
        result += self.a1 * np.exp(-(self.delta0 + self.gap) * time) * np.outer(low1, low1)
        weights = np.exp(-self.tail_energies * time)
        result += (self.tail_vectors.T * weights) @ self.tail_vectors
        result += self.continuum_matrix * np.exp(-TAIL_EDGE * time) / (
            1 + self.continuum_scale * time
        ) ** self.continuum_shape
        return result

    def mean(self, time, probe):
        probe = np.asarray(probe, dtype=float)
        return float(probe @ self.matrix(time) @ probe)

    def target(self):
        return np.array([
            self.delta0, math.log(self.gap), math.log(self.a0), self.theta0,
        ])


def generate(seed, family):
    if family not in FAMILIES:
        raise ValueError("unknown public family")
    rng = np.random.default_rng(seed)

    def uniform(lower, upper):
        return float(rng.uniform(lower, upper))

    def loguniform(lower, upper):
        return math.exp(uniform(math.log(lower), math.log(upper)))

    delta0 = uniform(0.8, 1.15)
    gap = uniform(0.35, 0.8)
    a0 = loguniform(0.5, 1.4)
    a1 = loguniform(0.5, 1.5)
    theta0 = uniform(-math.pi / 2, math.pi / 2)
    sign = int(rng.choice([-1, 1]))
    separation = uniform(0.45, 1.25)
    tail_mass = loguniform(0.4, 2.0)
    if family == "dark_state":
        a0 = loguniform(0.15, 0.4)
        a1 = loguniform(1.2, 2.0)
        separation = math.pi / 2 + uniform(-0.06, 0.06)
    elif family == "near_degenerate":
        gap = uniform(0.045, 0.12)
        separation = uniform(0.65, 1.3)
    elif family == "aligned_residues":
        gap = uniform(0.45, 0.8)
        separation = uniform(0.075, 0.18)
        a0 = loguniform(0.5, 1.2)
        a1 = loguniform(0.6, 1.8)
    elif family == "weak_low":
        gap = uniform(0.5, 0.85)
        separation = uniform(0.55, 1.25)
        a0 = loguniform(0.045, 0.1)
        a1 = loguniform(0.9, 1.8)
    elif family == "tail_nuisance":
        tail_mass = loguniform(4.0, 10.0)
    theta1 = canonical_angle(theta0 + sign * separation)
    atom_count = int(rng.integers(4, 11))
    continuum_fraction = uniform(0.15, 0.45)
    atom_weights = rng.dirichlet(np.full(atom_count, 0.7))
    atom_weights *= tail_mass * (1 - continuum_fraction)
    energies = rng.uniform(TAIL_EDGE, 8.0, atom_count)
    energies[0] = uniform(TAIL_EDGE, TAIL_EDGE + 0.3)
    angles = rng.uniform(-math.pi / 2, math.pi / 2, atom_count)
    vectors = np.sqrt(atom_weights)[:, None] * np.stack(
        [np.cos(angles), np.sin(angles)], axis=1,
    )
    continuum_angle = uniform(-math.pi / 2, math.pi / 2)
    continuum_vector = direction(continuum_angle)
    complement = direction(continuum_angle + math.pi / 2)
    eigen_fraction = uniform(0.1, 0.5)
    continuum_matrix = tail_mass * continuum_fraction * (
        eigen_fraction * np.outer(continuum_vector, continuum_vector)
        + (1 - eigen_fraction) * np.outer(complement, complement)
    )
    return Instance(
        family, delta0, gap, a0, a1, theta0, theta1, energies, vectors,
        continuum_matrix, uniform(0.35, 0.9), int(rng.integers(1, 4)),
    )


class Oracle:
    def __init__(self, instance, noise_seed):
        self.instance = instance
        self.rng = np.random.default_rng(noise_seed)
        self.used = 0

    def measure(self, time, probe):
        if self.used >= BUDGET:
            raise ValueError("budget exhausted")
        self.used += 1
        sigma = float(noise_std(time))
        value = self.instance.mean(time, probe) + sigma * self.rng.standard_normal()
        return {
            "type": "observation", "index": self.used, "y": float(value),
            "sigma": sigma, "remaining": BUDGET - self.used,
        }
