import argparse
import json
import math
import os
import sys
from collections import Counter

import numpy as np

from build_batch import CONCEPT, OWNED, immutable_manifest, require, sha256, write_json


sys.path.insert(0, str(CONCEPT / "attempts/v_1"))
from acquisition import UNKNOWN, acquire, prior
from experiment import MASKS, ORDERS, SUBSETS, transform
from solution import FAMILIES, predict_prior


def signed_sum(values):
    return math.fsum(float(value) for value in values)


def analyze_case(model, table, diagnostic, record):
    energy = np.zeros(256)
    energy[ORDERS <= 3] = table[ORDERS <= 3]
    low_terms = transform(energy)
    low_terms[ORDERS >= 4] = 0
    family = FAMILIES.index(model["family"])
    mean = predict_prior(energy, np.asarray(model["orbital_energy"]), family)
    covariance = prior(low_terms, fifth_weight=2)
    queries, _, cost = acquire(low_terms, covariance, mean=mean, budget=104, power=0.8, return_queries=True, quints=0)
    require(bool(np.all(ORDERS[queries] == 4)), "champion acquisition no longer selects only quadruples")
    require(len(queries) + 56 == record["queries"] and cost + 56 == record["cost"], "replayed query counts disagree with actual record")
    design = SUBSETS[queries][:, UNKNOWN].astype(float)
    kernel = design @ covariance @ design.T
    weights = np.linalg.solve(kernel + np.eye(len(queries)) * 1e-20, design @ covariance @ np.ones(len(UNKNOWN)))
    measured = table[queries] - SUBSETS[queries] @ low_terms
    innovations = measured - design @ mean[UNKNOWN]
    fallback_tail = float(mean[UNKNOWN].sum() + weights @ innovations)
    uncertainty = float(np.sqrt(max(0, covariance.sum() - weights @ (design @ covariance @ np.ones(len(UNKNOWN))))))
    true_terms = transform(table)
    added_mask = 1 << diagnostic.get("active_added_virtual_index", 7)
    old_unknown = UNKNOWN[(UNKNOWN & added_mask) == 0]
    new_unknown = UNKNOWN[(UNKNOWN & added_mask) != 0]
    old_queries = (queries & added_mask) == 0
    old_fallback = float(mean[old_unknown].sum() + weights[old_queries] @ innovations[old_queries])
    new_fallback = fallback_tail - old_fallback
    old_truth = signed_sum(true_terms[old_unknown])
    new_truth = signed_sum(true_terms[new_unknown])
    low_sum = float(low_terms.sum())
    correction = float(record["estimate"] - low_sum - fallback_tail)
    old_error = old_fallback - old_truth
    new_error = new_fallback - new_truth
    require(abs(old_error + new_error + correction - record["error"]) < 1e-11, "signed error attribution does not close")
    old_indicator = ((UNKNOWN & added_mask) == 0).astype(float)
    old_covariance = design @ covariance @ old_indicator
    old_variance = float(old_indicator @ covariance @ old_indicator)
    posterior_old_variance = max(0, old_variance - old_covariance @ np.linalg.solve(kernel + np.eye(len(queries)) * 1e-20, old_covariance))
    unqueried_old = [int(mask) for mask in old_unknown if mask not in queries]
    quadruple_order = sorted(MASKS[4], key=lambda mask: abs(true_terms[mask]), reverse=True)
    decomposition = []
    for order in range(4, 9):
        old_masks = [mask for mask in old_unknown if int(mask).bit_count() == order]
        new_masks = [mask for mask in new_unknown if int(mask).bit_count() == order]
        decomposition.append({
            "order": order,
            "old_true_signed_eh": signed_sum(true_terms[old_masks]),
            "old_true_absolute_eh": signed_sum(abs(true_terms[old_masks])),
            "new_true_signed_eh": signed_sum(true_terms[new_masks]),
            "new_true_absolute_eh": signed_sum(abs(true_terms[new_masks])),
            "old_neural_mean_eh": signed_sum(mean[old_masks]),
            "new_neural_mean_eh": signed_sum(mean[new_masks]),
        })
    return {
        "index": record["index"], "seed_witness": diagnostic["seed_witness"],
        "active_added_virtual_index": diagnostic.get("active_added_virtual_index", 7),
        "actual_error_eh": record["error"], "actual_estimate_eh": record["estimate"],
        "truth_eh": record["truth"], "mbe3_eh": low_sum,
        "actual_estimated_tail_eh": float(record["estimate"] - low_sum),
        "true_tail_eh": old_truth + new_truth, "fallback_tail_eh": fallback_tail,
        "old_tail_true_eh": old_truth, "new_tail_true_eh": new_truth,
        "old_tail_fallback_eh": old_fallback, "new_tail_fallback_eh": new_fallback,
        "old_fallback_error_eh": old_error, "new_fallback_error_eh": new_error,
        "actual_minus_fallback_eh": correction,
        "uncertainty_eh": uncertainty,
        "physical_fit_skipped_by_uncertainty_gate": uncertainty < 4e-6,
        "physical_fit_attribution_note": "Actual-minus-fallback detects net correction, not whether a fit was attempted; timer-based skipping is not observable in evaluator records.",
        "prior_old_tail_standard_deviation_eh": math.sqrt(old_variance),
        "posterior_old_tail_standard_deviation_eh": math.sqrt(posterior_old_variance),
        "deterministically_replayed_quadruple_masks": queries.tolist(),
        "quadruple_masks_source": "unchanged acquisition functions replayed from observed <=3 CAS values; official evaluator records counts, not masks; acquisition has no timer dependence",
        "queried_old_quadruples": int(sum(old_queries)),
        "queried_new_quadruples": int(sum(~old_queries)),
        "unqueried_old_tail_signed_eh": signed_sum(true_terms[unqueried_old]),
        "query_weights_max_deviation_from_one": float(np.max(np.abs(weights - 1))),
        "largest_absolute_quadruples": [
            {"mask": int(mask), "new_virtual": bool(mask & added_mask), "increment_eh": float(true_terms[mask]), "queried": bool(mask in queries)}
            for mask in quadruple_order[:12]
        ],
        "signed_order_decomposition": decomposition,
    }


def rmse(values):
    return math.sqrt(math.fsum(float(value) ** 2 for value in values) / len(values))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, choices=(1, 2), default=1)
    arguments = parser.parse_args()
    os.umask(0o077)
    batch = OWNED / f"batch_{arguments.batch:02d}"
    official = json.loads((batch / "score.json").read_text())
    score_path = batch / "score.json"
    score = official
    if not official.get("valid"):
        score_path = batch / "score_wall600_diagnostic.json"
        score = json.loads(score_path.read_text())
        require(score.get("diagnostic_only") and score.get("same_cpu_query_memory_limits_satisfied"), "diagnostic replay lacks unchanged CPU/query/memory validity")
    require(score.get("valid") and len(score["records"]) == 120, "no complete valid scientific replay")
    models = json.loads((batch / "models.json").read_text())
    tables = np.load(batch / "cases.npz", allow_pickle=False)["energies"]
    diagnostics = json.loads((batch / "diagnostics.json").read_text())
    provenance = json.loads((batch / "provenance.json").read_text())
    validation = json.loads((batch / "validation_summary.json").read_text())
    require(immutable_manifest() == provenance["input_sha256"], "immutable assets changed since construction")
    require(sha256(batch / "cases.npz") == validation["cases_sha256"], "energy table changed since validation")
    require(sha256(batch / "models.json") == validation["models_sha256"], "models changed since validation")
    records = score["records"]
    for index, record in enumerate(records):
        require(record["index"] == index and record["family"] == models[index]["family"], "record identity mismatch")
        require(abs(record["truth"] - tables[index, -1]) < 1e-14, "record truth mismatch")
    cases = [analyze_case(models[index], tables[index], diagnostics[index], record)
             for index, record in enumerate(records) if record["family"] == "mixed"]
    ordinary = [record for record in records if record["family"] != "mixed"]
    mixed_diagnostics = [item for item in diagnostics if item["family"] == "mixed"]
    seed_summary = {}
    for name in ("fresh_b1", "author_private"):
        selected = [case for case in cases if case["seed_witness"] == name]
        seed_summary[name] = {
            "count": len(selected), "rmse_eh": rmse([case["actual_error_eh"] for case in selected]),
            "mean_signed_error_eh": signed_sum([case["actual_error_eh"] for case in selected]) / len(selected),
            "mean_old_fallback_error_eh": signed_sum([case["old_fallback_error_eh"] for case in selected]) / len(selected),
            "mean_new_fallback_error_eh": signed_sum([case["new_fallback_error_eh"] for case in selected]) / len(selected),
            "mean_actual_minus_fallback_eh": signed_sum([case["actual_minus_fallback_eh"] for case in selected]) / len(selected),
            "old_tail_range_eh": [min(case["old_tail_true_eh"] for case in selected), max(case["old_tail_true_eh"] for case in selected)],
        }
    summary = {
        "candidate_batches_built": len(list(OWNED.glob("batch_??"))),
        "scientific_score_file": score_path.name,
        "diagnostic_only": bool(score.get("diagnostic_only", False)),
        "official_valid": official["valid"], "official_passed": official["passed"], "official_reason": official["reason"],
        "accuracy_targets_met": score["rmse_hartree"] <= 1e-5 and score["worst_family_rmse_hartree"] <= 2.5e-5,
        "rmse_hartree": score["rmse_hartree"], "worst_family_rmse_hartree": score["worst_family_rmse_hartree"],
        "family_rmse_hartree": score["family_rmse_hartree"], "maximum_absolute_error_hartree": score["maximum_absolute_error_hartree"],
        "ordinary_100_rmse_eh": rmse([record["error"] for record in ordinary]),
        "ordinary_100_maximum_absolute_error_eh": max(abs(record["error"]) for record in ordinary),
        "mixed_error_over_25_microhartree_count": sum(abs(case["actual_error_eh"]) > 2.5e-5 for case in cases),
        "mixed_physical_uncertainty_skip_count": sum(case["physical_fit_skipped_by_uncertainty_gate"] for case in cases),
        "mixed_no_net_physical_correction_count": sum(abs(case["actual_minus_fallback_eh"]) < 1e-12 for case in cases),
        "mixed_old_quadruple_count_histogram": dict(Counter(str(case["queried_old_quadruples"]) for case in cases)),
        "mixed_uncertainty_range_eh": [min(case["uncertainty_eh"] for case in cases), max(case["uncertainty_eh"] for case in cases)],
        "mixed_old_triple_maximum_eh": max(item["old_max_abs_triple_eh"] for item in mixed_diagnostics),
        "mixed_new_triple_maximum_range_eh": [min(item["new_max_abs_triple_eh"] for item in mixed_diagnostics), max(item["new_max_abs_triple_eh"] for item in mixed_diagnostics)],
        "cpu_seconds": score.get("cpu_seconds"), "runtime_seconds": score["runtime_seconds"],
        "peak_policy_rss_bytes": score.get("peak_policy_rss_bytes"),
        "maximum_query_cost": score["maximum_query_cost"],
        "query_count_histogram": dict(Counter(str(record["queries"]) for record in records)),
        "seed_groups": seed_summary, "validation": validation,
        "immutable_inputs_unchanged": True,
        "scope": "conditioned stress evidence only; not an IID distributional claim or a new participant",
        "root_cause": "Parent-magnitude covariance systematically underweights old signed >=4 increments despite tiny old triples; active-eighth triples redirect quadruple acquisition. Neural/fitted tail correction is separately measured rather than assumed absent.",
    }
    write_json(batch / "failure_analysis.json", {"summary": summary, "mixed_cases": cases})
    write_json(batch / "summary.json", summary)
    write_json(batch / "artifact_sha256.json", {
        str(path.relative_to(OWNED)): sha256(path)
        for path in sorted(batch.iterdir()) if path.is_file() and path.name != "artifact_sha256.json"
    })
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
