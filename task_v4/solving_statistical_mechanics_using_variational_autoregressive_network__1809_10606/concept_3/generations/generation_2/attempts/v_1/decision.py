import argparse
import time

import numpy as np
from scipy.special import expit


class DecisionProblem:
    def __init__(self, draws):
        self.draws = draws.reshape(-1, 48, 64)
        self.mean = self.draws.mean(axis=0)
        self.indices = [np.flatnonzero((self.draws[:, query].max(axis=0) > 1e-5) |
                                      (self.mean[query] > 1e-8)) for query in range(48)]
        self.starts = np.cumsum([0] + [len(index) + 1 for index in self.indices])[:-1]
        self.groups = np.asarray([query % 12 >= 6 for query in range(48)])
        self.features = self.compress(self.draws)
        self.entropies = np.add.reduceat(self.features * np.log(np.maximum(self.features, 1e-300)), self.starts, axis=-1)

    def compress(self, predictions):
        parts = []
        for query, index in enumerate(self.indices):
            selected = predictions[..., query, index]
            other = np.ones(64, dtype=bool)
            other[index] = False
            tail = predictions[..., query, other].sum(axis=-1, keepdims=True)
            parts.extend([selected, tail])
        return np.concatenate(parts, axis=-1)

    def expand(self, features):
        probabilities = self.mean.copy()
        for query, index in enumerate(self.indices):
            start = self.starts[query]
            other = np.ones(64, dtype=bool)
            other[index] = False
            probabilities[query, index] = features[start:start + len(index)]
            if other.any():
                probabilities[query, other] *= features[start + len(index)] / probabilities[query, other].sum()
        probabilities = np.maximum(probabilities, 1e-300)
        return probabilities / probabilities.sum(axis=1, keepdims=True)

    def scores(self, probabilities):
        features = self.compress(probabilities)
        kl = self.entropies - np.add.reduceat(self.features * np.log(np.maximum(features, 1e-300)), self.starts, axis=-1)
        tv = np.add.reduceat(np.abs(self.features - features), self.starts, axis=-1) / 2
        ratio = np.maximum.reduce([kl.mean(axis=-1) / .020,
                                   kl[:, ~self.groups].mean(axis=-1) / .035,
                                   kl[:, self.groups].mean(axis=-1) / .035,
                                   tv.max(axis=-1) / .120])
        return ratio, kl, tv

    def report(self, probabilities, name):
        score, kl, tv = self.scores(probabilities)
        print(name, "pass probability", np.mean(score <= 1), "expected KL", kl.mean(),
              "ratio quantiles", np.quantile(score, [.1, .25, .5, .9]), flush=True)
        return float(np.mean(score <= 1))


def cluster_candidates(problem, count, rng):
    probabilities = problem.mean.copy()
    candidates = [probabilities.copy()]
    coverages = [np.mean(problem.scores(probabilities)[0] <= 1)]
    total = len(problem.draws)
    started = time.time()
    for trial in range(count):
        if trial == 0:
            probabilities = problem.mean.copy()
        else:
            center = problem.draws[rng.integers(total)]
            probabilities = center * 0.8 + problem.mean * 0.2
        fraction = rng.choice([.02, .04, .06, .08, .12, .18])
        closest_count = max(20, int(total * fraction))
        for iteration in range(12):
            score = problem.scores(probabilities)[0]
            closest = np.argpartition(score, closest_count)[:closest_count]
            next_probabilities = .98 * problem.draws[closest].mean(axis=0) + .02 * problem.mean
            coverage = np.mean(score <= 1)
            candidates.append(probabilities.copy())
            coverages.append(coverage)
            difference = np.abs(probabilities - next_probabilities).max()
            probabilities = next_probabilities
            if difference < 1e-4:
                break
        if trial % 10 == 0:
            print("cluster trial", trial, "best coverage", max(coverages), "elapsed", time.time() - started, flush=True)
    order = np.argsort(coverages)[::-1]
    diverse = []
    for index in order:
        candidate = candidates[index]
        if all(np.abs(candidate - previous).sum(axis=1).max() > .025 for previous in diverse):
            diverse.append(candidate)
        if len(diverse) >= 20:
            break
    return np.asarray(diverse)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive")
    parser.add_argument("--trials", type=int, default=80)
    parser.add_argument("--output", default="decision_candidates.npz")
    parser.add_argument("--train-all", action="store_true")
    args = parser.parse_args()
    archive = np.load(args.archive)
    chains = archive["predictions"]
    training = DecisionProblem(chains if args.train_all else chains[::2])
    validation = DecisionProblem(chains[1::2])
    print("training draws", len(training.draws), "validation draws", len(validation.draws),
          "features", training.features.shape, flush=True)
    training.report(training.mean, "training posterior mean")
    validation.report(training.mean, "validation posterior mean")
    for query in [36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47]:
        index = training.mean[query].argmax()
        print("query", query, "dominant outcome", index,
              "probability quantiles", np.quantile(training.draws[:, query, index], [.05, .25, .5, .75, .95]), flush=True)
    candidates = cluster_candidates(training, args.trials, np.random.default_rng(456))
    training_scores = []
    validation_scores = []
    for index, candidate in enumerate(candidates):
        training_scores.append(training.report(candidate, f"candidate {index} train"))
        validation_scores.append(validation.report(candidate, f"candidate {index} validation"))
    np.savez(args.output, candidates=candidates, training_scores=training_scores, validation_scores=validation_scores)


if __name__ == "__main__":
    main()
