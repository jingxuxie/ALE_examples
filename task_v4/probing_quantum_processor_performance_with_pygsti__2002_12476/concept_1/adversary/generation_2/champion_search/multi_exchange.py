import argparse
import itertools
import json
import os
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np

from metrics import HERE, profile, write_json
from optimize import Search, normalize


class MultiSearch(Search):
    def __init__(self, seconds, seed, broaden):
        super().__init__(seconds, seed)
        self.broaden = broaden
        if broaden:
            with np.load(HERE / "own_training.npz", allow_pickle=False) as source:
                self.data.features = np.concatenate([self.data.features, source["features"]])
                self.data.families = np.concatenate([self.data.families, source["families"]])
                self.data.parameters = np.concatenate([self.data.parameters, source["parameters"]])
            self.data.reference = profile(self.data.features, self.data.reference_counts, direct=True)
            self.rows = self.data.features * np.sqrt(64 * self.available / self.costs)[None, :, None]
            self.family_masks = [self.data.families == family for family in np.unique(self.data.families)]
            self.normalizers = np.array([self.data.reference["intact"][mask].mean() for mask in self.family_masks])
        self.log("multiswap_configuration", scenarios=len(self.data.families), own_generated_training=broaden,
                 main_held_out_benchmark_used=False)

    def consider(self, counts, label):
        super().consider(counts, label)
        if self.best is not None:
            self.best[1]["private_training_scenarios"] = len(self.data.families)
            self.best[1]["main_600_used_for_fitting"] = False
            write_json(HERE / "score.json", self.best[1])

    def multi(self, start, rounds=10):
        support = np.flatnonzero(start)
        allocation, value = self.solve(support, start[support] * self.costs[support] / self.available, iterations=100)
        self.consider(self.integerize(support, allocation), "multiswap_fixed")
        for iteration in range(rounds):
            if time.monotonic() >= self.deadline or self.best[1]["passed"]:
                break
            state = self.state(allocation, support, all_gradients=True)
            ratios = np.concatenate([state[5] / 5, [state[4] / 4]])
            active = ratios >= .8 * ratios.max()
            addition_scores = np.mean(state[3][:-1][active], axis=0)
            addition_scores[support] = -np.inf
            ranked = np.argsort(addition_scores)[::-1]
            addition_pool = list(ranked[:4]) + list(self.rng.choice(ranked[4:60], 4, replace=False))
            pairs = list(itertools.combinations(addition_pool, 2))
            self.rng.shuffle(pairs)
            pairs = sorted(pairs[:16], key=lambda pair: -(addition_scores[pair[0]] + addition_scores[pair[1]]))
            best = None
            for additions in pairs:
                extended = np.concatenate([support, np.array(additions)])
                extended_allocation, extended_value = self.solve(extended, np.append(allocation * .94, [.03, .03]), iterations=60)
                removal_pool = np.unique(np.concatenate([np.argsort(extended_allocation)[:7],
                                                         np.argsort(extended_allocation / self.upper[extended])[:5]]))
                removal_trials = []
                for removals in itertools.combinations(removal_pool, 2):
                    keep = np.ones(len(extended), dtype=bool)
                    keep[list(removals)] = False
                    if np.array_equal(np.sort(extended[keep]), np.sort(support)):
                        continue
                    provisional = normalize(extended_allocation[keep], self.upper[extended[keep]])
                    trial_state = self.state(provisional, extended[keep])
                    removal_trials.append((self.merit(trial_state), keep))
                removal_trials.sort(key=lambda entry: entry[0])
                for unused, keep in removal_trials[:2]:
                    trial_support = extended[keep]
                    trial_allocation, trial_value = self.solve(trial_support, extended_allocation[keep], iterations=70)
                    if trial_value < value - 1e-5 and (best is None or trial_value < best[0]):
                        best = trial_value, trial_support, trial_allocation
                if time.monotonic() >= self.deadline:
                    break
            if best is None:
                self.log("multiswap_stationary", iteration=iteration, objective=value)
                if iteration >= 2:
                    break
                continue
            value, support, allocation = best
            self.consider(self.integerize(support, allocation), "two_support_exchange")
            self.log("multiswap", iteration=iteration, objective=value)

    def run_multi(self):
        start = np.array(json.loads((HERE / "design.json").read_text())["batches"])
        self.consider(start, "multiswap_initial")
        self.multi(start)
        self.log("multiswap_finished", core=self.best[1]["core_score"], worst=self.best[1]["worst_family_score"],
                 intact=self.best[1]["intact_mean_ratio"], passed=self.best[1]["passed"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=480)
    parser.add_argument("--seed", type=int, default=371506)
    parser.add_argument("--broaden", action="store_true")
    args = parser.parse_args()
    MultiSearch(args.seconds, args.seed, args.broaden).run_multi()


if __name__ == "__main__":
    main()
