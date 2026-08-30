"""Trusted stencil construction, nearby-root solves, and complete certificates."""

import math
from collections import Counter

import numpy as np

from independent import IndependentSystem


def trusted_points(interaction, radius):
    records = [({"point": 0, "axis": None, "sign": 0}, interaction.copy())]
    point_index = 1
    for row in range(15):
        for column in range(row, 15):
            for sign in (1, -1):
                point = interaction.copy()
                offset = sign * radius if row == column else sign * radius / math.sqrt(2.0)
                point[row, column] += offset
                if row != column:
                    point[column, row] += offset
                records.append(({"point": point_index, "axis": [row, column], "sign": sign}, point))
                point_index += 1
    return records


def evaluate_stencil(data, limits, evaluate_point):
    oracle = IndependentSystem()
    base_report = evaluate_point(data, oracle=oracle, check_path=False)
    if not base_report.get("diagnostics", {}).get("admissible", False):
        base_report["diagnostics"]["stencil"] = {"point_count": 241, "evaluated_points": 1,
                                                   "not_run": "base endpoint rejected"}
        return base_report
    interaction = np.array(data["pair_matrix"], dtype=float)
    interaction = (interaction + interaction.T) / 2
    points = trusted_points(interaction, limits["robust_stencil_radius"])
    if len(points) != limits["robust_stencil_points"]:
        raise ValueError("trusted stencil size mismatch")
    invalid = [{**metadata, "max_entry": float(np.max(abs(point))), "frobenius_norm": float(np.linalg.norm(point))}
               for metadata, point in points if np.max(abs(point)) > limits["pair_entry_max"]
               or np.linalg.norm(point) > limits["pair_frobenius_max"]]
    if invalid:
        return {"schema_version": 1, "generation": "population-witness-v3-robust", "passed": False,
                "score": 0.0, "core_score": 0.0, "threshold": limits["population_violation_min"],
                "worst": {"constraint": "stencil_domain", "point": invalid[0]["point"]},
                "runtime_seconds": 0.0, "reason": "stencil_domain_failure",
                "diagnostics": {"admissible": False, "base": base_report["diagnostics"],
                                "domain_invalid_points": invalid, "physics_failure_claim": False,
                                "stencil": {"point_count": len(points), "evaluated_points": 1}}}
    amplitudes = np.array(data["amplitudes"], dtype=float)
    energies = np.array(limits["orbital_energies"])
    reports = [base_report]
    artifacts = [data]
    for metadata, point in points[1:]:
        hamiltonian, _, _ = oracle.build(energies, point)
        try:
            solution = oracle.solve(hamiltonian, amplitudes)
            artifact = {"schema_version": 1, "orbital_energies": energies.tolist(),
                        "pair_matrix": point.tolist(), "amplitudes": solution.tolist()}
            report = evaluate_point(artifact, oracle=oracle, check_path=False)
        except Exception as error:
            artifact = None
            report = {"passed": False, "score": 0.0, "core_score": 0.0,
                      "reason": "perturbed_root_failure: " + str(error)[:160], "worst": None,
                      "diagnostics": {"admissible": False}}
        reports.append(report)
        artifacts.append(artifact)
    endpoint_feasible = all(report["diagnostics"].get("admissible", False) for report in reports)
    path_count = 0
    if endpoint_feasible:
        for index, artifact in enumerate(artifacts):
            reports[index] = evaluate_point(artifact, oracle=oracle, check_path=True)
            path_count += 1
    records = []
    constraint_failures = Counter()
    for (metadata, point), report in zip(points, reports):
        diagnostic = report["diagnostics"]
        constraints = diagnostic.get("constraints", [])
        failures = [constraint["constraint"] for constraint in constraints if constraint["margin"] < 0]
        if not diagnostic.get("admissible", False) and not failures:
            failures = [report["reason"]]
        constraint_failures.update(failures)
        record = {**metadata, "admissible": diagnostic.get("admissible", False),
                  "reason": report["reason"], "failures": failures, "worst": report.get("worst")}
        for metric in ("occupation_violation", "rdm_dad", "energy_error", "ground_overlap", "reference_weight",
                       "fci_gap", "hf_real_min", "hf_imaginary_min", "cc_residual", "lambda_residual", "lambda_norm",
                       "amplitude_norm", "jacobian_condition", "continuation"):
            if metric in diagnostic:
                record[metric] = diagnostic[metric]
        records.append(record)
    complete = all("occupation_violation" in record for record in records)
    feasible = endpoint_feasible and path_count == len(points) and all(record["admissible"] for record in records)
    observed = [record for record in records if "occupation_violation" in record]
    weakest = min(observed, key=lambda record: record["occupation_violation"])
    largest_dad = max(observed, key=lambda record: record["rdm_dad"])
    largest_error = max(observed, key=lambda record: record["energy_error"])
    raw_score = float(weakest["occupation_violation"])
    core_score = raw_score if feasible else 0.0
    passed = feasible and core_score >= limits["population_violation_min"]
    worst_constraints = [{**record["worst"], "point": record["point"]} for record in records
                         if record["worst"] is not None and "margin" in record["worst"]]
    reason = ("robust_witness_verified" if passed else "robust_constraints_failed" if not feasible
              else "worst_population_violation_below_threshold")
    return {"schema_version": 1, "generation": "population-witness-v3-robust", "passed": bool(passed),
            "score": min(1.0, core_score / limits["population_violation_min"]), "core_score": core_score,
            "threshold": limits["population_violation_min"], "runtime_seconds": 0.0, "reason": reason,
            "worst": min(worst_constraints, key=lambda record: record["margin"]) if worst_constraints else None,
            "diagnostics": {"admissible": feasible, "base": reports[0]["diagnostics"], "points": records,
                            "failure_clusters": dict(constraint_failures), "endpoint_feasible": endpoint_feasible,
                            "worst_population_violation_observed": raw_score, "worst_population_point": weakest["point"],
                            "max_dad_observed": largest_dad["rdm_dad"], "max_dad_point": largest_dad["point"],
                            "max_energy_error_observed": largest_error["energy_error"],
                            "max_energy_error_point": largest_error["point"],
                            "stencil": {"radius": limits["robust_stencil_radius"], "point_count": len(points),
                                        "evaluated_points": len(reports), "all_endpoint_statistics_complete": complete,
                                        "path_certificates_evaluated": path_count}}}
