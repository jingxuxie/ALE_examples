import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
from physics import FAMILIES, fisher_features


def covariance_for(features, counts):
    information = features.transpose(0, 2, 1) @ (features * (64 * counts)[None, :, None])
    information += np.eye(14)[None] * 1e-10
    return information, np.linalg.inv(information)


def summarize(name, features, families, parameters, baseline_risks, counts, support, candidates, contract):
    information, covariance = covariance_for(features, counts)
    full_risks = np.trace(covariance[:, :12, :12], axis1=1, axis2=2)
    known_readout_risks = np.trace(np.linalg.inv(information[:, :12, :12]), axis1=1, axis2=2)
    full_diagonal = np.diagonal(covariance[:, :12, :12], axis1=1, axis2=2)
    loss_risks = []
    rows = []
    for local, index in enumerate(support):
        lost_counts = counts.copy()
        lost_counts[local] = 0
        lost_information, lost_covariance = covariance_for(features, lost_counts)
        after = np.trace(lost_covariance[:, :12, :12], axis1=1, axis2=2)
        loss_risks.append(after)
        ratios = after / full_risks
        leverages = 64 * counts[local] * np.sum((features[:, local, None, :] @ covariance)[:, 0, :] *
                                               features[:, local], axis=1)
        increment = np.diagonal(lost_covariance[:, :12, :12], axis1=1, axis2=2) - full_diagonal
        known_after = np.trace(np.linalg.inv(lost_information[:, :12, :12]), axis1=1, axis2=2)
        eigenvalues = np.linalg.eigvalsh(lost_information)
        family_values = {}
        for family in FAMILIES:
            mask = families == family
            parameter_increase = increment[mask].mean(axis=0)
            ranked_parameters = np.argsort(parameter_increase)[::-1]
            family_values[family] = dict(mean_risk_before=float(full_risks[mask].mean()),
                                         mean_risk_after=float(after[mask].mean()),
                                         aggregate_inflation=float(after[mask].mean() / full_risks[mask].mean()),
                                         mean_pointwise_inflation=float(ratios[mask].mean()),
                                         max_pointwise_inflation=float(ratios[mask].max()),
                                         reduction_vs_nominal_baseline=float(1 - after[mask].mean() / baseline_risks[mask].mean()),
                                         mean_leverage=float(leverages[mask].mean()), max_leverage=float(leverages[mask].max()),
                                         dominant_increment_parameters=[dict(parameter=contract["parameter_order"][parameter],
                                                                              mean_risk_increment=float(parameter_increase[parameter]))
                                                                        for parameter in ranked_parameters[:4]])
        worst = int(np.argmax(ratios))
        parameter_increase = increment.mean(axis=0)
        ranked_parameters = np.argsort(parameter_increase)[::-1]
        total_increase = float(after.mean() - full_risks.mean())
        nuisance_increment = total_increase - float(known_after.mean() - known_readout_risks.mean())
        row = dict(candidate_index=int(index), circuit=candidates[index], lost_batches=int(counts[local]),
                   lost_shots=int(counts[local] * 64), mean_risk_after=float(after.mean()),
                   aggregate_inflation=float(after.mean() / full_risks.mean()),
                   mean_pointwise_inflation=float(ratios.mean()), max_pointwise_inflation=float(ratios.max()),
                   core_reduction_vs_nominal_baseline=float(1 - after.mean() / baseline_risks.mean()),
                   worst_family_reduction_vs_nominal_baseline=min(value["reduction_vs_nominal_baseline"] for value in family_values.values()),
                   minimum_information_eigenvalue=float(eigenvalues.min()),
                   minimum_leverage_residual=float(1 - leverages.max()),
                   fraction_points_more_than_double_risk=float(np.mean(ratios > 2)),
                   mean_risk_increment=total_increase,
                   mean_known_readout_risk_increment=float(known_after.mean() - known_readout_risks.mean()),
                   extra_increment_from_unknown_readout=nuisance_increment,
                   nuisance_fraction_of_increment=float(nuisance_increment / total_increase),
                   dominant_increment_parameters=[dict(parameter=contract["parameter_order"][parameter],
                                                        mean_risk_increment=float(parameter_increase[parameter]))
                                                   for parameter in ranked_parameters[:6]],
                   family_results=family_values,
                   worst_point=dict(family=str(families[worst]), parameters=parameters[worst].tolist(),
                                    risk_before=float(full_risks[worst]), risk_after=float(after[worst]),
                                    inflation=float(ratios[worst])))
        row["still_meets_original_score_targets"] = (row["core_reduction_vs_nominal_baseline"] >= 0.5 and
                                                    row["worst_family_reduction_vs_nominal_baseline"] >= 0.4)
        rows.append(row)
    loss_risks = np.array(loss_risks).T
    family_summary = {}
    for family in FAMILIES:
        mask = families == family
        aggregate = loss_risks[mask].mean(axis=0) / full_risks[mask].mean()
        worst_local = int(np.argmax(aggregate))
        family_summary[family] = dict(mean_aggregate_inflation_over_uniform_circuit_loss=float(aggregate.mean()),
                                      max_aggregate_inflation_over_circuit_loss=float(aggregate.max()),
                                      worst_circuit=int(support[worst_local]),
                                      max_pointwise_inflation=float(np.max(loss_risks[mask] / full_risks[mask, None])))
    ranked = sorted(rows, key=lambda row: row["aggregate_inflation"], reverse=True)
    result = dict(dataset=name, scenarios=len(features), circuits=len(support), no_reallocation=True,
                  original_design_unchanged=True, initial_objective_includes_loss=False,
                  inflation_definition="ratio of mean post-loss A-risk to mean intact-design A-risk; pointwise ratios reported separately",
                  mean_risk_before=float(full_risks.mean()),
                  mean_aggregate_inflation_over_uniform_circuit_loss=float(np.mean([row["aggregate_inflation"] for row in rows])),
                  max_aggregate_inflation_over_circuit_loss=ranked[0]["aggregate_inflation"],
                  worst_circuit=ranked[0]["candidate_index"],
                  max_pointwise_inflation=float(np.max(loss_risks / full_risks[:, None])),
                  failures_of_original_targets_after_loss=sum(not row["still_meets_original_score_targets"] for row in rows),
                  family_summary=family_summary, circuits_ranked_by_aggregate_inflation=ranked)
    np.savez_compressed(HERE / f"loss_risks_{name}.npz", loss_risks=loss_risks, intact_risks=full_risks,
                        families=families, parameters=parameters, support=support)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--broad-limit-per-family", type=int, default=500)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    started = time.monotonic()
    candidates = json.loads((ROOT / "participant/input/candidates.json").read_text())
    contract = json.loads((ROOT / "participant/input/contract.json").read_text())
    counts = np.array(json.loads((HERE / "design.json").read_text())["batches"])
    support = np.flatnonzero(counts)
    selected_candidates = [candidates[index] for index in support]
    if args.check_only:
        result = json.loads((HERE / "loss_audit.json").read_text())
        rows = result["broad"]["circuits_ranked_by_aggregate_inflation"]
        selected_rows = {row["candidate_index"]: row for row in rows[:3]}
        for row in sorted(rows, key=lambda value: value["max_pointwise_inflation"], reverse=True)[:3]:
            selected_rows[row["candidate_index"]] = row
        checks = []
        for index, row in selected_rows.items():
            parameter = np.array(row["worst_point"]["parameters"])
            local = int(np.flatnonzero(support == index)[0])
            loss_counts = counts[support].copy()
            loss_counts[local] = 0
            step_ratios = {}
            for step in [1e-6, 5e-7, 2e-7]:
                features = fisher_features(parameter, selected_candidates, step=step)[None]
                information, covariance = covariance_for(features, counts[support])
                lost_information, lost_covariance = covariance_for(features, loss_counts)
                before = float(np.trace(covariance[0, :12, :12]))
                after = float(np.trace(lost_covariance[0, :12, :12]))
                step_ratios[str(step)] = after / before
            column = covariance[0] @ features[0, local]
            leverage = 64 * counts[support[local]] * float(features[0, local] @ column)
            sherman = covariance[0] + 64 * counts[support[local]] * np.outer(column, column) / (1 - leverage)
            sherman_error = abs(float(np.trace(sherman[:12, :12])) / after - 1)
            ratios = np.array(list(step_ratios.values()))
            checks.append(dict(candidate_index=index, family=row["worst_point"]["family"],
                               inflation_by_derivative_step=step_ratios,
                               relative_step_variation=float((ratios.max() - ratios.min()) / ratios[0]),
                               sherman_morrison_relative_risk_error=sherman_error,
                               minimum_loss_information_eigenvalue=float(np.linalg.eigvalsh(lost_information[0]).min()),
                               loss_information_condition_number=float(np.linalg.cond(lost_information[0])),
                               loss_ridge=1e-10))
        checked = dict(checks=checks, design_sha256=result["design_sha256"],
                       passed=all(value["relative_step_variation"] < 1e-5 and
                                  value["sherman_morrison_relative_risk_error"] < 1e-7 and
                                  value["minimum_loss_information_eigenvalue"] > 1e-6 for value in checks))
        (HERE / "loss_numerical_checks.json").write_text(json.dumps(checked, indent=2) + "\n")
        print(json.dumps(checked, indent=2))
        if not checked["passed"]:
            raise SystemExit(1)
        return
    with np.load(ROOT / "evaluator/hidden/benchmark.npz", allow_pickle=False) as hidden:
        hidden_result = summarize("frozen_hidden", hidden["features"][:, support], hidden["families"],
                                  hidden["parameters"], hidden["baseline_risks"], counts[support], support, candidates, contract)
    result = dict(privileged=True, fresh_artifacts_read=False,
                  design_sha256=hashlib.sha256((HERE / "design.json").read_bytes()).hexdigest(),
                  frozen_hidden=hidden_result)
    (HERE / "loss_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"dataset": "frozen_hidden", "mean_inflation": hidden_result["mean_aggregate_inflation_over_uniform_circuit_loss"],
                      "max_inflation": hidden_result["max_aggregate_inflation_over_circuit_loss"],
                      "worst_circuit": hidden_result["worst_circuit"]}), flush=True)
    if args.broad_limit_per_family:
        with np.load(HERE / "broad_space.npz", allow_pickle=False) as broad:
            selected = np.concatenate([np.flatnonzero(broad["families"] == family)[:args.broad_limit_per_family] for family in FAMILIES])
            parameters = broad["parameters"][selected].copy()
            families = broad["families"][selected].copy()
            baseline_risks = broad["baseline_risks"][selected].copy()
            original_candidate_risks = broad["candidate_risks"][selected].copy()
        feature_rows = []
        for index, parameter in enumerate(parameters):
            feature_rows.append(fisher_features(parameter, selected_candidates))
            if (index + 1) % args.broad_limit_per_family == 0:
                print(json.dumps({"event": "broad_loss_feature_generation", "scenarios": index + 1,
                                  "elapsed_seconds": time.monotonic() - started}), flush=True)
        features = np.array(feature_rows)
        broad_result = summarize("broad", features, families, parameters, baseline_risks,
                                 counts[support], support, candidates, contract)
        broad_result["intact_risk_reproduction_mean_error"] = abs(broad_result["mean_risk_before"] - float(original_candidate_risks.mean()))
        result["broad"] = broad_result
    result["wall_seconds"] = time.monotonic() - started
    (HERE / "loss_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    for name in ["frozen_hidden", "broad"]:
        if name in result:
            print(json.dumps({"dataset": name, "mean_inflation": result[name]["mean_aggregate_inflation_over_uniform_circuit_loss"],
                              "max_inflation": result[name]["max_aggregate_inflation_over_circuit_loss"],
                              "worst_circuit": result[name]["worst_circuit"],
                              "family_summary": result[name]["family_summary"]}), flush=True)


if __name__ == "__main__":
    main()
