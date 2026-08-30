import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

from champion_policy import Policy, exchange


class LowShotPolicy(Policy):
    def __init__(self, hello, communication):
        super().__init__(hello, communication)
        self.settings = json.loads((Path(__file__).parent / "settings.json").read_text())
        centers = np.asarray([[np.mean([self.coordinates[vertex][axis] for vertex in edge])
                               for axis in range(2)] for edge in self.edges])
        distances = np.asarray([min(sum(abs(self.coordinates[left][axis] - self.coordinates[right][axis])
                                         for axis in range(2))
                                     for left in self.edges[first] for right in self.edges[second])
                                for first, second in self.pairs])
        weights = np.ones(len(self.pairs))
        if self.family == "local_clusters":
            separations = np.abs(centers[:, None, :] - centers[None, :, :]).sum(axis=2)
            weights = (.002 + 2 * np.exp(-(separations[self.pairs[:, 0]] +
                                           separations[self.pairs[:, 1]]) / 2).mean(axis=1))
            weights *= np.exp(-(distances - 1) / 2)
        elif self.family == "spam_drift":
            local = np.exp(-(distances - 1) / 1.3) + .05
            weights = .5 / len(weights) + .5 * local / local.sum()
        self.inclusion = np.minimum(.8, (round(.30 * self.edge_count) + .5) * weights / weights.sum())
        self.slab_mean = np.full(len(self.pairs), 2.25)
        self.slab_variance = np.full(len(self.pairs), 2.5 ** 2 / 12)
        base_mean, base_variance = .45, .5 ** 2 / 12
        if self.family in ("anticorrelated", "spam_drift"):
            base_mean = .85 / math.log(1 / .15)
            base_variance = (1 - .15 ** 2) / (2 * math.log(1 / .15)) - base_mean ** 2
        if self.family == "anticorrelated":
            self.slab_mean[:] = 2.75 - base_mean
            self.slab_variance[:] = 1.5 ** 2 / 12 + base_variance / 2
        self.prior_mean = np.r_[.25, np.full(self.edge_count, base_mean), self.inclusion * self.slab_mean]
        self.prior_variance = np.r_[.3 ** 2 / 12, np.full(self.edge_count, base_variance),
                                   self.inclusion * (self.slab_variance + self.slab_mean ** 2) -
                                   (self.inclusion * self.slab_mean) ** 2]
        self.beta = self.prior_mean.copy()

    def spam_prior(self, parameters):
        deviations = parameters.copy()
        variance = [.4 ** 2 / 3] + [.9 ** 2 / 3] * self.edge_count + [1 / 3]
        if self.drift:
            variance += [.23, .23, .8 ** 2 / 3, 1 / 12]
            deviations[-1] -= 1
        precision = self.settings.get("spam_strength", 1.) / np.asarray(variance)
        return .5 * np.sum(deviations ** 2 * precision), deviations * precision

    def fit_spam(self, rows, reference_counts, reference_shots, reference_times):
        features = self.spam_features(rows)

        def objective(parameters):
            contrast, derivative, jacobian = self.spam_parts(parameters, features, reference_times)
            probability = self.floor + (1 - self.floor) * contrast
            loss = -np.sum(reference_counts * np.log(probability) +
                           (reference_shots - reference_counts) * np.log1p(-probability))
            residual = (reference_shots * probability - reference_counts) / (probability * (1 - probability))
            penalty, gradient = self.spam_prior(parameters)
            return loss + penalty, jacobian.T @ (residual * (1 - self.floor) * derivative) + gradient

        initial = np.zeros(len(self.spam_bounds())) if self.spam is None else self.spam.copy()
        if self.drift and self.spam is None:
            initial[-1] = 1.
        result = minimize(objective, initial, method="L-BFGS-B", jac=True, bounds=self.spam_bounds(),
                          options={"maxiter": 180, "ftol": 1e-9})
        self.spam = result.x
        return features

    def fit(self, exact=False):
        rows = np.asarray([record[0] for record in self.records])
        depths = np.asarray([record[1] for record in self.records])
        counts = np.asarray([record[2]["successes"] for record in self.records] +
                            [record[3]["successes"] for record in self.records])
        shots = np.asarray([record[2]["shots"] for record in self.records] +
                           [record[3]["shots"] for record in self.records])
        times = np.asarray([record[2]["context"] for record in self.records] +
                           [record[3]["context"] for record in self.records])
        count_rows = len(rows)
        spam_features = self.fit_spam(rows, counts[:count_rows], shots[:count_rows], times[:count_rows])
        contrast = self.spam_parts(self.spam, spam_features, times[count_rows:])[0]
        probability = (counts[count_rows:] + .5) / (shots[count_rows:] + 1.)
        rate = -np.log(np.maximum(1e-8, probability - self.floor) / ((1 - self.floor) * contrast)) / depths
        variance = ((1 - probability) / (shots[count_rows:] * probability) + .001) / depths ** 2
        design = rows * (.01 / np.sqrt(variance[:, None]))
        target = rate / np.sqrt(variance)
        gram = design.T @ design
        rhs = design.T @ target
        strength = self.settings.get("strength", 1.)
        precision = strength / self.prior_variance
        mode = self.settings.get("mode", "ridge")
        penalty = np.zeros(self.dimension)
        if mode == "lasso":
            penalty[self.offset:] = self.settings.get("lasso", 1.) * np.sqrt(np.diag(gram)[self.offset:])
            precision[self.offset:] *= .05
        prior_mean = self.prior_mean.copy()

        def quadratic(coefficients):
            centered = coefficients - prior_mean
            gradient = gram @ coefficients - rhs + centered * precision + penalty
            loss = .5 * coefficients @ (gram @ coefficients) - rhs @ coefficients
            return loss + .5 * np.sum(centered ** 2 * precision) + penalty @ coefficients, gradient

        result = minimize(quadratic, self.beta, method="L-BFGS-B", jac=True, bounds=self.rate_bounds(),
                          options={"maxiter": 300, "ftol": 1e-9})
        self.beta = result.x
        if mode == "spike":
            diagonal = np.diag(gram)
            residual = rhs - gram @ self.beta
            temperature = self.settings.get("temperature", 1.)
            for iteration in range(120):
                largest_change = 0.
                for index in self.generator.permutation(self.dimension):
                    conditional_rhs = residual[index] + diagonal[index] * self.beta[index]
                    if index < self.offset:
                        updated = (conditional_rhs + precision[index] * prior_mean[index]) / (diagonal[index] + precision[index])
                        updated = np.clip(updated, *self.rate_bounds()[index])
                    else:
                        pair_index = index - self.offset
                        conditional_precision = diagonal[index] / temperature
                        conditional_rhs /= temperature
                        slab_variance = self.slab_variance[pair_index]
                        slab_mean = self.slab_mean[pair_index]
                        posterior_variance = 1 / (conditional_precision + 1 / slab_variance)
                        posterior_mean = posterior_variance * (conditional_rhs + slab_mean / slab_variance)
                        log_bayes_factor = .5 * (math.log(posterior_variance / slab_variance) +
                                                posterior_mean ** 2 / posterior_variance - slab_mean ** 2 / slab_variance)
                        inclusion = self.inclusion[pair_index]
                        posterior_inclusion = expit(math.log(inclusion / (1 - inclusion)) + log_bayes_factor)
                        updated = posterior_inclusion * np.clip(posterior_mean, .5, 3.5)
                    change = .5 * (updated - self.beta[index])
                    self.beta[index] += change
                    residual -= gram[:, index] * change
                    largest_change = max(largest_change, abs(change))
                if largest_change < .0002:
                    break
            return self.beta
        if not exact:
            return self.beta
        expanded_rows = np.vstack((rows, rows))
        expanded_spam = np.vstack((spam_features, spam_features))
        depth_vector = np.r_[np.zeros(count_rows), depths]

        def likelihood(parameters):
            coefficients = parameters[:self.dimension]
            contrast, derivative, jacobian = self.spam_parts(parameters[self.dimension:], expanded_spam, times)
            exponential = np.exp(-.01 * depth_vector * (expanded_rows @ coefficients))
            signal = (1 - self.floor) * contrast * exponential
            probability = np.clip(self.floor + signal, 1e-12, 1 - 1e-12)
            loss = -np.sum(counts * np.log(probability) + (shots - counts) * np.log1p(-probability))
            residual = (shots * probability - counts) / (probability * (1 - probability))
            centered = coefficients - prior_mean
            gradient_rate = expanded_rows.T @ (-.01 * depth_vector * signal * residual) + precision * centered + penalty
            spam_loss, spam_gradient = self.spam_prior(parameters[self.dimension:])
            gradient_spam = jacobian.T @ ((1 - self.floor) * exponential * derivative * residual) + spam_gradient
            return loss + .5 * np.sum(centered ** 2 * precision) + penalty @ coefficients + spam_loss, np.r_[gradient_rate, gradient_spam]

        result = minimize(likelihood, np.r_[self.beta, self.spam], method="L-BFGS-B", jac=True,
                          bounds=self.rate_bounds() + self.spam_bounds(),
                          options={"maxiter": 400, "ftol": 1e-9})
        self.beta = result.x[:self.dimension]
        self.spam = result.x[self.dimension:]
        return self.beta

    def acquire(self):
        budget = self.hello["limits"]["shots_budget"]
        pair_count = min(self.settings.get("contexts", 96), budget // 64)
        pair_shots, remainder = divmod(budget, pair_count)
        control_count = self.settings.get("controls", 4)
        controls = [[]] + [[int(edge)] for edge in self.generator.permutation(self.edge_count)[:max(0, control_count - 2)]] + [[]]
        for index in range(pair_count):
            if index == pair_count // 2:
                self.fit()
            if index < control_count:
                matching = controls[index]
            else:
                size = self.maximum if self.generator.random() < self.settings.get("dense_fraction", .85) else self.maximum - 2
                matching = None
                while matching is None:
                    forced = ()
                    if self.generator.random() < .8:
                        weights = 1 / (3 + self.pair_counts)
                        pair_index = self.generator.choice(len(self.pairs), p=weights / weights.sum())
                        forced = tuple(self.pairs[pair_index])
                    matching = self.matching(size, forced)
            row = self.features(matching)
            estimate = max(.001, .01 * row @ self.beta)
            depth = int(np.clip(2 * round(self.settings.get("depth_scale", 1.5) / estimate / 2), 2, 256))
            allocated = pair_shots + int(index < remainder)
            reference_shots = max(32, min(allocated - 32, int(round(self.settings.get("reference_fraction", .20) * allocated))))
            reference = self.exchange({"type": "experiment", "matching": matching, "depth": 0, "shots": reference_shots})
            decayed = self.exchange({"type": "experiment", "matching": matching, "depth": depth, "shots": allocated - reference_shots})
            self.records.append((row, depth, reference, decayed))
            self.pair_counts += row[self.offset:]
        self.fit(exact=True)


if __name__ == "__main__":
    LowShotPolicy(json.loads(sys.stdin.readline()), exchange).run()
