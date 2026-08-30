import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import itertools
import json
import math
import sys
import numpy as np
from scipy.optimize import minimize, lsq_linear
from scipy.special import expit


class Policy:
    def __init__(self, hello, exchange):
        self.hello = hello
        self.exchange = exchange
        self.edges = [tuple(edge) for edge in hello['edges']]
        self.edge_count = len(self.edges)
        self.qubits = hello['qubits']
        self.maximum = hello['max_matching_size']
        self.family = hello['family']
        self.drift = self.family == 'spam_drift'
        self.floor = 2.0 ** (-self.qubits)
        self.generator = np.random.default_rng(78263)
        columns = hello['shape'][1]
        self.coordinates = [(vertex // columns, vertex % columns) for vertex in range(self.qubits)]
        self.lookup = {edge: index for index, edge in enumerate(self.edges)}
        pairs = []
        for first, second in itertools.combinations(range(self.edge_count), 2):
            if set(self.edges[first]).intersection(self.edges[second]):
                continue
            distance = min(abs(self.coordinates[left][0] - self.coordinates[right][0]) +
                           abs(self.coordinates[left][1] - self.coordinates[right][1])
                           for left in self.edges[first] for right in self.edges[second])
            if self.family != 'distant_pairs' or distance >= 3:
                pairs.append((first, second))
        self.pairs = np.asarray(pairs, dtype=int)
        self.offset = self.edge_count + 1
        self.dimension = self.offset + len(self.pairs)
        self.records = []
        self.pair_counts = np.zeros(len(self.pairs))
        self.beta = np.zeros(self.dimension)
        self.beta[0] = .25
        self.beta[1:self.offset] = .45
        self.spam = None

    def matching(self, size, forced=()):
        occupied = {vertex for edge in forced for vertex in self.edges[edge]}
        neighbors = {}
        for first, second in self.edges:
            if first in occupied or second in occupied:
                continue
            if sum(self.coordinates[first]) % 2:
                first, second = second, first
            neighbors.setdefault(first, []).append(second)
        for choices in neighbors.values():
            self.generator.shuffle(choices)
        partners = {}

        def augment(vertex, seen):
            for neighbor in neighbors.get(vertex, []):
                if neighbor in seen:
                    continue
                seen.add(neighbor)
                if neighbor not in partners or augment(partners[neighbor], seen):
                    partners[neighbor] = vertex
                    return True
            return False

        for vertex in self.generator.permutation(list(neighbors)):
            augment(int(vertex), set())
        available = [self.lookup[tuple(sorted((first, second))) ]
                     for second, first in partners.items()]
        needed = size - len(forced)
        if len(available) < needed:
            return None
        chosen = self.generator.choice(available, needed, replace=False).tolist()
        return sorted([int(edge) for edge in forced] + chosen)

    def features(self, matching):
        row = np.zeros(self.dimension)
        row[0] = 1.
        row[1 + np.asarray(matching, dtype=int)] = 1.
        row[self.offset:] = row[1 + self.pairs[:, 0]] * row[1 + self.pairs[:, 1]]
        return row

    def spam_features(self, rows):
        active = rows[:, 1:self.offset]
        sizes = active.sum(axis=1)
        return np.column_stack((np.ones(len(rows)), active / np.sqrt(np.maximum(1., sizes[:, None])),
                                sizes / (self.qubits // 2)))

    def spam_parts(self, params, features, times):
        size = self.edge_count + 2
        latent = features @ params[:size]
        if self.drift:
            angles = 2 * np.pi * params[size + 3] * times
            sine = np.sin(angles)
            cosine = np.cos(angles)
            latent += params[size] * sine + params[size + 1] * cosine + params[size + 2] * (times - .5)
            frequency_grad = 2 * np.pi * times * (params[size] * cosine - params[size + 1] * sine)
            jacobian = np.column_stack((features, sine, cosine, times - .5, frequency_grad))
        else:
            jacobian = features
        sigmoid = expit(latent)
        return .58 + .37 * sigmoid, .37 * sigmoid * (1 - sigmoid), jacobian

    def spam_bounds(self):
        bounds = [(-.4, .4)] + [(-.9, .9)] * self.edge_count + [(-1., 1.)]
        if self.drift:
            bounds += [(-.95, .95), (-.95, .95), (-.8, .8), (.5, 1.5)]
        return bounds

    def fit_spam(self, rows, reference_counts, reference_shots, reference_times):
        features = self.spam_features(rows)

        def objective(params):
            contrast, derivative, jacobian = self.spam_parts(params, features, reference_times)
            probability = self.floor + (1 - self.floor) * contrast
            loss = -np.sum(reference_counts * np.log(probability) +
                           (reference_shots - reference_counts) * np.log1p(-probability))
            residual = (reference_shots * probability - reference_counts) / (probability * (1 - probability))
            gradient = jacobian.T @ (residual * (1 - self.floor) * derivative)
            return loss, gradient

        starts = []
        if self.spam is not None:
            starts.append(self.spam)
        else:
            for frequency in ([.65, 1., 1.35] if self.drift else [1.]):
                initial = np.zeros(len(self.spam_bounds()))
                if self.drift:
                    initial[-1] = frequency
                starts.append(initial)
        results = [minimize(objective, start, method='L-BFGS-B', jac=True,
                            bounds=self.spam_bounds(),
                            options={'maxiter': 250, 'ftol': 1e-11, 'gtol': 1e-5}) for start in starts]
        self.spam = min(results, key=lambda result: result.fun).x
        return features

    def rate_bounds(self):
        base_bounds = (.15, 1.) if self.family in ('anticorrelated', 'spam_drift') else (.2, .7)
        return [(.1, .4)] + [base_bounds] * self.edge_count + [(0., 3.5)] * len(self.pairs)

    def fit(self, exact=False):
        rows = np.asarray([record[0] for record in self.records])
        depths = np.asarray([record[1] for record in self.records])
        reference_counts = np.asarray([record[2]['successes'] for record in self.records])
        reference_shots = np.asarray([record[2]['shots'] for record in self.records])
        reference_times = np.asarray([record[2]['context'] for record in self.records])
        decay_counts = np.asarray([record[3]['successes'] for record in self.records])
        decay_shots = np.asarray([record[3]['shots'] for record in self.records])
        decay_times = np.asarray([record[3]['context'] for record in self.records])
        spam_features = self.fit_spam(rows, reference_counts, reference_shots, reference_times)
        contrast, _, _ = self.spam_parts(self.spam, spam_features, decay_times)
        probability = (decay_counts + .5) / (decay_shots + 1.)
        rate = -np.log(np.maximum(1e-8, probability - self.floor) / ((1 - self.floor) * contrast)) / depths
        variance = ((1 - probability) / (decay_shots * probability) + .0003) / depths ** 2
        deviation = np.sqrt(variance)
        design = rows * (.01 / deviation[:, None])
        target = rate / deviation
        gram = design.T @ design
        rhs = design.T @ target
        penalty = np.zeros(self.dimension)
        penalty[self.offset:] = 2.8 * np.sqrt(np.diag(gram)[self.offset:])

        def objective(beta):
            gradient = gram @ beta - rhs + penalty
            return .5 * beta @ (gram @ beta) - rhs @ beta + penalty @ beta, gradient

        result = minimize(objective, self.beta, method='L-BFGS-B', jac=True, bounds=self.rate_bounds(),
                          options={'maxiter': 800, 'ftol': 1e-11, 'gtol': 1e-5})
        self.beta = result.x
        selected = np.flatnonzero(self.beta[self.offset:] > .45) + self.offset
        active = np.r_[np.arange(self.offset), selected]
        bounds = np.asarray(self.rate_bounds())[active]
        solution = lsq_linear(design[:, active], target, bounds=(bounds[:, 0], bounds[:, 1]),
                              method='bvls', tol=1e-9).x
        self.beta[:] = 0.
        self.beta[active] = solution
        if exact:
            selected = selected[self.beta[selected] > .5]
            active = np.r_[np.arange(self.offset), selected]
            expanded_rows = np.vstack((rows[:, active], rows[:, active]))
            expanded_spam = np.vstack((spam_features, spam_features))
            times = np.r_[reference_times, decay_times]
            depth_vector = np.r_[np.zeros(len(rows)), depths]
            counts = np.r_[reference_counts, decay_counts]
            shots = np.r_[reference_shots, decay_shots]
            number_rates = len(active)

            def likelihood(params):
                contrast, derivative, jacobian = self.spam_parts(params[number_rates:], expanded_spam, times)
                rate = .01 * (expanded_rows @ params[:number_rates])
                exponential = np.exp(-depth_vector * rate)
                signal = (1 - self.floor) * contrast * exponential
                probability = np.clip(self.floor + signal, 1e-12, 1 - 1e-12)
                loss = -np.sum(counts * np.log(probability) + (shots - counts) * np.log1p(-probability))
                residual = (shots * probability - counts) / (probability * (1 - probability))
                gradient_rate = expanded_rows.T @ (-.01 * depth_vector * signal * residual)
                gradient_spam = jacobian.T @ ((1 - self.floor) * exponential * derivative * residual)
                return loss, np.r_[gradient_rate, gradient_spam]

            bounds = [self.rate_bounds()[index] for index in active] + self.spam_bounds()
            result = minimize(likelihood, np.r_[self.beta[active], self.spam], method='L-BFGS-B', jac=True,
                              bounds=bounds, options={'maxiter': 600, 'ftol': 1e-11, 'gtol': 1e-4})
            self.beta[:] = 0.
            self.beta[active] = result.x[:number_rates]
            self.spam = result.x[number_rates:]
        return self.beta

    def acquire(self):
        controls = [[]] + [[edge] for edge in self.generator.permutation(self.edge_count).tolist()] + [[]]
        for index in range(384):
            if index == 192:
                self.fit()
            if index < len(controls):
                matching = controls[index]
            else:
                size = self.maximum if self.generator.random() < .85 else self.maximum - 2
                matching = None
                while matching is None:
                    forced = ()
                    if self.generator.random() < .8:
                        weights = 1. / (3. + self.pair_counts)
                        pair = self.generator.choice(len(self.pairs), p=weights / weights.sum())
                        forced = tuple(self.pairs[pair].tolist())
                    matching = self.matching(size, forced)
            row = self.features(matching)
            if index < 192:
                estimate = .0025 + .0045 * len(matching)
                estimate += .0225 * (round(.3 * self.edge_count) + .5) * row[self.offset:].sum() / len(self.pairs)
            else:
                estimate = max(.001, .01 * row @ self.beta)
            depth = int(np.clip(2 * round(1.5 / estimate / 2), 2, 256))
            reference = self.exchange({'type': 'experiment', 'matching': matching, 'depth': 0, 'shots': 96})
            decayed = self.exchange({'type': 'experiment', 'matching': matching, 'depth': depth, 'shots': 529})
            self.records.append((row, depth, reference, decayed))
            self.pair_counts += row[self.offset:]
        self.fit(exact=True)

    def run(self):
        self.acquire()
        targets = self.exchange({'type': 'ready'})['matchings']
        rates = [.01 * self.features(matching) @ self.beta for matching in targets]
        predictions = [(1 - 4. ** (-self.qubits)) * (-math.expm1(-max(0., rate))) for rate in rates]
        self.exchange({'type': 'final', 'predictions': predictions})


def exchange(message):
    print(json.dumps(message, allow_nan=False), flush=True)
    response = sys.stdin.readline()
    if not response:
        raise RuntimeError('evaluator_closed')
    return json.loads(response)


def main():
    hello = json.loads(sys.stdin.readline())
    Policy(hello, exchange).run()


if __name__ == '__main__':
    main()
