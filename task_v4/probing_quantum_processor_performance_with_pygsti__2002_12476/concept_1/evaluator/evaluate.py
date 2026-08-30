import argparse
import itertools
import json
from pathlib import Path
import stat
import time

import numpy as np


def strict_pairs(pairs):
    document = {}
    for key, value in pairs:
        if key in document:
            raise ValueError("duplicate JSON key")
        document[key] = value
    return document


def reject_constant(value):
    raise ValueError("nonfinite JSON constant")


def risk_profile(features, batches, removed, shots):
    support = np.flatnonzero(batches)
    counts = batches[support] * shots
    cases = list(itertools.combinations(range(len(support)), min(removed, len(support))))
    loss_counts = np.tile(counts, (len(cases), 1))
    for index, case in enumerate(cases):
        loss_counts[index, list(case)] = 0
    intact_risks = []
    loss_risks = []
    worst_pairs = []
    for model_features in features:
        rows = model_features[support]
        all_counts = np.concatenate([counts[None], loss_counts], axis=0)
        information = np.einsum("ci,kc,cj->kij", rows, all_counts, rows, optimize=True)
        information += np.eye(14)[None] * 1e-10
        if np.any(np.linalg.eigvalsh(information)[:, 0] <= 0):
            raise ValueError("numerically nonpositive information")
        covariance = np.linalg.inv(information)
        risks = np.trace(covariance[:, :12, :12], axis1=1, axis2=2)
        if not np.all(np.isfinite(risks)) or np.any(risks <= 0):
            raise ValueError("nonpositive or nonfinite information risk")
        worst = int(np.argmax(risks[1:]))
        intact_risks.append(float(risks[0]))
        loss_risks.append(float(risks[1 + worst]))
        worst_pairs.append(support[list(cases[worst])].tolist())
    return np.array(intact_risks), np.array(loss_risks), worst_pairs


def evaluate(submission):
    started = time.monotonic()
    root = Path(__file__).resolve().parent
    result = dict(core_score=0., worst_family_score=0., runtime_seconds=0., resource_score=0.,
                  passed=False, valid=False, reason="")
    try:
        path = Path(submission)
        if path.is_symlink():
            raise ValueError("submission symlinks are forbidden")
        if path.is_dir():
            path = path / "design.json"
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError("submission must be a regular JSON file")
        if path.stat().st_size > 100000:
            raise ValueError("submission exceeds 100 KB")
        with path.open("rb") as handle:
            payload = handle.read(100001)
        if len(payload) > 100000:
            raise ValueError("submission exceeds 100 KB")
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=strict_pairs,
                           parse_constant=reject_constant)
        if not isinstance(value, dict) or set(value) != {"batches"}:
            raise ValueError("expected exactly the batches field")
        data = np.load(root / "hidden/benchmark.npz", allow_pickle=False)
        contract = json.loads((root / "hidden/contract.json").read_text())
        entries = value["batches"]
        if not isinstance(entries, list) or len(entries) != len(data["costs"]):
            raise ValueError("wrong batch-vector length")
        if any(type(entry) is not int or not 0 <= entry <= contract["max_batches_per_circuit"] for entry in entries):
            raise ValueError("batch counts must be bounded nonnegative integers")
        batches = np.array(entries, dtype=np.int64)
        active = int(np.count_nonzero(batches))
        cost = int(batches @ data["costs"] + active * contract["setup_ticks"])
        if not 1 <= active <= contract["max_distinct_circuits"]:
            raise ValueError("distinct-circuit limit violated")
        if cost > contract["execution_budget_ticks"]:
            raise ValueError("execution budget exceeded")
        intact, loss, worst_pairs = risk_profile(data["features"], batches,
                                                contract["lost_circuits"], contract["shots_per_batch"])
        family_scores = {}
        family_risks = {}
        for family in np.unique(data["families"]):
            mask = data["families"] == family
            family_scores[str(family)] = float(data["champion_intact_risks"][mask].mean() / loss[mask].mean())
            family_risks[str(family)] = float(loss[mask].mean())
        ratio = float(intact.mean() / data["champion_intact_risks"].mean())
        result.update(valid=True, core_score=float(data["champion_intact_risks"].mean() / loss.mean()),
                      loss_risk_reduction=float(1 - loss.mean() / data["champion_loss_risks"].mean()),
                      loss_to_champion_intact_ratio=float(loss.mean() / data["champion_intact_risks"].mean()),
                      worst_family_score=min(family_scores.values()), family_scores=family_scores,
                      mean_loss_risk=float(loss.mean()), family_loss_risks=family_risks,
                      mean_intact_risk=float(intact.mean()), intact_mean_ratio=ratio,
                      intact_guard_passed=ratio <= contract["intact_mean_ratio_limit"],
                      execution_ticks=cost, distinct_circuits=active,
                      resource_score=float(1 - cost / contract["execution_budget_ticks"]),
                      worst_lost_circuits_per_model=worst_pairs)
        result["passed"] = (result["core_score"] >= contract["target_core_score"] and
                            result["worst_family_score"] >= contract["target_worst_family_score"] and
                            result["intact_guard_passed"])
        reasons = []
        if result["core_score"] < contract["target_core_score"]:
            reasons.append("overall fourfold loss-risk budget exceeded")
        if result["worst_family_score"] < contract["target_worst_family_score"]:
            reasons.append("a regime exceeds its fivefold loss-risk budget")
        if not result["intact_guard_passed"]:
            reasons.append("intact-design efficiency guard violated")
        result["reason"] = "; ".join(reasons) if reasons else "all frozen resilience targets met"
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError, np.linalg.LinAlgError) as error:
        result["reason"] = str(error)
    result["runtime_seconds"] = time.monotonic() - started
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = evaluate(args.submission)
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(encoded)
    print(encoded, end="")


if __name__ == "__main__":
    main()
