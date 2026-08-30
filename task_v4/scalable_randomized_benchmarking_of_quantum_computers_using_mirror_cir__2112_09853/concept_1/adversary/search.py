import argparse
import itertools
import json
import platform
import time

import numpy as np
import scipy
from scipy.linalg import qr
from scipy.optimize import Bounds, LinearConstraint, NonlinearConstraint, minimize, minimize_scalar


class SearchModel:
    def __init__(self):
        self.epsilon = 0.02
        self.depths = np.arange(0, 258, 2)
        labels = np.arange(256)
        x_bits = labels & 15
        z_bits = labels >> 4
        self.keys = []
        self.supports = []
        permutations = []
        for site in range(4):
            digits = ((x_bits >> site) & 1) + 2 * ((z_bits >> site) & 1)
            for axes in itertools.permutations((1, 2, 3)):
                mapped = np.array((0, *axes))[digits]
                permutation = labels ^ (((mapped & 1) ^ ((x_bits >> site) & 1)) << site)
                permutation ^= (((mapped >> 1) ^ ((z_bits >> site) & 1)) << (site + 4))
                permutations.append(permutation)
                self.keys.append(("single", site, axes))
                self.supports.append([1 << site, 1 << (site + 4), (1 << site) + (1 << (site + 4))])
        for control in range(4):
            for target in ((control + 1) % 4, (control - 1) % 4):
                permutations.append(labels ^ (((x_bits >> control) & 1) << target)
                                    ^ (((z_bits >> target) & 1) << (control + 4)))
                self.keys.append(("cx", control, target))
                allowed_mask = (1 << control) | (1 << target)
                self.supports.append([int(label) for label in labels[1:]
                                      if ((label | (label >> 4)) & 15 & ~allowed_mask) == 0])
        self.permutations = np.array(permutations)
        inverse_indices = []
        for kind, site, action in self.keys:
            inverse_key = ((kind, site, tuple(action.index(axis) + 1 for axis in (1, 2, 3)))
                           if kind == "single" else (kind, site, action))
            inverse_indices.append(self.keys.index(inverse_key))
        self.inverses = np.array(inverse_indices)
        self.integer_weights = np.array([1 if key[0] == "single" else 2 for key in self.keys])
        self.weights = self.integer_weights / 40
        parity = np.array([int(label).bit_count() % 2 for label in labels])
        self.commutation = 1 - 2 * parity[(x_bits[:, None] & z_bits[None, :])
                                         ^ (z_bits[:, None] & x_bits[None, :])]
        self.error_gate = np.concatenate([np.full(len(support), gate)
                                          for gate, support in enumerate(self.supports)])
        self.error_label = np.concatenate(self.supports)
        self.lookup = np.full((32, 256), -1, dtype=int)
        self.lookup[self.error_gate, self.error_label] = np.arange(192)
        rows = np.zeros((32, 192))
        rows[self.error_gate, np.arange(192)] = 1
        means = np.zeros((256, 192))
        means[self.error_label, np.arange(192)] = self.integer_weights[self.error_gate]
        self.full_constraint = np.vstack((rows, means[1:]))
        self.uniform = np.array([1 / len(self.supports[gate]) for gate in self.error_gate])
        self.full_target = self.full_constraint @ self.uniform
        self.integer_target = np.rint(60 * self.full_target).astype(int)
        _, triangular, pivots = qr(self.full_constraint.T, pivoting=True, mode="economic")
        self.rank = int(np.sum(abs(np.diag(triangular)) > 1e-10))
        self.constraint = self.full_constraint[pivots[:self.rank]]
        self.target = self.full_target[pivots[:self.rank]]
        self.lower = np.array([2 if self.keys[gate][0] == "single" else 1
                               for gate in self.error_gate])
        self.upper = np.array([42 if self.keys[gate][0] == "single" else 21
                               for gate in self.error_gate])
        partners = self.lookup[self.inverses[self.error_gate],
                               self.permutations[self.inverses[self.error_gate], self.error_label]]
        self.quadratic = np.zeros((192, 192), dtype=int)
        self.quadratic[np.arange(192), partners] = self.integer_weights[self.error_gate]
        if not np.array_equal(self.quadratic, self.quadratic.T):
            raise AssertionError("Inverse-pair quadratic form is not symmetric")
        self.pair_target = self.overlap(self.uniform)

    def overlap(self, conditional):
        return float(conditional @ self.quadratic @ conditional / 40)

    def overlap_gradient(self, conditional):
        return 2 * (self.quadratic @ conditional) / 40

    def evaluate(self, conditional, gradient=True):
        probabilities = np.zeros((32, 256))
        probabilities[:, 0] = 0.98
        probabilities[self.error_gate, self.error_label] = self.epsilon * conditional
        lambdas = probabilities @ self.commutation
        inverse_lambdas = lambdas[self.inverses]
        permuted_lambdas = np.take_along_axis(lambdas, self.permutations, axis=1)
        coefficients = self.weights[:, None] * inverse_lambdas * permuted_lambdas
        vectors = np.ones((129, 256))
        for half_depth in range(1, 129):
            vectors[half_depth] = np.sum(coefficients * vectors[half_depth - 1][self.permutations], axis=0)
        values = vectors[:, 1:].mean(axis=1)

        def profile(rate):
            shape = np.exp(-rate * self.depths)
            amplitude = (shape @ values) / (shape @ shape)
            return np.sum((values - amplitude * shape) ** 2)

        fitted = minimize_scalar(profile, bounds=(0.005, 0.04), method="bounded",
                                 options={"xatol": 1e-13})
        rate = float(fitted.x)
        shape = np.exp(-rate * self.depths)
        amplitude = (shape @ values) / (shape @ shape)
        residual = values - amplitude * shape
        estimate = (255 / 256) * (-np.expm1(-rate))
        if not gradient:
            return {"r": float(estimate), "bias": float(1 - estimate / self.epsilon),
                    "amplitude": float(amplitude), "t": rate,
                    "max_residual": float(np.max(abs(residual))),
                    "rmse": float(np.sqrt(np.mean(residual ** 2))),
                    "S2": float(values[1]), "S256": float(values[-1])}
        jacobian = np.array((shape, -amplitude * self.depths * shape)).T
        cross_curvature = residual @ (-self.depths * shape)
        rate_curvature = residual @ (amplitude * self.depths ** 2 * shape)
        curvature = jacobian.T @ jacobian - np.array(((0, cross_curvature),
                                                     (cross_curvature, rate_curvature)))
        response = np.linalg.solve(curvature, jacobian.T)
        value_gradient = (255 / 256) * np.exp(-rate) / self.epsilon * response[1]
        excess = np.maximum(abs(residual) - 0.008, 0)
        residual_gradient = 40000 * excess * np.sign(residual)
        value_gradient += residual_gradient - response.T @ (jacobian.T @ residual_gradient)
        objective = estimate / self.epsilon + 20000 * np.sum(excess ** 2)
        coefficient_gradient = np.zeros_like(coefficients)
        adjoint = np.zeros(256)
        for half_depth in range(128, 0, -1):
            adjoint[1:] += value_gradient[half_depth] / 255
            coefficient_gradient += adjoint[None, :] * vectors[half_depth - 1][self.permutations]
            adjoint = np.sum(coefficients * adjoint[self.permutations], axis=0)
        lambda_gradient = np.zeros_like(lambdas)
        for gate in range(32):
            lambda_gradient[self.inverses[gate]] += (
                self.weights[gate] * permuted_lambdas[gate] * coefficient_gradient[gate])
            lambda_gradient[gate, self.permutations[gate]] += (
                self.weights[gate] * inverse_lambdas[gate] * coefficient_gradient[gate])
        conditional_gradient = self.epsilon * np.sum(
            lambda_gradient[self.error_gate] * self.commutation[self.error_label], axis=1)
        return float(objective), conditional_gradient

    def initial_counts(self):
        counts = np.rint(60 * self.uniform).astype(int)
        for site in range(4):
            identity = self.keys.index(("single", site, (1, 2, 3)))
            swap = self.keys.index(("single", site, (2, 1, 3)))
            counts[self.error_gate == identity] += np.array((18, -18, 0))
            counts[self.error_gate == swap] -= np.array((18, -18, 0))
        return counts

    def repair(self, rounded):
        if not np.array_equal(self.full_constraint @ rounded, self.integer_target):
            raise RuntimeError("Rounding did not preserve linear equalities; this run needs another start")
        changes = []
        for first_gate in range(32):
            for second_gate in range(first_gate + 1, 32):
                if set(self.supports[first_gate]) != set(self.supports[second_gate]):
                    continue
                for first_label, second_label in itertools.combinations(self.supports[first_gate], 2):
                    for amount in (-1, 1):
                        change = np.zeros(192, dtype=int)
                        change[self.lookup[first_gate, first_label]] = amount
                        change[self.lookup[first_gate, second_label]] = -amount
                        change[self.lookup[second_gate, first_label]] = -amount
                        change[self.lookup[second_gate, second_label]] = amount
                        trial = rounded + change
                        if np.all(trial >= self.lower) and np.all(trial <= self.upper):
                            changes.append(change)
        changes = np.array(changes)
        products = changes @ self.quadratic
        current_overlap = int(rounded @ self.quadratic @ rounded)
        desired_delta = 32640 - current_overlap
        deltas = 2 * (products @ rounded) + np.sum(products * changes, axis=1)
        paired_deltas = deltas[:, None] + deltas[None, :] + 2 * (products @ changes.T)
        candidates = [rounded] if desired_delta == 0 else []
        candidates.extend(rounded + change for change in changes[deltas == desired_delta])
        locations = np.argwhere(paired_deltas == desired_delta)
        for first_index, second_index in locations:
            if second_index >= first_index:
                candidates.append(rounded + changes[first_index] + changes[second_index])
        unique = {tuple(int(value) for value in candidate): candidate for candidate in candidates
                  if np.all(candidate >= self.lower) and np.all(candidate <= self.upper)}
        scored = []
        for candidate in unique.values():
            if int(candidate @ self.quadratic @ candidate) != 32640:
                raise AssertionError("Repair did not restore exact overlap")
            if not np.array_equal(self.full_constraint @ candidate, self.integer_target):
                raise AssertionError("Repair changed the average channel")
            metrics = self.evaluate(candidate / 60, gradient=False)
            if metrics["max_residual"] <= 0.004 and metrics["S256"] >= 0.005:
                scored.append((metrics["r"], tuple(candidate), candidate, metrics))
        if not scored:
            raise RuntimeError("No admissible one/two-move integer repair found")
        scored.sort(key=lambda item: (item[0], item[1]))
        _, _, winner, metrics = scored[0]
        return winner, metrics, {"unit_moves": len(changes), "repair_candidates": len(unique),
                                 "rounded_overlap": current_overlap,
                                 "winning_overlap": int(winner @ self.quadratic @ winner),
                                 "changed_entries": int(np.count_nonzero(winner != rounded))}

    def encode(self, counts):
        single = counts[:72].reshape(4, 6, 3).tolist()
        cx_rows = []
        for gate in range(24, 32):
            _, control, target = self.keys[gate]
            local_labels = []
            for code in range(1, 16):
                control_digit, target_digit = code % 4, code // 4
                label = ((control_digit & 1) << control) | ((control_digit >> 1) << (control + 4))
                label |= ((target_digit & 1) << target) | ((target_digit >> 1) << (target + 4))
                local_labels.append(label)
            cx_rows.append(counts[self.lookup[gate, local_labels]].tolist())
        return {"single": single, "cx": cx_rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--maxiter", type=int, default=600)
    parser.add_argument("--verify-gradient", action="store_true")
    arguments = parser.parse_args()
    started = time.perf_counter()
    model = SearchModel()
    initial = model.initial_counts() / 60
    gradient_evidence = None
    if arguments.verify_gradient:
        direction = np.random.default_rng(12).normal(size=192)
        for gate in range(32):
            mask = model.error_gate == gate
            direction[mask] -= direction[mask].mean()
        step = 1e-5
        finite_difference = (model.evaluate(initial + step * direction)[0]
                             - model.evaluate(initial - step * direction)[0]) / (2 * step)
        analytic = model.evaluate(initial)[1] @ direction
        error = abs(finite_difference - analytic)
        gradient_evidence = {"finite_difference": float(finite_difference),
                             "analytic": float(analytic), "absolute_error": float(error)}
        if error > 1e-6:
            raise AssertionError("Adjoint gradient failed finite-difference cross-check")
    constraints = [LinearConstraint(model.constraint, model.target, model.target),
                   NonlinearConstraint(model.overlap, model.pair_target, model.pair_target,
                                       jac=model.overlap_gradient)]
    optimized = minimize(model.evaluate, initial, jac=True, method="SLSQP",
                         bounds=Bounds(model.lower / 60, model.upper / 60),
                         constraints=constraints,
                         options={"maxiter": arguments.maxiter, "ftol": 1e-11, "disp": False})
    if not optimized.success:
        raise RuntimeError(str(optimized.message))
    rounded = np.rint(60 * optimized.x).astype(int)
    winner, metrics, repair_evidence = model.repair(rounded)
    if metrics["bias"] < 0.0244:
        raise RuntimeError("Found a valid integer witness but missed the target bias")
    result = {"algorithm": "adjoint SLSQP, nearest-integer rounding, exhaustive one/two transportation-move repair",
              "initialization": "uniform counts with matched identity/swap +/-18 perturbations; does not read a winning witness",
              "python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
              "elapsed_seconds": time.perf_counter() - started, "variables": 192,
              "linear_constraint_rank": model.rank, "gradient_check": gradient_evidence,
              "optimizer": {"success": bool(optimized.success), "message": str(optimized.message),
                            "iterations": int(optimized.nit), "function_evaluations": int(optimized.nfev),
                            "continuous_metrics": model.evaluate(optimized.x, gradient=False),
                            "linear_residual": float(np.max(abs(model.full_constraint @ optimized.x - model.full_target))),
                            "overlap_residual": float(model.overlap(optimized.x) - model.pair_target)},
              "repair": repair_evidence, "metrics": metrics, "witness": model.encode(winner)}
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
