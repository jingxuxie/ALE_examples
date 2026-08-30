import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from search import SearchModel


class GeneralModel(SearchModel):
    def decode(self, payload):
        counts = np.empty(192, dtype=int)
        counts[:72] = np.array(payload["single"]).reshape(72)
        for row_index, gate in enumerate(range(24, 32)):
            _, control, target = self.keys[gate]
            for code, value in enumerate(payload["cx"][row_index], start=1):
                control_digit, target_digit = code % 4, code // 4
                label = ((control_digit & 1) << control) | ((control_digit >> 1) << (control + 4))
                label |= ((target_digit & 1) << target) | ((target_digit >> 1) << (target + 4))
                counts[self.lookup[gate, label]] = value
        return counts

    def family_calibrations(self, counts):
        table = np.zeros((32, 256), dtype=np.int64)
        table[self.error_gate, self.error_label] = counts
        uniform_table = np.zeros_like(table)
        uniform_table[self.error_gate, self.error_label] = np.rint(60 * self.uniform).astype(int)
        single_marginal = table[:24].sum(axis=0)
        cx_marginal = table[24:].sum(axis=0)
        single_baseline = uniform_table[:24].sum(axis=0)
        cx_baseline = uniform_table[24:].sum(axis=0)
        pulled = np.take_along_axis(table, self.permutations, axis=1)
        overlaps = np.sum(table[self.inverses] * pulled, axis=1)
        return {"single_marginal_max_count_error": int(np.max(abs(single_marginal - single_baseline))),
                "cx_marginal_max_count_error": int(np.max(abs(cx_marginal - cx_baseline))),
                "single_overlap": int(overlaps[:24].sum()), "single_overlap_target": 28800,
                "cx_overlap": int(overlaps[24:].sum()), "cx_overlap_target": 1920,
                "single_axis_marginals": [[int(single_marginal[label]) for label in support]
                                          for support in self.supports[::6][:4]],
                "cx_axis_marginals": [[int(cx_marginal[label]) for label in support]
                                      for support in self.supports[::6][:4]],
                "per_class_overlaps": overlaps.tolist()}

    def run(self, conditional, eta=0.4, epsilon=0.02, half_depth=128,
            lower_depth=0, upper_depth=None, scan=False, gradient=False,
            residual_limit=0.004, penalty=20000):
        weights = np.array([(1 - eta) / 24] * 24 + [eta / 8] * 8)
        probabilities = np.zeros((32, 256))
        probabilities[:, 0] = 1 - epsilon
        probabilities[self.error_gate, self.error_label] = epsilon * conditional
        lambdas = probabilities @ self.commutation
        inverse_lambdas = lambdas[self.inverses]
        permuted_lambdas = np.take_along_axis(lambdas, self.permutations, axis=1)
        coefficients = weights[:, None] * inverse_lambdas * permuted_lambdas
        vectors = np.ones((half_depth + 1, 256))
        for position in range(1, half_depth + 1):
            vectors[position] = np.sum(coefficients * vectors[position - 1][self.permutations], axis=0)
        values = vectors[:, 1:].mean(axis=1)
        depths = 2 * np.arange(half_depth + 1)
        mask = depths >= lower_depth
        if upper_depth is not None:
            mask &= depths <= upper_depth
        selected_depths, selected_values = depths[mask], values[mask]

        def profile(rate):
            shape = np.exp(-rate * selected_depths)
            amplitude = (shape @ selected_values) / (shape @ shape)
            return float(np.sum((selected_values - amplitude * shape) ** 2))

        if scan:
            grid = np.linspace(epsilon / 4, 2 * epsilon, 4097)
            shapes = np.exp(-np.outer(grid, selected_depths))
            amplitudes = (shapes @ selected_values) / np.sum(shapes * shapes, axis=1)
            losses = np.sum((selected_values - amplitudes[:, None] * shapes) ** 2, axis=1)
            minima = np.flatnonzero((losses[1:-1] <= losses[:-2]) & (losses[1:-1] <= losses[2:])) + 1
            candidates = [(profile(grid[0]), grid[0]), (profile(grid[-1]), grid[-1])]
            for index in minima:
                fitted = minimize_scalar(profile, bounds=(grid[index - 1], grid[index + 1]),
                                         method="bounded", options={"xatol": 1e-12})
                candidates.append((float(fitted.fun), float(fitted.x)))
            _, rate = min(candidates)
        else:
            fitted = minimize_scalar(profile, bounds=(epsilon / 4, 2 * epsilon),
                                     method="bounded", options={"xatol": 1e-13})
            rate = float(fitted.x)
        shape = np.exp(-rate * selected_depths)
        amplitude = (shape @ selected_values) / (shape @ shape)
        residual = selected_values - amplitude * shape
        estimate = (255 / 256) * (-np.expm1(-rate))
        metrics = {"eta": eta, "epsilon": epsilon, "r": float(estimate),
                   "bias": float(1 - estimate / epsilon), "bias_per_epsilon": float((1 - estimate / epsilon) / epsilon),
                   "amplitude": float(amplitude), "t": float(rate),
                   "max_residual": float(np.max(abs(residual))),
                   "fit_depth_min": int(selected_depths[0]), "fit_depth_max": int(selected_depths[-1]),
                   "end_signal": float(values[-1]), "polarizations": values.tolist()}
        if not gradient:
            return metrics
        jacobian = np.array((shape, -amplitude * selected_depths * shape)).T
        cross_curvature = residual @ (-selected_depths * shape)
        rate_curvature = residual @ (amplitude * selected_depths ** 2 * shape)
        curvature = jacobian.T @ jacobian - np.array(((0, cross_curvature), (cross_curvature, rate_curvature)))
        response = np.linalg.solve(curvature, jacobian.T)
        selected_gradient = (255 / 256) * np.exp(-rate) / epsilon * response[1]
        excess = np.maximum(abs(residual) - residual_limit, 0)
        residual_gradient = 2 * penalty * excess * np.sign(residual)
        selected_gradient += residual_gradient - response.T @ (jacobian.T @ residual_gradient)
        objective = estimate / epsilon + penalty * np.sum(excess ** 2)
        value_gradient = np.zeros(half_depth + 1)
        value_gradient[mask] = selected_gradient
        coefficient_gradient = np.zeros_like(coefficients)
        adjoint = np.zeros(256)
        for position in range(half_depth, 0, -1):
            adjoint[1:] += value_gradient[position] / 255
            coefficient_gradient += adjoint[None, :] * vectors[position - 1][self.permutations]
            adjoint = np.sum(coefficients * adjoint[self.permutations], axis=0)
        lambda_gradient = np.zeros_like(lambdas)
        for gate in range(32):
            lambda_gradient[self.inverses[gate]] += weights[gate] * permuted_lambdas[gate] * coefficient_gradient[gate]
            lambda_gradient[gate, self.permutations[gate]] += weights[gate] * inverse_lambdas[gate] * coefficient_gradient[gate]
        conditional_gradient = epsilon * np.sum(lambda_gradient[self.error_gate] * self.commutation[self.error_label], axis=1)
        return float(objective), conditional_gradient
