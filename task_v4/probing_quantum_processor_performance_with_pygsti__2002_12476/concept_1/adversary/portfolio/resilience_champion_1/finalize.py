import hashlib
import json
import os
import sys
from collections import Counter

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np

from rebased import Benchmark, HERE, ROOT, TARGETS, profile, write_json


def aggregate_roots(benchmark, counts):
    result = profile(benchmark.features, counts, direct=True)
    support = np.flatnonzero(counts)
    rows = benchmark.features[:, support] * 8
    information = rows.transpose(0, 2, 1) @ (rows * counts[support][None, :, None]) + np.eye(14) * 1e-10
    intact_covariance = np.linalg.inv(information)
    lost = result["double_worst_circuits"]
    after_information = information.copy()
    for column in range(2):
        indices = lost[:, column]
        removed = benchmark.features[np.arange(len(rows)), indices] * 8
        after_information -= counts[indices, None, None] * removed[:, :, None] * removed[:, None, :]
    after_covariance = np.linalg.inv(after_information)
    increments = np.diagonal(after_covariance[:, :12, :12] - intact_covariance[:, :12, :12], axis1=1, axis2=2)
    dominant = np.argmax(increments, axis=1)
    groups = []
    for parameter in np.unique(dominant):
        mask = dominant == parameter
        pair_counts = Counter(tuple(int(value) for value in pair) for pair in lost[mask])
        groups.append(dict(dominant_parameter=benchmark.contract["parameter_order"][parameter],
                           operating_points=int(mask.sum()), family_counts=dict(Counter(str(family) for family in benchmark.families[mask])),
                           mean_loss_risk=float(result["double"][mask].mean()),
                           contribution_to_total_mean_increase=float((result["double"][mask] - result["intact"][mask]).sum() / len(rows)),
                           frequent_lost_pairs=[dict(pair=list(pair), frequency=frequency) for pair, frequency in pair_counts.most_common(4)]))
    groups.sort(key=lambda group: group["contribution_to_total_mean_increase"], reverse=True)
    means = increments.mean(axis=0)
    order = np.argsort(means)[::-1]
    return dict(clustering_rule="largest positive marginal target-parameter variance increase after that point's worst pair loss",
                mean_loss_risk=float(result["double"].mean()), mean_increase=float(increments.sum(axis=1).mean()),
                parameter_mean_increments=[dict(parameter=benchmark.contract["parameter_order"][index],
                                                mean_increment=float(means[index])) for index in order],
                clusters=groups)


def main():
    benchmark = Benchmark()
    counts = np.array(json.loads((HERE / "design.json").read_text())["batches"])
    exact = benchmark.evaluate(counts, direct=True)
    write_json(HERE / "score.json", exact)
    audit = json.loads((HERE / "audit_summary.json").read_text())
    numerical = json.loads((HERE / "numerical_checks.json").read_text())
    protected = json.loads((HERE / "protected_hashes.json").read_text())
    changed = [path for path, expected in protected.items() if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected]
    comparisons = {}
    for name, scores in audit["datasets"].items():
        candidate = scores["candidate"]
        comparisons[name] = dict(scenarios=candidate["scenarios"], passed=candidate["passed"],
                                core_score=candidate["core_score"], worst_family_score=candidate["worst_family_score"],
                                intact_mean_ratio=candidate["intact_mean_ratio"],
                                reference_mean_two_loss_risk=candidate["double"]["reference_mean_risk"],
                                candidate_mean_two_loss_risk=candidate["double"]["mean_risk"],
                                family_scores=candidate["double"]["family_scores"],
                                numerical_errors={label: score["direct_inverse_vs_woodbury_relative_error"] for label, score in scores.items()})
    roots = {"reference": aggregate_roots(benchmark, benchmark.reference_counts),
             "candidate": aggregate_roots(benchmark, counts)}
    write_json(HERE / "root_cause_clusters.json", roots)
    records = [json.loads(line) for line in (HERE / "search.jsonl").read_text().splitlines()]
    finished = [record for record in records if record["event"] == "finished"]
    passing = [record for record in records if record["event"] == "improvement" and record["passed"]]
    report = dict(status="feasibility_demonstrated" if exact["passed"] else "achievability_unknown",
                  solvability_demonstrated=exact["passed"], hardness_not_assessed=True,
                  private_generation_time_evidence=True, fresh_attempts_inspected=False,
                  authorized_champion_sha256=benchmark.champion_hash,
                  design_sha256=hashlib.sha256((HERE / "design.json").read_bytes()).hexdigest(),
                  targets=TARGETS, physical_constraints=dict(execution_ticks=exact["execution_ticks"],
                  budget_ticks=benchmark.contract["execution_budget_ticks"], distinct_circuits=exact["distinct_circuits"],
                  total_batches=exact["total_batches"], largest_batch_allocation=int(counts.max())),
                  comparisons=comparisons, numerical_checks_passed=numerical["numerical_checks_passed"],
                  independent_reconstruction_errors=numerical["independent_reconstruction"],
                  protected_paths_checked=len(protected), protected_paths_changed=changed,
                  first_passing_seconds=passing[0]["elapsed_seconds"] if passing else None,
                  completed_search_seconds=finished[0]["elapsed_seconds"] if finished else None,
                  broad_draws_used_for_this_search=False, new_fresh_seed=audit["fresh_seed"],
                  fresh_draws_never_used_for_search=audit["fresh_draws_never_used_for_search"],
                  initial_reference_broad_draws_used_in_prior_private_portfolio_work=True,
                  files=dict(optimizer="optimize.py", evaluator="rebased.py", design="design.json", exact_score="score.json",
                             broad_validation="audit_summary.json", roots="root_cause_clusters.json", search_log="search.jsonl",
                             numerical_verification="numerical_checks.json", documentation="README.md"))
    if (HERE / "robust_audit_summary.json").exists():
        population = json.loads((HERE / "robust_audit_summary.json").read_text())
        robust_counts = np.array(json.loads((HERE / "robust_design.json").read_text())["batches"])
        robust_exact = benchmark.evaluate(robust_counts, direct=True)
        write_json(HERE / "robust_exact_score.json", robust_exact)
        write_json(HERE / "robust_root_cause_clusters.json", aggregate_roots(benchmark, robust_counts))
        from verify_numerics import independent_profile
        independent = independent_profile(benchmark.features, robust_counts)
        canonical = profile(benchmark.features, robust_counts, direct=True)
        report["population_refinement"] = dict(design="robust_design.json", exact_score="robust_exact_score.json",
            design_sha256=hashlib.sha256((HERE / "robust_design.json").read_bytes()).hexdigest(),
            frozen_target_passed=robust_exact["passed"], broad_draws_used_for_selection=True,
            confirmation_seed=population["confirmation_seed"], confirmation_draws_used_for_search=False,
            independent_reconstruction_relative_error={mode: float(np.max(np.abs(independent[mode] / canonical[mode] - 1)))
                                                        for mode in ["intact", "double"]},
            comparisons={name: dict(scenarios=scores["candidate"]["scenarios"],
                core_score=scores["candidate"]["core_score"], worst_family_score=scores["candidate"]["worst_family_score"],
                intact_mean_ratio=scores["candidate"]["intact_mean_ratio"], passed=scores["candidate"]["passed"],
                family_scores=scores["candidate"]["double"]["family_scores"])
                for name, scores in population["datasets"].items()})
    write_json(HERE / "summary.json", report)
    print(json.dumps({key: value for key, value in report.items() if key not in ["comparisons", "files"]}, indent=2))


if __name__ == "__main__":
    main()
