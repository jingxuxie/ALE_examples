import argparse
import json
from pathlib import Path

import numpy as np

from decision import DecisionProblem
from evaluate import validate_archive
from infer import SOURCE


def exact_scores(draws, estimate):
    kl = np.sum(draws * (np.log(np.maximum(draws, 1e-300)) - np.log(estimate)), axis=-1)
    tv = np.abs(draws - estimate).sum(axis=-1) / 2
    field = np.asarray([query % 12 >= 6 for query in range(48)])
    ratio = np.maximum.reduce([kl.mean(axis=-1) / .020,
                               kl[..., field].mean(axis=-1) / .035,
                               kl[..., ~field].mean(axis=-1) / .035,
                               tv.max(axis=-1) / .120])
    return ratio, kl, tv


def block_standard_error(values, chain_count, count, block_size=50):
    values = np.asarray(values).reshape(chain_count, count)
    usable = count - count % block_size
    blocks = values[:, :usable].reshape(-1, block_size).mean(axis=1)
    return float(blocks.std(ddof=1) / np.sqrt(len(blocks)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("validation_archive")
    parser.add_argument("candidate_archives", nargs="+")
    parser.add_argument("--training-mean", default="two_chain_predictions.npz")
    parser.add_argument("--output", default="predictions.npz")
    parser.add_argument("--summary", default="selection_summary.json")
    parser.add_argument("--audit-last", action="store_true")
    args = parser.parse_args()
    chains = np.load(args.validation_archive)["predictions"]
    validation_chains = chains[:-1] if args.audit_last else chains
    problem = DecisionProblem(validation_chains)
    posterior_mean = np.load(args.training_mean)["probabilities"]
    baseline = np.load(SOURCE / "baseline/predictions.npz")["probabilities"]
    candidates = [baseline, posterior_mean]
    names = ["frozen baseline", "training posterior mean"]
    for path in args.candidate_archives:
        values = np.load(path)["candidates"]
        for index, value in enumerate(values):
            for fraction in [0.5, 0.75, 1.0]:
                candidates.append(fraction * value + (1 - fraction) * posterior_mean)
                names.append(f"{Path(path).name}:{index}:weight={fraction}")
        if "optimized" in path:
            for checkpoint in range(6):
                average = values[checkpoint::6].mean(axis=0)
                candidates.append(average)
                names.append(f"{Path(path).name}:checkpoint_average={checkpoint}")
    candidates = np.asarray(candidates)
    candidates = np.maximum(candidates, 1e-300)
    candidates /= candidates.sum(axis=-1, keepdims=True)
    rows = []
    passes = []
    for index, candidate in enumerate(candidates):
        ratio, kl, tv = problem.scores(candidate)
        passed = ratio <= 1
        passes.append(passed)
        coverage = float(passed.mean())
        standard_error = block_standard_error(passed, *validation_chains.shape[:2])
        rows.append({"index": index, "name": names[index], "coverage": coverage,
                     "coverage_standard_error": standard_error, "expected_kl": float(kl.mean())})
        print(index, names[index], "coverage", coverage, "se", standard_error,
              "expected KL", kl.mean(), flush=True)
    passes = np.asarray(passes)
    best = int(np.argmax([row["coverage"] for row in rows]))
    eligible = []
    for index, row in enumerate(rows):
        paired_difference = passes[best].astype(float) - passes[index].astype(float)
        difference_error = block_standard_error(paired_difference, *validation_chains.shape[:2])
        if paired_difference.mean() <= difference_error + 0.0005:
            eligible.append(index)
    chosen = min(eligible, key=lambda index: rows[index]["expected_kl"])
    estimate = candidates[chosen]
    chosen_ratio, chosen_kl, chosen_tv = exact_scores(validation_chains, estimate)
    baseline_ratio, baseline_kl, baseline_tv = exact_scores(validation_chains, baseline)
    print("CHOSEN", chosen, names[chosen], "exact coverage", np.mean(chosen_ratio <= 1),
          "baseline exact coverage", np.mean(baseline_ratio <= 1), flush=True)
    audit = None
    if args.audit_last:
        audit_ratio, audit_kl, audit_tv = exact_scores(chains[-1:], estimate)
        audit_baseline_ratio, _, _ = exact_scores(chains[-1:], baseline)
        audit = {"chosen_coverage": float(np.mean(audit_ratio <= 1)),
                 "baseline_coverage": float(np.mean(audit_baseline_ratio <= 1)),
                 "chosen_expected_kl": float(audit_kl.mean())}
        print("Independent audit", audit, flush=True)
    queries = json.loads((SOURCE / "input/queries.json").read_text())
    np.savez(args.output, probabilities=np.ascontiguousarray(estimate, dtype="<f8"),
             query_ids=np.asarray([query["id"] for query in queries], dtype="<U24"))
    validate_archive(args.output, queries)
    summary = {"note": "These validation results use independent posterior simulations, not hidden ground truth.",
               "validation_draws": list(validation_chains.shape[:2]),
               "chosen": rows[chosen], "highest_coverage": rows[best], "eligible": eligible,
               "exact_chosen_coverage": float(np.mean(chosen_ratio <= 1)),
               "exact_baseline_coverage": float(np.mean(baseline_ratio <= 1)),
               "audit": audit, "candidates": rows}
    Path(args.summary).write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
