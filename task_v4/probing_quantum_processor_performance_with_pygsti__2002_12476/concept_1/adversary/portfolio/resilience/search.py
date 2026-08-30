import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp

from metrics import Benchmark, HERE, ROOT, REFERENCE, TARGETS, covariance, loss_table, profile, score_profiles


def capped_normalize(values, upper):
    values = np.maximum(values, 1e-25)
    if upper.sum() < 1:
        return upper.copy()
    lower, higher = 0., 1.
    while np.minimum(values * higher, upper).sum() < 1:
        higher *= 2
    for iteration in range(70):
        middle = (lower + higher) / 2
        if np.minimum(values * middle, upper).sum() > 1:
            higher = middle
        else:
            lower = middle
    return np.minimum(values * ((lower + higher) / 2), upper)


class Search:
    def __init__(self, seconds, seed):
        self.started = time.monotonic()
        self.deadline = self.started + seconds
        self.rng = np.random.default_rng(seed)
        self.data = Benchmark()
        self.costs = self.data.costs
        self.contract = self.data.contract
        self.available = self.contract["execution_budget_ticks"] - 24 * self.contract["setup_ticks"]
        self.rows = self.data.features * np.sqrt(64 * self.available / self.costs)[None, :, None]
        self.upper = self.contract["max_batches_per_circuit"] * self.costs / self.available
        self.best = {"single": None, "double": None}
        self.best_counts = {"single": self.data.reference_counts.copy(), "double": self.data.reference_counts.copy()}
        self.mode = "single"
        self.temperature_ratio = 0.004
        self.family_boost = None
        self.evaluations = 0
        self.allowed_candidates = np.arange(len(self.costs))
        frozen = dict(targets=TARGETS, resource_contract=self.contract,
                      reference_design_sha256=hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
                      benchmark_sha256=hashlib.sha256((ROOT / "evaluator/hidden/benchmark.npz").read_bytes()).hexdigest(),
                      objective="mean over operating points of each point's maximum risk across all selected-circuit deletions",
                      no_reallocation_after_loss=True, targets_fixed_before_search=True,
                      private_feasibility_only=True, fresh_submissions_read=False)
        if not (HERE / "contract.json").exists():
            (HERE / "contract.json").write_text(json.dumps(frozen, indent=2) + "\n")
            (HERE / "reference_design.json").write_bytes(REFERENCE.read_bytes())
            (HERE / "reference_scores.json").write_text(json.dumps(self.data.evaluate(self.data.reference_counts), indent=2) + "\n")
        self.log("start", seconds=seconds, seed=seed, targets=TARGETS,
                 reference_intact=float(self.data.reference["intact"].mean()),
                 reference_single=float(self.data.reference["single"].mean()),
                 reference_double=float(self.data.reference["double"].mean()))

    def log(self, event, **values):
        result = dict(elapsed_seconds=time.monotonic() - self.started, event=event, **values)
        with (HERE / "search.jsonl").open("a") as stream:
            stream.write(json.dumps(result, allow_nan=False) + "\n")
        print(json.dumps(result, allow_nan=False), flush=True)

    def state(self, allocation, support, all_gradients=False):
        rows = self.rows[:, support]
        base = covariance(rows, allocation)
        order = 1 if self.mode == "single" else 2
        table, cases, base = loss_table(rows, allocation, order, base)
        top_count = min(3, table.shape[1])
        selected = np.argpartition(table, -top_count, axis=1)[:, -top_count:]
        chosen = cases[selected]
        information = np.repeat(base[0][:, None], top_count, axis=1)
        scenario = np.arange(len(rows))[:, None]
        slot = np.arange(top_count)[None]
        for deletion in range(order):
            local = chosen[:, :, deletion]
            removed_rows = rows[scenario, local]
            information -= allocation[local, None, None] * (removed_rows[:, :, :, None] @ removed_rows[:, :, None, :])
        inverted = np.linalg.inv(information)
        risks = np.trace(inverted[:, :, :12, :12], axis1=2, axis2=3)
        temperature = self.temperature_ratio * self.data.reference[self.mode].mean()
        logits = risks / temperature
        normalizer = logsumexp(logits, axis=1)
        soft_weights = np.exp(logits - normalizer[:, None])
        scenario_weights = np.ones(len(rows)) / len(rows) / self.data.reference[self.mode].mean()
        if self.family_boost is not None:
            mask = self.data.families == self.family_boost
            scenario_weights[mask] += 0.45 / np.sum(mask) / self.data.reference[self.mode][mask].mean()
        objective = float(scenario_weights @ (temperature * normalizer))
        gradient_rows = self.rows if all_gradients else rows
        projection = gradient_rows[:, None] @ inverted[:, :, :, :12]
        derivatives = -np.sum(projection * projection, axis=3)
        for deletion in range(order):
            local = chosen[:, :, deletion]
            removed = support[local] if all_gradients else local
            derivatives[scenario, slot, removed] = 0
        gradient = np.sum(scenario_weights[:, None, None] * soft_weights[:, :, None] * derivatives, axis=(0, 1))
        intact_projected = gradient_rows @ base[1][:, :, :12]
        intact_gradient = -np.mean(np.sum(intact_projected * intact_projected, axis=2), axis=0) / self.data.reference["intact"].mean()
        intact_ratio = float(base[2].mean() / self.data.reference["intact"].mean())
        point_gradient = np.sum(soft_weights[:, :, None] * derivatives, axis=1)
        family_ratios = []
        family_gradients = []
        for family in np.unique(self.data.families):
            mask = self.data.families == family
            normalizer_family = self.data.reference[self.mode][mask].mean()
            family_ratios.append(float((temperature * normalizer[mask]).mean() / normalizer_family))
            family_gradients.append(point_gradient[mask].mean(axis=0) / normalizer_family)
        return (objective, gradient, intact_ratio, intact_gradient, np.array(family_ratios), np.array(family_gradients),
                temperature * normalizer, point_gradient, base[2], -np.sum(intact_projected * intact_projected, axis=2))

    def solve(self, support, allocation=None, iterations=90):
        support = np.array(support, dtype=int)
        if allocation is None:
            allocation = np.ones(len(support))
        allocation = capped_normalize(allocation, self.upper[support])
        cached = {}
        def state_at(value):
            if "allocation" not in cached or not np.array_equal(value, cached["allocation"]):
                cached["allocation"] = value.copy()
                cached["state"] = self.state(value, support)
            return cached["state"]
        def objective(value):
            state = state_at(value)
            return state[0], state[1]
        def guard(value):
            return 1.187 - state_at(value)[2]
        def guard_gradient(value):
            return -state_at(value)[3]
        def family_guard(value):
            return 1 - TARGETS[self.mode + "_family_reduction"] - 0.004 - state_at(value)[4]
        def family_guard_gradient(value):
            return -state_at(value)[5]
        result = minimize(objective, allocation, jac=True, method="SLSQP",
                          bounds=list(zip(np.zeros(len(support)), self.upper[support])),
                          constraints=[{"type": "ineq", "fun": lambda value: 1 - value.sum(),
                                        "jac": lambda value: -np.ones(len(value))},
                                       {"type": "ineq", "fun": guard, "jac": guard_gradient},
                                       {"type": "ineq", "fun": family_guard, "jac": family_guard_gradient}],
                          options={"maxiter": iterations, "ftol": 1e-8})
        allocation = np.clip(result.x, 0, self.upper[support])
        if allocation.sum() > 1:
            allocation /= allocation.sum()
        state = self.state(allocation, support)
        value = state[0] + 20 * max(0., state[2] - 1.19)
        value += 10 * np.maximum(state[4] - (1 - TARGETS[self.mode + "_family_reduction"]), 0).sum()
        return allocation, float(value)

    def integerize(self, support, allocation):
        counts = np.zeros(len(self.costs), dtype=np.int64)
        counts[support] = np.minimum(48, np.floor(allocation * self.available / self.costs[support])).astype(int)
        while True:
            remaining = self.contract["execution_budget_ticks"] - counts @ self.costs - np.count_nonzero(counts) * self.contract["setup_ticks"]
            prices = self.costs[support] + (counts[support] == 0) * self.contract["setup_ticks"]
            legal = (counts[support] < 48) & (prices <= remaining)
            if not np.any(legal):
                break
            allocation = counts[support] * self.costs[support] / self.available
            state = self.state(allocation, support)
            multiplier = max(0, state[2] - 1.17) * 100
            gain = -(state[1] + multiplier * state[3]) * self.costs[support] / self.available / prices
            gain[~legal] = -np.inf
            counts[support[int(np.argmax(gain))]] += 1
        return counts

    def key(self, scores, mode):
        core_ratio = 1 - scores[mode]["core_score"]
        family_ratio = 1 - scores[mode]["worst_family_score"]
        violation = max(0, scores["intact_mean_ratio"] - 1.2) * 30
        violation += max(0, family_ratio - (1 - TARGETS[mode + "_family_reduction"])) * 10
        return core_ratio + violation + (0 if scores[mode]["passed"] else 10)

    def consider(self, counts, label):
        self.evaluations += 1
        try:
            scores = self.data.evaluate(counts, direct=False)
        except (ValueError, np.linalg.LinAlgError):
            return
        for mode in ["single", "double"]:
            if self.best[mode] is None or self.key(scores, mode) < self.key(self.best[mode], mode) - 1e-7:
                exact = self.data.evaluate(counts, direct=True)
                self.best[mode] = exact
                self.best_counts[mode] = counts.copy()
                (HERE / f"best_{mode}.json").write_text(json.dumps({"batches": counts.tolist()}) + "\n")
                (HERE / f"best_{mode}_score.json").write_text(json.dumps(exact, indent=2) + "\n")
                self.log("improvement", mode=mode, label=label, intact_ratio=exact["intact_mean_ratio"],
                         single_core=exact["single"]["core_score"], single_worst=exact["single"]["worst_family_score"],
                         single_passed=exact["single"]["passed"], double_core=exact["double"]["core_score"],
                         double_worst=exact["double"]["worst_family_score"], double_passed=exact["double"]["passed"],
                         allocation={str(index): int(counts[index]) for index in np.flatnonzero(counts)})

    def exchange(self, start, rounds=8, width=9):
        support = np.flatnonzero(start)
        allocation, value = self.solve(support, start[support] * self.costs[support] / self.available)
        self.consider(self.integerize(support, allocation), "fixed_support")
        if self.best[self.mode][self.mode]["passed"]:
            return self.best_counts[self.mode].copy()
        for iteration in range(rounds):
            if time.monotonic() > self.deadline:
                break
            state = self.state(allocation, support, all_gradients=True)
            addition_scores = -state[1] - max(0, state[2] - 1.17) * 20 * state[3]
            violated = state[4] > 1 - TARGETS[self.mode + "_family_reduction"]
            if np.any(violated):
                addition_scores -= 10 * np.sum(state[5][violated], axis=0)
            addition_scores[support] = -np.inf
            permitted = np.zeros(len(self.costs), dtype=bool)
            permitted[self.allowed_candidates] = True
            addition_scores[~permitted] = -np.inf
            available = np.flatnonzero(np.isfinite(addition_scores))
            additions = available[np.argsort(addition_scores[available])[-width:][::-1]]
            best = None
            for addition in additions:
                extended = np.append(support, addition)
                extended_allocation, extended_value = self.solve(extended, np.append(allocation * 0.965, 0.035), iterations=65)
                if len(support) < 24 and extended_value < value - 1e-5:
                    if best is None or extended_value < best[0]:
                        best = extended_value, extended, extended_allocation
                remove_order = list(np.argsort(extended_allocation / self.upper[extended])[:3])
                remove_order += list(np.argsort(extended_allocation)[:2])
                removal_scores = []
                for removal in range(len(extended)):
                    keep = np.arange(len(extended)) != removal
                    provisional = capped_normalize(extended_allocation[keep], self.upper[extended[keep]])
                    trial = self.state(provisional, extended[keep])
                    removal_scores.append(trial[0] + 20 * max(0, trial[2] - 1.19) +
                                          10 * np.maximum(trial[4] - (1 - TARGETS[self.mode + "_family_reduction"]), 0).sum())
                remove_order = list(np.argsort(removal_scores)[:2]) + remove_order[:2]
                for removal in dict.fromkeys(remove_order):
                    if removal == len(support):
                        continue
                    keep = np.arange(len(extended)) != removal
                    trial_support = extended[keep]
                    trial_allocation, trial_value = self.solve(trial_support, extended_allocation[keep], iterations=65)
                    if trial_value < value - 2e-5 and (best is None or trial_value < best[0]):
                        best = trial_value, trial_support, trial_allocation
                if time.monotonic() > self.deadline:
                    break
            if best is None:
                self.log("support_stationary", mode=self.mode, objective=value, iteration=iteration)
                break
            value, support, allocation = best
            self.consider(self.integerize(support, allocation), "support_exchange")
            self.log("exchange", mode=self.mode, iteration=iteration, objective=value,
                     elapsed=time.monotonic() - self.started)
            if self.best[self.mode][self.mode]["passed"]:
                break
        return self.integerize(support, allocation)

    def run(self):
        warm = []
        for mode in ["single", "double"]:
            path = HERE / f"best_{mode}.json"
            if path.exists():
                warm.append(np.array(json.loads(path.read_text())["batches"]))
        self.consider(self.data.reference_counts, "original_reference")
        for counts in warm:
            self.consider(counts, "private_warm_start")
        self.exchange(self.best_counts["single"], rounds=6, width=10)
        generation = 0
        while time.monotonic() < self.deadline - 30:
            generation += 1
            if self.best["single"]["single"]["passed"]:
                self.mode = "double"
            else:
                self.mode = "single"
            score = self.best[self.mode]
            family = min(score[self.mode]["family_scores"], key=lambda name: score[self.mode]["family_scores"][name]["reduction"])
            self.family_boost = family if generation % 3 == 1 else None
            self.temperature_ratio = 0.0015 if generation % 3 == 2 else 0.004
            start = self.best_counts[self.mode].copy()
            if generation % 4 == 0:
                start = self.best_counts["single"].copy()
            self.log("restart", mode=self.mode, generation=generation, family_boost=self.family_boost,
                     temperature_ratio=self.temperature_ratio)
            self.exchange(start, rounds=6, width=10)
            if self.best["single"]["single"]["passed"] and self.best["double"]["double"]["passed"]:
                self.log("both_targets_demonstrated")
                break
        chosen = "double" if self.best["double"]["double"]["passed"] else "single"
        (HERE / "design.json").write_text(json.dumps({"batches": self.best_counts[chosen].tolist()}) + "\n")
        (HERE / "score.json").write_text(json.dumps(self.best[chosen], indent=2) + "\n")
        summary = dict(single_feasible=self.best["single"]["single"]["passed"],
                       double_feasible=self.best["double"]["double"]["passed"], selected_design=chosen,
                       seconds=time.monotonic() - self.started, evaluated_designs=self.evaluations,
                       private_optimizer=True, fresh_attempts_read=False, public_files_changed=False,
                       single=self.best["single"], double=self.best["double"])
        (HERE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        self.log("complete", selected_design=chosen, single_feasible=summary["single_feasible"],
                 double_feasible=summary["double_feasible"], evaluated_designs=self.evaluations)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=850)
    parser.add_argument("--seed", type=int, default=7148420)
    args = parser.parse_args()
    Search(args.seconds, args.seed).run()


if __name__ == "__main__":
    main()
