import argparse
import json
import os
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np

from rebased import Benchmark, HERE, OLD, write_json
from search import Search


class RebasedSearch(Search):
    def __init__(self, seconds, seed):
        self.started = time.monotonic()
        self.deadline = self.started + seconds
        self.rng = np.random.default_rng(seed)
        self.data = Benchmark()
        self.data.freeze()
        self.costs = self.data.costs
        self.contract = self.data.contract
        self.available = self.contract["execution_budget_ticks"] - 24 * self.contract["setup_ticks"]
        self.rows = self.data.features * np.sqrt(64 * self.available / self.costs)[None, :, None]
        self.upper = 48 * self.costs / self.available
        self.best = {"double": None}
        self.best_counts = {"double": self.data.reference_counts.copy()}
        self.mode = "double"
        self.temperature_ratio = 0.0005
        self.family_boost = None
        self.evaluations = 0
        self.allowed_candidates = np.arange(len(self.costs))
        self.log("start", seconds=seconds, seed=seed,
                 reference_intact=float(self.data.reference["intact"].mean()),
                 reference_double=float(self.data.reference["double"].mean()))

    def log(self, event, **values):
        record = dict(elapsed_seconds=time.monotonic() - self.started, event=event, **values)
        with (HERE / "search.jsonl").open("a") as stream:
            stream.write(json.dumps(record, allow_nan=False) + "\n")
        print(json.dumps(record, allow_nan=False), flush=True)

    def state(self, allocation, support, all_gradients=False):
        state = list(super().state(allocation, support, all_gradients))
        state[0] = 0.15 * state[0] + float(np.mean(state[4]))
        state[1] = 0.15 * state[1] + np.mean(state[5], axis=0)
        return tuple(state)

    def integerize(self, support, allocation):
        counts = np.zeros(len(self.costs), dtype=np.int64)
        counts[support] = np.minimum(48, np.floor(allocation * self.available / self.costs[support] + 1e-8)).astype(int)
        while True:
            remaining = self.contract["execution_budget_ticks"] - counts @ self.costs - np.count_nonzero(counts) * self.contract["setup_ticks"]
            prices = self.costs[support] + (counts[support] == 0) * self.contract["setup_ticks"]
            legal = (counts[support] < 48) & (prices <= remaining)
            if not np.any(legal):
                break
            state = self.state(counts[support] * self.costs[support] / self.available, support)
            gradient = state[1] + max(0, state[2] - 1.175) * 100 * state[3]
            violations = np.maximum(state[4] - 0.685, 0)
            gradient += 30 * np.sum(violations[:, None] * state[5], axis=0)
            gain = -gradient * self.costs[support] / self.available / prices
            gain[~legal] = -np.inf
            counts[support[int(np.argmax(gain))]] += 1
        return counts

    def consider(self, counts, label):
        self.evaluations += 1
        try:
            scores = self.data.evaluate(counts, direct=False)
        except (ValueError, np.linalg.LinAlgError):
            return
        if self.best["double"] is not None and self.key(scores, "double") >= self.key(self.best["double"], "double") - 1e-8:
            return
        exact = self.data.evaluate(counts, direct=True)
        self.best["double"] = exact
        self.best_counts["double"] = counts.copy()
        write_json(HERE / "design.json", {"batches": counts.tolist()})
        write_json(HERE / "score.json", exact)
        self.log("improvement", label=label, core_score=exact["core_score"],
                 worst_family_score=exact["worst_family_score"], intact_ratio=exact["intact_mean_ratio"],
                 passed=exact["passed"], families=exact["double"]["family_scores"],
                 allocation={str(index): int(counts[index]) for index in np.flatnonzero(counts)})

    def run(self):
        starts = [("prior_frozen_double", OLD / "best_double.json"),
                  ("prior_refined_double", OLD / "double_design.json"),
                  ("prior_single", OLD / "single_design.json"),
                  ("champion", HERE / "reference_design.json")]
        if (HERE / "design.json").exists():
            starts.insert(0, ("resume", HERE / "design.json"))
        designs = []
        for label, path in starts:
            counts = np.array(json.loads(path.read_text())["batches"], dtype=int)
            self.consider(counts, label)
            support = np.flatnonzero(counts)
            allocation, value = self.solve(support, counts[support] * self.costs[support] / self.available, iterations=160)
            rounded = self.integerize(support, allocation)
            self.consider(rounded, label + "/continuous")
            designs.append((value, rounded))
            self.log("start_completed", label=label, objective=value)
            if self.best["double"]["passed"]:
                break
        designs.sort(key=lambda item: item[0])
        generation = 0
        while time.monotonic() < self.deadline and not self.best["double"]["passed"]:
            start = designs[generation % len(designs)][1] if generation < len(designs) else self.best_counts["double"].copy()
            self.log("portfolio_exchange", generation=generation)
            result = self.exchange(start, rounds=10, width=12)
            self.consider(result, "portfolio_final")
            generation += 1
            if generation > 2 * len(designs):
                break
        self.log("finished", evaluations=self.evaluations, passed=self.best["double"]["passed"],
                 core_score=self.best["double"]["core_score"],
                 worst_family_score=self.best["double"]["worst_family_score"],
                 intact_ratio=self.best["double"]["intact_mean_ratio"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=950)
    parser.add_argument("--seed", type=int, default=39517202)
    args = parser.parse_args()
    RebasedSearch(args.seconds, args.seed).run()


if __name__ == "__main__":
    main()
