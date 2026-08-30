import argparse
import json
import os
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp

from metrics import Benchmark, HERE, ROOT, information_state, loss_table, write_json


def normalize(values, upper):
    values = np.maximum(values, 1e-20)
    if upper.sum() <= 1:
        return upper.copy()
    lower, higher = 0., 1.
    while np.minimum(values * higher, upper).sum() < 1:
        higher *= 2
    for iteration in range(60):
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
        self.data.freeze()
        self.costs = self.data.costs
        self.available = 1600000 - 24 * 12000
        self.rows = self.data.features * np.sqrt(64 * self.available / self.costs)[None, :, None]
        self.upper = 48 * self.costs / self.available
        self.family_masks = [self.data.families == family for family in np.unique(self.data.families)]
        self.normalizers = np.array([self.data.reference["intact"][mask].mean() for mask in self.family_masks])
        self.best = None
        self.best_counts = None
        self.log("started", seconds=seconds, seed=seed, targets="private provisional 4x/5x usability caps",
                 champion_intact=float(self.data.reference["intact"].mean()),
                 champion_triple=float(self.data.reference["loss_3"].mean()))

    def log(self, event, **values):
        record = dict(elapsed=time.monotonic() - self.started, event=event, **values)
        with (HERE / "search.jsonl").open("a") as stream:
            stream.write(json.dumps(record, allow_nan=False) + "\n")
        print(json.dumps(record, allow_nan=False), flush=True)

    def state(self, allocation, support, all_gradients=False):
        rows = self.rows[:, support]
        base = information_state(rows, allocation)
        table, cases, base = loss_table(rows, allocation, 3, base)
        top_count = 4
        top_indices = np.argpartition(table, -top_count, axis=1)[:, -top_count:]
        selected = cases[top_indices]
        information = np.repeat(base[0][:, None], top_count, axis=1)
        scenario = np.arange(len(rows))[:, None]
        for slot in range(3):
            local = selected[:, :, slot]
            removed = rows[scenario, local]
            information -= allocation[local, None, None] * removed[:, :, :, None] * removed[:, :, None, :]
        covariance = np.linalg.inv(information)
        risks = np.trace(covariance[:, :, :12, :12], axis1=2, axis2=3)
        temperature = .08
        logarithms = risks / temperature
        normalizer = logsumexp(logarithms, axis=1)
        weights = np.exp(logarithms - normalizer[:, None])
        point_risk = temperature * normalizer
        gradient_rows = self.rows if all_gradients else rows
        projected = gradient_rows[:, None] @ covariance[:, :, :, :12]
        derivatives = -np.sum(projected ** 2, axis=3)
        for slot in range(3):
            local = selected[:, :, slot]
            removed = support[local] if all_gradients else local
            derivatives[scenario, np.arange(top_count)[None], removed] = 0
        point_gradient = np.sum(weights[:, :, None] * derivatives, axis=1)
        mean_risk = point_risk.mean()
        mean_gradient = point_gradient.mean(axis=0)
        family_means = np.array([point_risk[mask].mean() for mask in self.family_masks])
        family_gradients = np.array([point_gradient[mask].mean(axis=0) for mask in self.family_masks])
        intact_projection = gradient_rows @ base[1][:, :, :12]
        intact_gradient = -np.mean(np.sum(intact_projection ** 2, axis=2), axis=0)
        intact_mean = base[2].mean()
        intact_ratio = intact_mean / self.data.reference["intact"].mean()
        overall_ratio = mean_risk / self.data.reference["intact"].mean()
        family_ratios = family_means / self.normalizers
        objective = .5 * np.log(overall_ratio) + .5 * np.mean(np.log(family_ratios)) + .2 * np.log(intact_ratio)
        gradient = .5 * mean_gradient / mean_risk + .5 * np.mean(family_gradients / family_means[:, None], axis=0) + .2 * intact_gradient / intact_mean
        ratios = np.concatenate([family_ratios / 4.9, [overall_ratio / 3.92, intact_ratio / 1.18]])
        log_gradients = np.concatenate([family_gradients / family_means[:, None],
                                       (mean_gradient / mean_risk)[None], (intact_gradient / intact_mean)[None]], axis=0)
        guards = -np.log(ratios)
        return objective, gradient, guards, -log_gradients, overall_ratio, family_ratios, intact_ratio

    def solve(self, support, allocation=None, iterations=70):
        support = np.array(support)
        allocation = normalize(self.upper[support] if allocation is None else allocation, self.upper[support])
        lower = self.costs[support] / self.available
        allocation = np.clip(allocation, lower, self.upper[support])
        rows = self.rows[:, support]
        normalizer_intact = self.data.reference["intact"].mean()
        def intact_objective(values):
            state = information_state(rows, values)
            projected = rows @ state[1][:, :, :12]
            gradient = -np.mean(np.sum(projected ** 2, axis=2), axis=0) / normalizer_intact
            return state[2].mean() / normalizer_intact, gradient
        if intact_objective(allocation)[0] > 1.19:
            repaired = minimize(intact_objective, allocation, jac=True, method="SLSQP",
                bounds=list(zip(lower, self.upper[support])),
                constraints={"type": "ineq", "fun": lambda values: 1-values.sum(), "jac": lambda values: -np.ones(len(values))},
                options={"maxiter": 100, "ftol": 1e-9})
            allocation = np.clip(repaired.x, lower, self.upper[support])
            if repaired.fun > 1.198:
                state = self.state(allocation, support)
                return allocation, self.merit(state) + 1000
        cached = {}
        def state_at(values):
            if "values" not in cached or not np.array_equal(cached["values"], values):
                cached["values"] = values.copy()
                cached["state"] = self.state(values, support)
            return cached["state"]
        first_state = state_at(allocation)
        scale = max(1, first_state[4] / 4, np.max(first_state[5] / 5))
        initial = np.append(allocation, 1.)
        def epigraph_guard(values):
            state = state_at(values[:-1])
            ratios = np.concatenate([state[5] / 5, [state[4] / 4]])
            return values[-1] - ratios / scale
        def epigraph_gradient(values):
            state = state_at(values[:-1])
            ratios = np.concatenate([state[5] / 5, [state[4] / 4]])
            return np.column_stack([state[3][:-1] * ratios[:, None] / scale, np.ones(len(ratios))])
        def intact_guard(values):
            return 1.19 - state_at(values[:-1])[6]
        def intact_gradient(values):
            state = state_at(values[:-1])
            return np.append(state[3][-1] * state[6], 0.)
        result = minimize(lambda values: (values[-1], np.append(np.zeros(len(support)), 1.)), initial, jac=True, method="SLSQP",
            bounds=list(zip(lower, self.upper[support])) + [(0., None)],
            constraints=[{"type": "ineq", "fun": lambda values: 1 - values[:-1].sum(), "jac": lambda values: np.append(-np.ones(len(support)), 0.)},
                         {"type": "ineq", "fun": epigraph_guard, "jac": epigraph_gradient},
                         {"type": "ineq", "fun": intact_guard, "jac": intact_gradient}],
            options={"maxiter": iterations, "ftol": 2e-7})
        values = np.clip(result.x[:-1], lower, self.upper[support])
        if values.sum() > 1:
            values /= values.sum()
        state = self.state(values, support)
        value = self.merit(state)
        return values, float(value)

    def merit(self, state):
        return float(np.log(max(state[4] / 4, np.max(state[5] / 5))) + 30 * max(0, state[6] - 1.18))

    def integerize(self, support, allocation):
        counts = np.zeros(840, dtype=int)
        counts[support] = np.clip(np.floor(allocation * self.available / self.costs[support] + 1e-8), 1, 48).astype(int)
        while counts @ self.costs + 12000 * np.count_nonzero(counts) > 1600000:
            selected = support[counts[support] > 1]
            counts[selected[np.argmax(self.costs[selected])]] -= 1
        while True:
            remaining = 1600000 - counts @ self.costs - 12000 * np.count_nonzero(counts)
            legal = (counts[support] < 48) & (self.costs[support] <= remaining)
            if not np.any(legal):
                break
            state = self.state(counts[support] * self.costs[support] / self.available, support)
            if state[6] > 1.195:
                gain = state[3][-1].copy()
            else:
                ratios = np.concatenate([state[5] / 5, [state[4] / 4]])
                gain = np.mean(state[3][:-1][ratios >= .95 * ratios.max()], axis=0)
            gain[~legal] = -np.inf
            counts[support[np.argmax(gain)]] += 1
        return counts

    def consider(self, counts, label):
        score = self.data.evaluate(counts, direct=True)
        key = np.log(max(.25 / score["core_score"], .20 / score["worst_family_score"]))
        key += 1e6 if score["intact_mean_ratio"] > 1.2 else 0
        self.log("candidate", label=label, core=score["core_score"], worst=score["worst_family_score"],
                 mean_loss=score["candidate_triple_mean"], intact=score["intact_mean_ratio"], passed=score["passed"])
        if self.best is None or key < self.best[0]:
            self.best = key, score
            self.best_counts = counts.copy()
            write_json(HERE / "design.json", {"batches": counts.tolist()})
            write_json(HERE / "score.json", score)
            self.log("improvement", label=label, core=score["core_score"], worst=score["worst_family_score"],
                     mean_loss=score["candidate_triple_mean"], intact=score["intact_mean_ratio"], passed=score["passed"],
                     allocation={str(index): int(counts[index]) for index in np.flatnonzero(counts)})

    def exchange(self, counts, rounds=10, width=6):
        support = np.flatnonzero(counts)
        allocation, value = self.solve(support, counts[support] * self.costs[support] / self.available, iterations=100)
        self.consider(self.integerize(support, allocation), "fixed_support")
        for iteration in range(rounds):
            if time.monotonic() > self.deadline or self.best[1]["passed"]:
                break
            state = self.state(allocation, support, all_gradients=True)
            ratios = np.concatenate([state[5] / 5, [state[4] / 4]])
            active = ratios >= .90 * ratios.max()
            additions_score = np.mean(state[3][:-1][active], axis=0)
            if state[6] > 1.17:
                additions_score += 5 * state[3][-1]
            additions_score[support] = -np.inf
            additions = np.argsort(additions_score)[-width:][::-1]
            best = None
            for addition in additions:
                extended = np.append(support, addition)
                extended_allocation, extended_value = self.solve(extended, np.append(allocation * .96, .04), iterations=45)
                removal_scores = []
                for removal in range(len(extended)):
                    keep = np.arange(len(extended)) != removal
                    temporary = normalize(extended_allocation[keep], self.upper[extended[keep]])
                    state = self.state(temporary, extended[keep])
                    removal_scores.append(self.merit(state))
                removal_order = list(np.argsort(removal_scores)[:2]) + list(np.argsort(extended_allocation)[:1])
                for removal in dict.fromkeys(removal_order):
                    if removal == len(support):
                        continue
                    keep = np.arange(len(extended)) != removal
                    trial_support = extended[keep]
                    trial_allocation, trial_value = self.solve(trial_support, extended_allocation[keep], iterations=55)
                    if trial_value < value - 1e-6 and (best is None or trial_value < best[0]):
                        best = trial_value, trial_support, trial_allocation
                if time.monotonic() > self.deadline:
                    break
            if best is None:
                self.log("stationary", iteration=iteration, objective=value)
                break
            value, support, allocation = best
            self.consider(self.integerize(support, allocation), "support_exchange")
            self.log("exchange", iteration=iteration, objective=value)

    def run(self, start_name):
        start = np.array(json.loads((HERE / start_name).read_text())["batches"])
        self.consider(start, "private_portfolio_seed")
        self.consider(self.data.reference_counts, "champion")
        self.exchange(start, rounds=20)
        self.log("finished", passed=self.best[1]["passed"], core=self.best[1]["core_score"],
                 worst=self.best[1]["worst_family_score"], intact=self.best[1]["intact_mean_ratio"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=1050)
    parser.add_argument("--seed", type=int, default=891324)
    parser.add_argument("--start", default="champion_design.json")
    args = parser.parse_args()
    Search(args.seconds, args.seed).run(args.start)


if __name__ == "__main__":
    main()
