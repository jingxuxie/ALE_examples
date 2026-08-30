import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REFERENCE = HERE.parent / "design.json"
TARGETS = {"single_core_reduction": 0.25, "single_family_reduction": 0.15,
           "double_core_reduction": 0.50, "double_family_reduction": 0.30,
           "intact_mean_ratio_limit": 1.20}


def covariance(rows, allocation):
    information = rows.transpose(0, 2, 1) @ (rows * allocation[None, :, None])
    information += np.eye(14)[None] * 1e-10
    inverse = np.linalg.inv(information)
    risk = np.trace(inverse[:, :12, :12], axis1=1, axis2=2)
    if not np.all(np.isfinite(risk)) or np.any(risk <= 0):
        raise ValueError("nonpositive or nonfinite covariance risk")
    return information, inverse, risk


def loss_table(rows, allocation, order, state=None):
    information, inverse, intact = covariance(rows, allocation) if state is None else state
    leverage = (rows @ inverse) @ rows.transpose(0, 2, 1)
    projected = rows @ inverse[:, :, :12]
    target_gram = projected @ projected.transpose(0, 2, 1)
    diagonal = np.diagonal(leverage, axis1=1, axis2=2)
    target_diagonal = np.diagonal(target_gram, axis1=1, axis2=2)
    residual = 1 - allocation[None] * diagonal
    if order == 1:
        cases = np.arange(len(allocation))[:, None]
        table = intact[:, None] + allocation[None] * target_diagonal / np.maximum(residual, 1e-14)
    else:
        first, second = np.triu_indices(len(allocation), 1)
        cases = np.stack([first, second], axis=1)
        product = allocation[first] * allocation[second]
        cross = leverage[:, first, second]
        determinant = residual[:, first] * residual[:, second] - product[None] * cross ** 2
        numerator = (residual[:, second] * allocation[None, first] * target_diagonal[:, first] +
                     residual[:, first] * allocation[None, second] * target_diagonal[:, second] +
                     2 * product[None] * cross * target_gram[:, first, second])
        table = intact[:, None] + numerator / np.maximum(determinant, 1e-14)
    return table, cases, (information, inverse, intact)


def profile(features, counts, direct=False):
    support = np.flatnonzero(counts)
    rows = features[:, support] * 8
    allocation = counts[support].astype(float)
    state = covariance(rows, allocation)
    result = {"intact": state[2], "support": support}
    for order, label in [(1, "single"), (2, "double")]:
        table, cases, state = loss_table(rows, allocation, order, state)
        if direct:
            exact = []
            for case in cases:
                reduced = allocation.copy()
                reduced[case] = 0
                exact.append(covariance(rows, reduced)[2])
            table = np.array(exact).T
        worst = np.argmax(table, axis=1)
        result[label] = table[np.arange(len(features)), worst]
        result[label + "_worst_circuits"] = support[cases[worst]]
    return result


def score_profiles(candidate, reference, families):
    intact_ratio = float(candidate["intact"].mean() / reference["intact"].mean())
    value = {"intact_mean_risk": float(candidate["intact"].mean()),
             "reference_intact_mean_risk": float(reference["intact"].mean()),
             "intact_mean_ratio": intact_ratio,
             "intact_guard_passed": intact_ratio <= TARGETS["intact_mean_ratio_limit"] + 1e-12}
    for label in ["single", "double"]:
        families_value = {}
        for family in np.unique(families):
            mask = families == family
            families_value[str(family)] = {"candidate_mean_risk": float(candidate[label][mask].mean()),
                                           "reference_mean_risk": float(reference[label][mask].mean()),
                                           "reduction": float(1 - candidate[label][mask].mean() / reference[label][mask].mean())}
        score = float(1 - candidate[label].mean() / reference[label].mean())
        worst_family = min(entry["reduction"] for entry in families_value.values())
        value[label] = {"core_score": score, "worst_family_score": worst_family,
                        "mean_risk": float(candidate[label].mean()),
                        "reference_mean_risk": float(reference[label].mean()),
                        "family_scores": families_value,
                        "passed": value["intact_guard_passed"] and score >= TARGETS[label + "_core_reduction"] and
                                  worst_family >= TARGETS[label + "_family_reduction"]}
    return value


class Benchmark:
    def __init__(self):
        frozen_path = HERE / "contract.json"
        if frozen_path.exists():
            frozen = json.loads(frozen_path.read_text())
            if frozen["targets"] != TARGETS or frozen["reference_design_sha256"] != hashlib.sha256(REFERENCE.read_bytes()).hexdigest():
                raise ValueError("frozen resilience targets or original reference changed")
        self.contract = json.loads((ROOT / "participant/input/contract.json").read_text())
        self.candidates = json.loads((ROOT / "participant/input/candidates.json").read_text())
        self.reference_counts = np.array(json.loads(REFERENCE.read_text())["batches"])
        with np.load(ROOT / "evaluator/hidden/benchmark.npz", allow_pickle=False) as data:
            self.features = data["features"].copy()
            self.families = data["families"].copy()
            self.parameters = data["parameters"].copy()
            self.costs = data["costs"].copy()
        self.reference = profile(self.features, self.reference_counts, direct=True)

    def validate(self, counts):
        if len(counts) != len(self.costs) or np.any(counts < 0) or np.any(counts > self.contract["max_batches_per_circuit"]):
            raise ValueError("batch-vector bounds violated")
        if np.any(counts != np.floor(counts)):
            raise ValueError("batch vector must be integral")
        active = int(np.count_nonzero(counts))
        if not 3 <= active <= self.contract["max_distinct_circuits"]:
            raise ValueError("support limit violated")
        cost = int(counts @ self.costs + active * self.contract["setup_ticks"])
        if cost > self.contract["execution_budget_ticks"]:
            raise ValueError("execution budget exceeded")
        return cost, active

    def evaluate(self, counts, direct=True):
        cost, active = self.validate(counts)
        candidate = profile(self.features, counts, direct=direct)
        result = score_profiles(candidate, self.reference, self.families)
        result.update(valid=True, execution_ticks=cost, distinct_circuits=active,
                      total_batches=int(counts.sum()), targets=TARGETS,
                      reference_design_sha256=hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
                      worst_loss_taken_separately_at_each_operating_point=True,
                      every_loss_directly_inverted=direct)
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    data = json.loads(Path(args.submission).read_text())
    if not isinstance(data, dict) or set(data) != {"batches"} or any(type(value) is not int for value in data["batches"]):
        raise ValueError("expected exactly one integral batches vector")
    result = Benchmark().evaluate(np.array(data["batches"]), direct=True)
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        Path(args.output).write_text(encoded)
    print(encoded)


if __name__ == "__main__":
    main()
