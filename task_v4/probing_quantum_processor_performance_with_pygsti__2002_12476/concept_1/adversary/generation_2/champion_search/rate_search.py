import argparse
import itertools
import json
import os
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np

from metrics import HERE, information_state, loss_table, write_json
from multi_exchange import MultiSearch
from optimize import normalize


class RateSearch(MultiSearch):
    def __init__(self, seconds, seed, broaden):
        super().__init__(seconds, seed, broaden)
        with np.load(HERE / "training_source.npz", allow_pickle=False) as source:
            nominal = source["nominal_features"].copy()
        self.rate_eligible = np.linalg.norm(nominal[:, 9:12], axis=1) > 1e-6
        self.log("structured_rate_search", eligible=int(self.rate_eligible.sum()),
                 nominal_classification_only=True, evaluation_uses_full_nonlinear_features=True)

    def screened(self, support, allocation, selected):
        rows = self.rows[selected][:, support]
        base = information_state(rows, allocation)
        positions = np.flatnonzero(self.rate_eligible[support])
        cases = np.array(list(itertools.combinations(positions, 3)), dtype=int)
        table, unused, unused_state = loss_table(rows, allocation, 3, state=base, case_set=cases)
        loss = table.max(axis=1)
        families = self.data.families[selected]
        reference = self.data.reference["intact"][selected]
        family_ratios = [loss[families == family].mean() / reference[families == family].mean() / 5 for family in np.unique(families)]
        ratio = max(loss.mean() / reference.mean() / 4, max(family_ratios))
        intact = base[2].mean() / reference.mean()
        return float(np.log(ratio) + 12 * max(0, intact - 1.2))

    def run_structured(self):
        counts = np.array(json.loads((HERE / "design.json").read_text())["batches"])
        self.consider(counts, "structured_initial")
        support = np.flatnonzero(counts)
        allocation, value = self.solve(support, counts[support] * self.costs[support] / self.available, iterations=110)
        self.consider(self.integerize(support, allocation), "structured_fixed")
        for iteration in range(30):
            if time.monotonic() >= self.deadline or self.best[1]["passed"]:
                break
            state = self.state(allocation, support, all_gradients=True)
            ratios = np.concatenate([state[5] / 5, [state[4] / 4]])
            active = ratios >= .8 * ratios.max()
            addition_scores = np.mean(state[3][:-1][active], axis=0)
            addition_scores[~self.rate_eligible] = -np.inf
            addition_scores[support] = -np.inf
            ranked = np.argsort(addition_scores)[::-1]
            ranked = ranked[np.isfinite(addition_scores[ranked])]
            pool = list(ranked[:14]) + list(self.rng.choice(ranked[14:90], 8, replace=False))
            selected = np.concatenate([self.rng.choice(np.flatnonzero(self.data.families == family), 3, replace=False)
                                       for family in np.unique(self.data.families)])
            old_rate = np.flatnonzero(self.rate_eligible[support])
            candidates = []
            for local in old_rate:
                for addition in pool:
                    trial_support = support.copy()
                    trial_support[local] = addition
                    trial_allocation = normalize(allocation, self.upper[trial_support])
                    score = self.screened(trial_support, trial_allocation, selected)
                    candidates.append((score, trial_support, trial_allocation))
            addition_pairs = list(itertools.combinations(pool, 2))
            self.rng.shuffle(addition_pairs)
            addition_pairs = addition_pairs[:120]
            for removals in itertools.combinations(old_rate, 2):
                for additions in addition_pairs:
                    trial_support = support.copy()
                    trial_support[list(removals)] = additions
                    trial_allocation = normalize(allocation, self.upper[trial_support])
                    score = self.screened(trial_support, trial_allocation, selected)
                    candidates.append((score, trial_support, trial_allocation))
                if time.monotonic() >= self.deadline:
                    break
            candidates.sort(key=lambda entry: entry[0])
            self.log("rate_screened", iteration=iteration, candidates=len(candidates), best_screen=candidates[0][0])
            best = None
            seen = set()
            refined = 0
            for unused, trial_support, trial_allocation in candidates:
                fingerprint = tuple(sorted(trial_support))
                if fingerprint in seen:
                    continue
                seen.add(fingerprint)
                trial_state = self.state(trial_allocation, trial_support)
                if self.merit(trial_state) > value + 2.0 and refined >= 5:
                    continue
                new_allocation, new_value = self.solve(trial_support, trial_allocation, iterations=85)
                refined += 1
                if new_value < value - 1e-5 and (best is None or new_value < best[0]):
                    best = new_value, trial_support, new_allocation
                    self.consider(self.integerize(trial_support, new_allocation), "rate_intermediate")
                if refined >= 14 or time.monotonic() >= self.deadline or self.best[1]["passed"]:
                    break
            if best is None:
                self.log("rate_stationary", iteration=iteration, objective=value)
                if iteration >= 2:
                    break
                continue
            value, support, allocation = best
            self.consider(self.integerize(support, allocation), "rate_exchange")
            self.log("rate_exchange", iteration=iteration, objective=value, rate_slots=int(self.rate_eligible[support].sum()))
        self.log("rate_finished", core=self.best[1]["core_score"], worst=self.best[1]["worst_family_score"],
                 intact=self.best[1]["intact_mean_ratio"], passed=self.best[1]["passed"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=850)
    parser.add_argument("--seed", type=int, default=837210)
    parser.add_argument("--broaden", action="store_true")
    args = parser.parse_args()
    RateSearch(args.seconds, args.seed, args.broaden).run_structured()


if __name__ == "__main__":
    main()
