import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import importlib.util
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
from scipy.special import expit, logsumexp

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODULE_SPEC = importlib.util.spec_from_file_location("frozen_generation3_physics", ROOT / "evaluator/physics.py")
PHYSICS = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(PHYSICS)
SPEC = json.loads((ROOT / "participant/input/spec.json").read_text())
SPINS = PHYSICS.enumerate_spins(16)
HALF = SPINS[::2]
LOWER = np.tril_indices(16, -1)
EDGES = PHYSICS.torus_edges()
FEATURES = np.column_stack([HALF[:, first] * HALF[:, second] for first, second in EDGES])
BOUND = math.log(99) - 1e-9


class Problem:
    def __init__(self, document, gradient_weight):
        self.document = document
        self.spins = HALF[:, document["order"]]
        self.energy = -sum(coupling * HALF[:, first] * HALF[:, second] for coupling, (first, second) in zip(document["bonds"], EDGES))
        distance = np.count_nonzero(HALF != document["pattern"], axis=1)
        self.sector = (np.minimum(distance, 16 - distance) <= document["radius"]).astype(float)
        self.gradient_weight = gradient_weight
        self.last = None
        self.calls = 0
        self.deadline = math.inf

    def calculate(self, parameters):
        if time.monotonic() >= self.deadline:
            raise TimeoutError("bounded local optimization ended")
        if self.last is not None and np.array_equal(parameters, self.last):
            return self.cached
        self.last = parameters.copy()
        self.calls += 1
        weights = np.zeros((16, 16))
        weights[LOWER] = parameters[:120] - parameters[120:240]
        beta = parameters[-1]
        logits = self.spins @ weights.T
        log_probability = -np.logaddexp(0, -self.spins * logits).sum(axis=1)
        probability = 2 * np.exp(log_probability)
        positive = expit(logits)
        residual = (self.spins + 1) / 2 - positive
        potential = beta * self.energy
        target = np.exp(-potential - logsumexp(-potential))
        reward = potential + log_probability
        centered = reward - probability @ reward
        mean_energy_q = float(probability @ self.energy)
        mean_energy_p = float(target @ self.energy)
        variance_energy_p = float(target @ (self.energy - mean_energy_p) ** 2)
        variance = float(probability @ centered ** 2)
        entropy = float(-probability @ log_probability)
        divergence = float(probability @ reward + logsumexp(-potential) + math.log(2))
        difference = beta * (mean_energy_q - mean_energy_p)
        proposal_mass = float(probability @ self.sector)
        target_mass = float(target @ self.sector)

        def derivative(coefficient, beta_derivative):
            matrix = (residual * (probability * coefficient)[:, None]).T @ self.spins
            lower = matrix[LOWER]
            return np.concatenate([lower, -lower, [beta_derivative]])

        gradient_divergence = derivative(centered, mean_energy_q - mean_energy_p)
        gradient_variance = derivative(centered ** 2 + 2 * centered, 2 * float((probability * centered) @ self.energy))
        objective = variance
        objective_gradient = gradient_variance
        if self.gradient_weight:
            lower_gradient = gradient_divergence[:120]
            direction = np.sign(lower_gradient) * np.maximum(np.abs(lower_gradient) - 0.0027, 0)
            direction_matrix = np.zeros((16, 16))
            direction_matrix[LOWER] = direction
            directional_logits = self.spins @ direction_matrix.T
            directional_score = (residual * directional_logits).sum(axis=1)
            hessian_action = ((residual * (probability * (centered + 1) * directional_score)[:, None]).T @ self.spins)[LOWER]
            hessian_action -= (((probability * centered)[:, None] * positive * (1 - positive) * directional_logits).T @ self.spins)[LOWER]
            energy_gradient = derivative(self.energy, 0)[:120]
            packed_action = np.concatenate([hessian_action, -hessian_action, [float(direction @ energy_gradient)]])
            objective += self.gradient_weight * float(direction @ direction)
            objective_gradient = objective_gradient + 2 * self.gradient_weight * packed_action
        entropy_gradient = derivative(-log_probability, 0)
        energy_gradient = derivative(potential, mean_energy_q - mean_energy_p + beta * variance_energy_p)
        proposal_gradient = derivative(self.sector, 0)
        target_gradient = np.zeros(241)
        target_gradient[-1] = -float((target * self.sector) @ (self.energy - mean_energy_p))
        constraints = np.asarray([entropy - 3.0001, divergence - 0.4001, 0.3199 - difference,
                                  0.3199 + difference, 0.0009999 - proposal_mass, target_mass - 0.350001])
        constraint_jacobian = np.asarray([entropy_gradient, gradient_divergence, -energy_gradient,
                                          energy_gradient, -proposal_gradient, target_gradient])
        metrics = {"entropy": entropy, "reverse_kl": divergence, "reward_variance": variance,
                   "gradient_infinity": float(np.abs(gradient_divergence[:120]).max()),
                   "energy_error_per_spin": abs(difference) / 16,
                   "target_sector_mass": target_mass, "proposal_sector_mass": proposal_mass}
        report = PHYSICS.gate_report(metrics, SPEC)
        report["metrics"] = metrics
        self.cached = objective, objective_gradient, constraints, constraint_jacobian, report, weights
        return self.cached


