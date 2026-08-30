import sys

sys.dont_write_bytecode = True

import json
from pathlib import Path

import numpy as np

from replay import check_unchanged
from trusted_model import Model


SIDE = Path(__file__).resolve().parent
ROOT = SIDE.parents[1]


def transcript_diagnostics(episode, transcript):
    spec = episode["spec"]
    truth = np.array(episode["rates"])
    estimate = np.array(transcript["estimated_rates"])
    errors = np.log(estimate / truth)
    allocation = np.zeros(len(spec["actions"]))
    for entry in transcript["history"]:
        allocation[entry["query"]["action"]] += entry["query"]["shots"]
    model = Model(spec)
    covariance = np.linalg.inv(np.einsum("a,akl->kl", allocation, model.fisher(np.log(truth))))
    families = np.array([channel["family"] for channel in spec["channels"]])
    bulk_indices = np.flatnonzero(families == "bulk")
    bulk_sse = np.sum(errors[bulk_indices] ** 2)
    groups = {}
    for index in bulk_indices:
        groups.setdefault(tuple(spec["channels"][index]["masks"]), []).append(int(index))
    pairs = []
    for indices in groups.values():
        if len(indices) != 2:
            continue
        first, second = indices
        diagonal = np.diag(covariance)
        correlation = covariance[first, second] / np.sqrt(diagonal[first] * diagonal[second])
        contrast_sd = np.sqrt(diagonal[first] + diagonal[second] - 2 * covariance[first, second])
        pairs.append({"indices": indices, "masks": spec["channels"][first]["masks"],
                      "sectors": [spec["channels"][index]["sector"] for index in indices],
                      "truth": truth[indices].tolist(), "estimate": estimate[indices].tolist(),
                      "log_errors": errors[indices].tolist(),
                      "fraction_of_episode_bulk_sse": float(np.sum(errors[indices]**2) / bulk_sse),
                      "pair_sum_log_error": float(np.log(estimate[indices].sum() / truth[indices].sum())),
                      "log_rate_contrast_error": float(errors[first] - errors[second]),
                      "true_fisher_contrast_sd": float(contrast_sd),
                      "contrast_standardized_by_local_fisher": float((errors[first] - errors[second]) / contrast_sd),
                      "true_fisher_correlation": float(correlation),
                      "true_fisher_marginal_log_sd": np.sqrt(diagonal[indices]).tolist()})
    return {"allocation": allocation.astype(int).tolist(),
            "per_channel_log_errors": errors.tolist(), "bulk_pairs": pairs,
            "realized_allocation_true_fisher_family_log_sd": {
                family: float(np.sqrt(np.mean(np.diag(covariance)[families == family]))) for family in sorted(set(families))},
            "bulk_log_rmse": float(np.sqrt(np.mean(errors[bulk_indices]**2)))}


def main():
    check_unchanged()
    episodes = {episode["id"]: episode for episode in json.loads((ROOT / "evaluator/hidden/episodes.json").read_text())["episodes"]}
    official = json.loads((ROOT / "attempts/v_1_result.json").read_text())
    chain = [episode for episode in official["episodes"] if episode["regime"] == "chain_hooks"]
    chain_mse = np.array([episode["family_mse"]["bulk"] for episode in chain])
    output = {"official_score_unchanged": True,
              "official_mean_family_log_rmse": official["mean_family_log_rmse"],
              "official_worst_family_log_rmse": official["worst_regime_family_log_rmse"],
              "official_chain_bulk_episode_sse_fractions": {episode["id"]: float(value / chain_mse.sum()) for episode, value in zip(chain, chain_mse)},
              "official_other_11_cells_mean": float(np.mean([value for name, value in official["family_log_rmse"].items() if name != "chain_hooks/bulk"])),
              "tapes": {}, "diagnostics": {}}
    for tape in ("official_reproduction", "tape_1", "tape_2", "tape_3"):
        report_path = SIDE / (tape + "_report.json")
        if not report_path.exists():
            continue
        report = json.loads(report_path.read_text())
        output["tapes"][tape] = {}
        for policy, result in report["policies"].items():
            output["tapes"][tape][policy] = {"episodes_completed": len(result["episodes"]),
                "valid": result["valid"], "passes_original_thresholds_on_this_tape": result["passed"],
                "mean_family_log_rmse": result["mean_family_log_rmse"],
                "worst_family_log_rmse": result["worst_regime_family_log_rmse"],
                "chain_bulk_log_rmse": result["family_log_rmse"].get("chain_hooks/bulk"),
                "worst_cell": max(result["family_log_rmse"], key=result["family_log_rmse"].get) if result["valid"] else None,
                "maximum_cpu_seconds": max(row["cpu_seconds"] or 0.0 for row in result["episodes"])}
        for policy in ("candidate", "reference"):
            for episode_id in ("chain_hooks_0", "chain_hooks_1"):
                path = SIDE / "transcripts" / tape / policy / (episode_id + ".json")
                if path.exists():
                    transcript = json.loads(path.read_text())
                    if transcript["estimated_rates"] is not None:
                        output["diagnostics"][tape + "/" + policy + "/" + episode_id] = transcript_diagnostics(episodes[episode_id], transcript)
    trace_path = SIDE / "workspaces/official_reproduction_trace/candidate/chain_hooks_0/submission/trace.json"
    plain_path = SIDE / "transcripts/official_reproduction/candidate/chain_hooks_0.json"
    traced_path = SIDE / "transcripts/official_reproduction_trace/candidate/chain_hooks_0.json"
    if trace_path.exists() and plain_path.exists():
        plain = json.loads(plain_path.read_text())
        traced = json.loads(traced_path.read_text())
        assert plain == traced
        trace = json.loads(trace_path.read_text())
        truth = np.array(episodes["chain_hooks_0"]["rates"])
        records = []
        for record in trace:
            if record["kind"] == "fit":
                errors = np.array(record["log_rates"]) - np.log(truth)
                records.append({"kind": "fit", "shots": record["shots"], "iterations": record["iterations"],
                                "bulk_log_rmse": float(np.sqrt(np.mean(errors[6:14]**2))),
                                "pair_07_13_log_errors": errors[[7, 13]].tolist()})
            elif record["kind"] == "design":
                records.append({"kind": "design", "shots_before": record["shots_before"],
                                "planned_family_log_sd": record["predicted_family_sd_if_full_plan_used"],
                                "allocation": record["allocation"]})
            else:
                before = np.array(record["before_log_rates"]) - np.log(truth)
                after = np.array(record["after_log_rates"]) - np.log(truth)
                records.append({"kind": "posterior", "effective_samples": record["effective_samples"],
                                "bulk_rmse_before": float(np.sqrt(np.mean(before[6:14]**2))),
                                "bulk_rmse_after": float(np.sqrt(np.mean(after[6:14]**2))),
                                "pair_07_13_log_errors_before": before[[7, 13]].tolist(),
                                "pair_07_13_log_errors_after": after[[7, 13]].tolist()})
        output["official_instrumented_trace"] = {"exact_transcript_and_estimate_match": True, "records": records}
        model = Model(episodes["chain_hooks_0"]["spec"])
        counts = np.zeros((len(model.spec["actions"]), model.state_count))
        for entry in plain["history"]:
            counts[entry["query"]["action"]] += entry["observation"]["counts"]
        pre_posterior = np.array(next(record for record in trace if record["kind"] == "posterior")["before_log_rates"])
        random_start = np.random.default_rng(773901).uniform(model.bounds[:, 0], model.bounds[:, 1])
        optimizer = []
        for label, start in (("bounds_midpoint", model.bounds.mean(axis=1)), ("fixed_random", random_start), ("candidate_pre_posterior", pre_posterior)):
            fitted = model.fit(counts, initial=start, iterations=400)
            optimizer.append({"start": label, "log_likelihood": float(np.sum(counts * np.log(model.distribution(fitted)))),
                              "max_log_rate_difference_from_candidate_pre_posterior": float(np.max(np.abs(fitted - pre_posterior))),
                              "bulk_log_rmse": float(np.sqrt(np.mean((fitted[6:14] - np.log(truth[6:14]))**2)))})
        output["independent_trusted_model_optimizer_check"] = optimizer
        original_mse = official["episodes"][0]["family_mse"]["bulk"]
        reproduced_mse = output["diagnostics"]["official_reproduction/candidate/chain_hooks_0"]["bulk_log_rmse"]**2
        assert np.isclose(original_mse, reproduced_mse, rtol=1e-12, atol=1e-14)
    output["limitations"] = ["Only three supplementary random tapes on twelve fixed parameter instances; not a reliable general failure-rate estimate.",
        "Same seed labels do not mean identical observations under different actions and query batching.",
        "True-rate Fisher calculations are post-hoc local diagnostics, not participant-visible information or a causal ablation.",
        "The trace audit imports the frozen candidate only inside an isolated worker with no hidden rates; it is not an additional fresh attempt.",
        "Supplementary threshold passes/failures do not replace or relax the official score and frozen target."]
    (SIDE / "analysis.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"tapes": output["tapes"], "official_contributions": output["official_chain_bulk_episode_sse_fractions"]}, indent=2))
    check_unchanged()


if __name__ == "__main__":
    main()
