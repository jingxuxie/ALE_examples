import argparse
import hashlib
import importlib.util
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


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
from physics import FAMILIES, fisher_features, risks, sample_parameters


def capped_normalize(values, upper):
    values = np.maximum(values, 1e-30)
    if upper.sum() < 1 - 1e-10:
        return upper.copy()
    lower, higher = 0., 1.
    while np.minimum(values * higher, upper).sum() < 1:
        higher *= 2
    for iteration in range(90):
        middle = (lower + higher) / 2
        if np.minimum(values * middle, upper).sum() > 1:
            higher = middle
        else:
            lower = middle
    return np.minimum(values * ((lower + higher) / 2), upper)


class Search:
    def __init__(self, seed, seconds):
        self.started = time.monotonic()
        self.deadline = self.started + seconds
        self.rng = np.random.default_rng(seed)
        self.contract = json.loads((ROOT / "evaluator/hidden/contract.json").read_text())
        self.candidates = json.loads((ROOT / "participant/input/candidates.json").read_text())
        with np.load(ROOT / "evaluator/hidden/benchmark.npz", allow_pickle=False) as data:
            self.features = data["features"].copy()
            self.families = data["families"].copy()
            self.costs = data["costs"].copy()
            self.baseline_risks = data["baseline_risks"].copy()
        self.baseline = np.array(json.loads((ROOT / "participant/baseline/design.json").read_text())["batches"])
        self.budget = self.contract["execution_budget_ticks"]
        self.setup = self.contract["setup_ticks"]
        self.support_limit = self.contract["max_distinct_circuits"]
        self.limit = self.contract["max_batches_per_circuit"]
        self.available = self.budget - self.support_limit * self.setup
        self.upper = self.limit * self.costs / self.available
        self.scaled = self.features * np.sqrt(64 * self.available / self.costs)[None, :, None]
        self.family_names = list(FAMILIES)
        self.family_masks = np.array([self.families == family for family in self.family_names])
        self.family_norm = np.array([self.baseline_risks[mask].mean() for mask in self.family_masks])
        self.weights = np.ones(len(self.features)) / len(self.features) / self.baseline_risks.mean()
        self.best_key = np.inf
        self.best_counts = self.baseline.copy()
        self.best_result = None
        self.evaluations = 0
        spec = importlib.util.spec_from_file_location("private_frozen_evaluator", ROOT / "evaluator/evaluate.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.evaluate = module.evaluate
        self.log("configuration", seed=seed, seconds=seconds, scenario_count=len(self.features),
                 candidate_count=len(self.costs), target_core=0.5, target_worst_family=0.4,
                 privileged=True, fresh_artifacts_read=False)

    def log(self, event, **values):
        value = dict(elapsed_seconds=time.monotonic() - self.started, event=event, **values)
        with (HERE / "search.jsonl").open("a") as stream:
            stream.write(json.dumps(value, allow_nan=False) + "\n")
        print(json.dumps(value, allow_nan=False), flush=True)

    def information(self, support, allocation):
        features = self.scaled[:, support]
        information = features.transpose(0, 2, 1) @ (features * allocation[None, :, None])
        information += np.eye(14)[None] * 1e-10
        covariance = np.linalg.inv(information)
        risk = np.trace(covariance[:, :12, :12], axis1=1, axis2=2)
        return features, covariance, risk

    def objective(self, allocation, support):
        features, covariance, risk = self.information(support, allocation)
        projection = features @ covariance[:, :, :12]
        derivatives = -np.sum(projection * projection, axis=2)
        return float(self.weights @ risk), self.weights @ derivatives

    def solve(self, support, allocation=None, iterations=100):
        support = np.array(support, dtype=int)
        upper = self.upper[support]
        if allocation is None:
            allocation = capped_normalize(np.ones(len(support)), upper)
        else:
            allocation = capped_normalize(allocation, upper)
        result = minimize(self.objective, allocation, args=(support,), jac=True, method="SLSQP",
                          bounds=list(zip(np.zeros(len(support)), upper)),
                          constraints=[{"type": "ineq", "fun": lambda value: 1. - value.sum(),
                                        "jac": lambda value: -np.ones(len(value))}],
                          options={"maxiter": iterations, "ftol": 2e-9, "disp": False})
        allocation = np.clip(result.x, 0, upper)
        if allocation.sum() > 1:
            allocation /= allocation.sum()
        return allocation, float(self.objective(allocation, support)[0])

    def scores(self, counts, features=None, baseline=None, families=None):
        if features is None:
            features, baseline, families = self.features, self.baseline_risks, self.families
        candidate = risks(features, counts)
        core_ratio = candidate.mean() / baseline.mean()
        family_ratios = {str(family): float(candidate[families == family].mean() /
                                          baseline[families == family].mean())
                         for family in np.unique(families)}
        target_factor = max(core_ratio / 0.5, max(family_ratios.values()) / 0.6)
        return float(target_factor), float(core_ratio), family_ratios

    def integerize(self, support, allocation, refine=True):
        counts = np.zeros(len(self.costs), dtype=np.int64)
        counts[support] = np.minimum(self.limit, np.floor(allocation * self.available / self.costs[support])).astype(int)
        remaining = self.budget - counts @ self.costs - np.count_nonzero(counts) * self.setup
        features = self.features[:, support]
        while True:
            selected_counts = counts[support]
            price = self.costs[support] + (selected_counts == 0) * self.setup
            legal = (selected_counts < self.limit) & (price <= remaining)
            if not np.any(legal):
                break
            information = features.transpose(0, 2, 1) @ (features * (selected_counts * 64)[None, :, None])
            covariance = np.linalg.inv(information + np.eye(14)[None] * 1e-10)
            leverage = np.sum((features @ covariance) * features, axis=2) * 64
            projection = features @ covariance[:, :, :12]
            gains = (self.weights @ (64 * np.sum(projection * projection, axis=2) / (1 + leverage))) / price
            gains[~legal] = -np.inf
            local = int(np.argmax(gains))
            counts[support[local]] += 1
            remaining -= int(price[local])
        if refine:
            counts = self.integer_exchange(counts, rounds=15)
        return counts

    def integer_exchange(self, counts, rounds=15):
        support = np.flatnonzero(counts)
        features = self.features[:, support] * 8
        for iteration in range(rounds):
            information = features.transpose(0, 2, 1) @ (features * counts[support][None, :, None])
            covariance = np.linalg.inv(information + np.eye(14)[None] * 1e-10)
            score = float(self.weights @ np.trace(covariance[:, :12, :12], axis1=1, axis2=2))
            remaining = self.budget - counts @ self.costs - len(support) * self.setup
            best_score, best_pair = score, None
            for remove_local, remove_global in enumerate(support):
                if counts[remove_global] <= 1:
                    continue
                column = covariance @ features[:, remove_local, :, None]
                denominator = 1 - (features[:, remove_local, None, :] @ column).ravel()
                if denominator.min() <= 1e-8:
                    continue
                removed_cov = covariance + (column @ column.transpose(0, 2, 1)) / denominator[:, None, None]
                removed_risk = np.trace(removed_cov[:, :12, :12], axis1=1, axis2=2)
                projection = features @ removed_cov
                leverage = np.sum(projection * features, axis=2)
                gain = np.sum(projection[:, :, :12] ** 2, axis=2) / (1 + leverage)
                scores = self.weights @ (removed_risk[:, None] - gain)
                legal = (counts[support] < self.limit) & (self.costs[support] <= remaining + self.costs[remove_global])
                legal[remove_local] = False
                scores[~legal] = np.inf
                add_local = int(np.argmin(scores))
                if scores[add_local] < best_score - 1e-10:
                    best_score = float(scores[add_local])
                    best_pair = (remove_global, support[add_local])
            if best_pair is None:
                break
            counts[best_pair[0]] -= 1
            counts[best_pair[1]] += 1
        return counts

    def consider(self, counts, label):
        self.evaluations += 1
        factor, core_ratio, family_ratios = self.scores(counts)
        key = factor + 1e-5 * core_ratio
        if key < self.best_key:
            destination = HERE / "design.json"
            destination.write_text(json.dumps({"batches": counts.tolist()}) + "\n")
            result = self.evaluate(destination)
            if not result["valid"]:
                raise RuntimeError(result)
            self.best_counts = counts.copy()
            self.best_key = key
            self.best_result = result
            (HERE / "evaluator_score.json").write_text(json.dumps(result, indent=2) + "\n")
            self.log("new_best", label=label, target_factor=factor, result=result,
                     support=[int(index) for index in np.flatnonzero(counts)],
                     allocation={str(index): int(counts[index]) for index in np.flatnonzero(counts)})
        return factor

    def relax(self, iterations=500):
        support = np.arange(len(self.costs))
        allocation = capped_normalize(np.ones(len(support)), self.upper)
        previous = np.inf
        for iteration in range(iterations):
            value, gradient = self.objective(allocation, support)
            if iteration % 50 == 0:
                self.log("relaxation", iteration=iteration, weighted_ratio=value, allocation_sum=float(allocation.sum()),
                         effective_support=float(1 / np.sum(allocation ** 2)))
            updated = capped_normalize(allocation * np.sqrt(np.maximum(-gradient, 1e-30)), self.upper)
            if np.abs(previous - value) < 1e-9 or time.monotonic() > self.deadline:
                break
            allocation, previous = updated, value
        np.savez_compressed(HERE / "relaxation.npz", allocation=allocation, objective=value)
        return allocation

    def prune(self, relaxation, size=65):
        support = np.argsort(relaxation)[-size:]
        allocation, value = self.solve(support, relaxation[support], iterations=140)
        while len(support) > self.support_limit and time.monotonic() < self.deadline:
            features, covariance, risk = self.information(support, allocation)
            projection = features @ covariance
            leverage = np.sum(projection * features, axis=2)
            numerator = np.sum(projection[:, :, :12] ** 2, axis=2) * allocation[None]
            denominator = 1 - allocation[None] * leverage
            removal_losses = self.weights @ (numerator / np.maximum(denominator, 1e-14))
            invalid = np.any(denominator <= 1e-10, axis=0)
            removal_losses[invalid] = np.inf
            infeasible = self.upper[support].sum() - self.upper[support] < 1 - 1e-10
            removal_losses[infeasible] = np.inf
            remove = int(np.argmin(removal_losses))
            keep = np.arange(len(support)) != remove
            support, allocation = support[keep], allocation[keep]
            allocation, value = self.solve(support, allocation)
            if len(support) % 5 == 0 or len(support) == self.support_limit:
                self.log("pruning", circuits=len(support), weighted_ratio=value)
        return support, allocation

    def exchange(self, counts, rounds=30, width=16):
        support = np.flatnonzero(counts)
        allocation, value = self.solve(support, counts[support] * self.costs[support] / self.available)
        self.consider(self.integerize(support, allocation), "exchange_initial")
        for iteration in range(rounds):
            if time.monotonic() > self.deadline:
                break
            features, covariance, risk = self.information(support, allocation)
            projected = self.scaled @ covariance[:, :, :12]
            addition_scores = self.weights @ np.sum(projected * projected, axis=2)
            addition_scores[support] = -np.inf
            additions = np.argsort(addition_scores)[-width:][::-1]
            current_projection = features @ covariance
            leverage = np.sum(current_projection * features, axis=2)
            denominator = 1 - allocation[None] * leverage
            numerator = allocation[None] * np.sum(current_projection[:, :, :12] ** 2, axis=2)
            removal_loss = self.weights @ (numerator / np.maximum(denominator, 1e-12))
            remove_order = np.argsort(removal_loss)
            best = None
            for addition in additions:
                extended = np.append(support, addition)
                extended_allocation, extended_value = self.solve(extended, np.append(allocation * 0.97, 0.03), iterations=65)
                if len(support) < self.support_limit and extended_value < value - 2e-6:
                    if best is None or extended_value < best[0]:
                        best = extended_value, extended, extended_allocation
                drop_options = list(np.argsort(extended_allocation / np.maximum(self.upper[extended], 1e-12))[:3])
                drop_options += list(remove_order[:2])
                for removal in dict.fromkeys(drop_options):
                    if removal == len(support):
                        continue
                    keep = np.arange(len(extended)) != removal
                    trial_support = extended[keep]
                    trial_allocation, trial_value = self.solve(trial_support, extended_allocation[keep], iterations=65)
                    if trial_value < value - 2e-6 and (best is None or trial_value < best[0]):
                        best = trial_value, trial_support, trial_allocation
                if time.monotonic() > self.deadline:
                    break
            if best is None:
                self.log("exchange_stationary", iteration=iteration, weighted_ratio=value)
                break
            value, support, allocation = best
            trial_counts = self.integerize(support, allocation)
            self.consider(trial_counts, "support_exchange")
            self.log("exchange", iteration=iteration, weighted_ratio=value,
                     target_factor=self.scores(trial_counts)[0])
        return self.integerize(support, allocation)

    def broad_audit(self, per_family):
        rng = np.random.default_rng(982734005)
        supports = np.union1d(np.flatnonzero(self.baseline), np.flatnonzero(self.best_counts))
        candidates = [self.candidates[index] for index in supports]
        feature_rows, parameters, families = [], [], []
        for family in FAMILIES:
            for iteration in range(per_family):
                parameter = sample_parameters(rng, family)
                feature_rows.append(fisher_features(parameter, candidates))
                parameters.append(parameter)
                families.append(family)
            self.log("broad_audit_progress", family=family, per_family=per_family)
        features, families = np.array(feature_rows), np.array(families)
        baseline = risks(features, self.baseline[supports])
        candidate = risks(features, self.best_counts[supports])
        family_scores = {family: float(1 - candidate[families == family].mean() /
                                      baseline[families == family].mean()) for family in FAMILIES}
        ratios = candidate / baseline
        result = dict(independent_seed=982734005, scenarios=len(families), per_family=per_family,
                      mean_baseline_risk=float(baseline.mean()), mean_candidate_risk=float(candidate.mean()),
                      core_score=float(1 - candidate.mean() / baseline.mean()),
                      family_scores=family_scores, worst_family_score=min(family_scores.values()),
                      fraction_scenarios_improved=float(np.mean(ratios < 1)),
                      risk_ratio_quantiles={str(quantile): float(np.quantile(ratios, quantile))
                                            for quantile in [0., 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.]},
                      selected_using_this_audit=False,
                      design_sha256=hashlib.sha256((HERE / "design.json").read_bytes()).hexdigest())
        bootstrap_rng = np.random.default_rng(7744001)
        bootstrap_baseline = []
        bootstrap_candidate = []
        family_intervals = {}
        for family in FAMILIES:
            mask = families == family
            resampled = bootstrap_rng.integers(per_family, size=(2000, per_family))
            baseline_means = baseline[mask][resampled].mean(axis=1)
            candidate_means = candidate[mask][resampled].mean(axis=1)
            bootstrap_baseline.append(baseline_means)
            bootstrap_candidate.append(candidate_means)
            family_intervals[family] = np.quantile(1 - candidate_means / baseline_means, [0.025, 0.975]).tolist()
        bootstrap_scores = 1 - np.mean(bootstrap_candidate, axis=0) / np.mean(bootstrap_baseline, axis=0)
        result["paired_stratified_bootstrap_core_95_interval"] = np.quantile(bootstrap_scores, [0.025, 0.975]).tolist()
        result["paired_bootstrap_family_95_intervals"] = family_intervals
        result["worst_individual_cases"] = [dict(family=str(families[index]),
                                                 candidate_risk=float(candidate[index]),
                                                 baseline_risk=float(baseline[index]),
                                                 ratio=float(ratios[index]),
                                                 parameters=parameters[index].tolist())
                                            for index in np.argsort(ratios)[-10:][::-1]]
        result["passed_same_population_targets"] = result["core_score"] >= 0.5 and result["worst_family_score"] >= 0.4
        (HERE / "broad_space_score.json").write_text(json.dumps(result, indent=2) + "\n")
        np.savez_compressed(HERE / "broad_space.npz", parameters=parameters, families=families,
                            baseline_risks=baseline, candidate_risks=candidate, support=supports)
        self.log("broad_audit_complete", result=result)

    def run(self, audit_per_family):
        previous = HERE / "design.json"
        warm_start = np.array(json.loads(previous.read_text())["batches"]) if previous.exists() else None
        self.consider(self.baseline, "nominal_baseline")
        if warm_start is not None:
            self.consider(warm_start, "prior_private_search")
        support = np.flatnonzero(self.baseline)
        allocation, value = self.solve(support, self.baseline[support] * self.costs[support] / self.available)
        self.consider(self.integerize(support, allocation), "baseline_support_A_optimal")
        relaxed = self.relax()
        support, allocation = self.prune(relaxed)
        if len(support) <= self.support_limit:
            self.consider(self.integerize(support, allocation), "pruned_relaxation")
        self.exchange(self.best_counts.copy(), rounds=35, width=12)
        generation = 0
        while time.monotonic() < self.deadline - 45:
            generation += 1
            factor, core_ratio, family_ratios = self.scores(self.best_counts)
            worst = max(family_ratios, key=family_ratios.get)
            if generation % 3 == 1:
                weights = np.ones(len(self.features)) / len(self.features) / self.baseline_risks.mean()
                weights += 0.8 * (self.families == worst) / np.sum(self.families == worst) / self.family_norm[self.family_names.index(worst)]
                self.weights = weights
            elif generation % 3 == 2:
                family_weights = self.rng.dirichlet(np.ones(6) * 5)
                self.weights = np.zeros(len(self.features))
                for family_index, mask in enumerate(self.family_masks):
                    self.weights[mask] = family_weights[family_index] / np.sum(mask) / self.family_norm[family_index]
            else:
                self.weights = np.ones(len(self.features)) / len(self.features) / self.baseline_risks.mean()
            self.log("portfolio_restart", generation=generation, worst_family=worst,
                     target_factor=factor, weights=self.weights.tolist())
            if generation % 2:
                counts = self.best_counts.copy()
            else:
                perturbed = relaxed * np.exp(self.rng.normal(0, 0.55, len(relaxed)))
                support, allocation = self.prune(perturbed, size=45)
                if len(support) > self.support_limit:
                    break
                counts = self.integerize(support, allocation)
                self.consider(counts, "portfolio_prune")
            self.exchange(counts, rounds=10, width=8)
        self.log("search_complete", evaluated_designs=self.evaluations, result=self.best_result)
        self.finish(audit_per_family)

    def finish(self, audit_per_family):
        (HERE / "design.json").write_text(json.dumps({"batches": self.best_counts.tolist()}) + "\n")
        self.best_result = self.evaluate(HERE / "design.json")
        (HERE / "evaluator_score.json").write_text(json.dumps(self.best_result, indent=2) + "\n")
        if audit_per_family:
            self.broad_audit(audit_per_family)
        result = {"privileged_solution": True, "fresh_attempt": False,
                  "solvability_demonstrated": self.best_result["passed"],
                  "frozen_evaluator_result": self.best_result,
                  "current_invocation_wall_seconds": time.monotonic() - self.started,
                  "current_invocation_evaluated_integer_designs": self.evaluations,
                  "methods": ["fixed-support SLSQP A-optimal allocation", "capped multiplicative continuous relaxation",
                              "backward sparse pruning", "support add/drop exchanges", "integer shot exchanges",
                              "worst-family and randomized-weight portfolio"],
                  "targets_modified": False, "fresh_submissions_read": False}
        (HERE / "summary.json").write_text(json.dumps(result, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=1000)
    parser.add_argument("--seed", type=int, default=340190)
    parser.add_argument("--audit-per-family", type=int, default=100)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    search = Search(args.seed, args.seconds)
    if args.audit_only:
        counts = np.array(json.loads((HERE / "design.json").read_text())["batches"])
        search.consider(counts, "frozen_private_design_audit_only")
        search.finish(args.audit_per_family)
    else:
        search.run(args.audit_per_family)


if __name__ == "__main__":
    main()
