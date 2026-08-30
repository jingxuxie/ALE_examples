"""Cluster sweep failures and independently audit representative witnesses."""

import os
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from drift_audit import ENGINE, HERE, PROTOCOL, REFERENCE, ROOT, SPEC, summarize
import numpy as np


def independent_checks(record, evaluation):
    family, metrics = min(evaluation["families"].items(), key=lambda pair: pair[1]["margin"])
    angles = PROTOCOL.waveforms(record["witness"], SPEC)[family]
    oracle = REFERENCE.exact_state(angles)
    tensor_reference = ENGINE.exact_state(angles)
    full_rank = ENGINE.mps_state(angles, 64)[0]
    overlap = np.vdot(oracle, full_rank)
    checks = {"independent_exact_state_error": float(np.linalg.norm(oracle - tensor_reference)),
              "oracle_norm_error": float(abs(np.linalg.norm(oracle) - 1)),
              "chi64_state_error": float(np.linalg.norm(full_rank - overlap / abs(overlap) * oracle)),
              "independent_observable_error": float(abs(ENGINE.measure(tensor_reference)["zz1"] - REFERENCE.zz1(oracle)))}
    original_svd = ENGINE.svd
    def alternate_svd(*args, **kwargs):
        kwargs["lapack_driver"] = "gesdd"
        return original_svd(*args, **kwargs)
    alternate = []
    try:
        ENGINE.svd = alternate_svd
        for chi in SPEC["chis"]:
            alternate.append(REFERENCE.zz1(ENGINE.mps_state(angles, chi)[0]))
    finally:
        ENGINE.svd = original_svd
    checks["svd_driver_max_estimate_difference"] = float(np.max(np.abs(np.array(alternate) - metrics["estimates"])))
    alternative_metrics = PROTOCOL.metrics(REFERENCE.zz1(oracle), alternate, SPEC)
    return {"family": family, "checks": checks, "passed": all(value < 2e-8 for value in checks.values()),
            "alternate_driver_metrics": alternative_metrics,
            "failure_reproduces_across_drivers": not alternative_metrics["passed"] if not metrics["passed"] else alternative_metrics["passed"]}


def trajectory(angles, chi):
    original_compress = ENGINE.compress
    layers = []
    def measured_compression(tensors, cap):
        discarded, gaps, ties = original_compress(tensors, cap)
        layers.append({"layer": len(layers) + 1, "zz1": REFERENCE.zz1(ENGINE.expand_mps(tensors)),
                       "discarded_sum": float(sum(discarded)), "minimum_gap": float(min(gaps, default=1)),
                       "cut_ties": ties})
        return discarded, gaps, ties
    try:
        ENGINE.compress = measured_compression
        ENGINE.mps_state(angles, chi)
    finally:
        ENGINE.compress = original_compress
    return layers


def main():
    records = [json.loads(line) for line in (HERE / "sweep.jsonl").read_text().splitlines()]
    baselines = {record["champion"]: record for record in records if record["suite"] == "baseline"}
    groups = summarize(records)
    clusters = Counter()
    corner_shapes = {}
    detailed = []
    for record in records:
        if record["suite"] == "baseline" or not record["valid"]:
            continue
        baseline = baselines[record["champion"]]
        if record["suite"] == "corners":
            total = sum(record["direction"])
            shape = "uniform" if abs(total) == 6 else "balanced_zero_mean" if total == 0 else "mixed_unbalanced"
            key = f"{record['champion']}|{record['epsilon']:.7f}|{shape}"
            shape_group = corner_shapes.setdefault(key, {"cases": 0, "failed": 0})
            shape_group["cases"] += 1
            shape_group["failed"] += int(not record["passed"])
        for family, item in record["families"].items():
            if item["passed"]:
                continue
            original = baseline["families"][family]
            shifts = np.asarray(item["estimates"]) - original["estimates"]
            pair = (0, 1) if item["limiting_pair"] == "4_8" else (1, 2)
            dominant = max(pair, key=lambda index: abs(shifts[index]))
            cluster = f"{item['failure_type']}|pair_{item['limiting_pair']}|dominant_chi_{SPEC['chis'][dominant]}"
            clusters[record["champion"] + "|" + cluster] += 1
            detailed.append({"champion": record["champion"], "epsilon": record["epsilon"], "suite": record["suite"],
                             "name": record["name"], "family": family, "cluster": cluster,
                             "spread": item["spread"], "error": item["error"],
                             "exact_shift": item["exact"] - original["exact"], "estimate_shifts": shifts.tolist()})
    (HERE / "failure_clusters.json").write_text(json.dumps({"counts": clusters, "corner_shape_counts": corner_shapes, "failing_families": detailed}, indent=2) + "\n")
    selected = []
    for champion in baselines:
        failures = [record for record in records if record["champion"] == champion and record["valid"] and not record["passed"]]
        if not failures:
            continue
        smallest = min(record["epsilon"] for record in failures)
        first = min((record for record in failures if record["epsilon"] == smallest), key=lambda record: record["worst_family_score"])
        worst = min(failures, key=lambda record: record["worst_family_score"])
        selected.extend([("smallest_failing_scale", first), ("strongest_failure", worst)])
    audits = []
    for label, record in selected:
        name = f"{record['champion']}_{label}"
        directory = HERE / "failures" / name
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "witness.json").write_text(json.dumps(record["witness"], indent=2) + "\n")
        (directory / "case.json").write_text(json.dumps(record, indent=2) + "\n")
        subprocess.run([sys.executable, "-I", str(ROOT / "evaluator" / "evaluate.py"),
                        "--submission", str(directory), "--output", str(directory / "evaluation.json")], check=True)
        evaluation = json.loads((directory / "evaluation.json").read_text())
        difference = max(abs(evaluation["families"][family][key] - item[key])
                         for family, item in record["families"].items() for key in ("spread", "error", "exact"))
        audit = independent_checks(record, evaluation)
        audit.update(label=label, champion=record["champion"], epsilon=record["epsilon"],
                     suite=record["suite"], name=record["name"], direction=record["direction"],
                     path=str(directory.relative_to(ROOT)), frozen_checker_passed=evaluation["passed"],
                     frozen_checker_valid=evaluation["valid"], sweep_checker_max_difference=difference,
                     worst_family_score=evaluation["worst_family_score"],
                     maximum_spread=record["maximum_spread"], minimum_error=record["minimum_error"])
        if label == "smallest_failing_scale":
            family = audit["family"]
            baseline_angles = PROTOCOL.waveforms(baselines[record["champion"]]["witness"], SPEC)[family]
            drifted_angles = PROTOCOL.waveforms(record["witness"], SPEC)[family]
            trace = {"family": family, "baseline": {}, "drifted": {}}
            for chi in SPEC["chis"]:
                trace["baseline"][str(chi)] = trajectory(baseline_angles, chi)
                trace["drifted"][str(chi)] = trajectory(drifted_angles, chi)
            trace["exact_baseline"] = [REFERENCE.zz1(REFERENCE.exact_state(baseline_angles[:depth])) for depth in range(1, len(baseline_angles) + 1)]
            trace["exact_drifted"] = [REFERENCE.zz1(REFERENCE.exact_state(drifted_angles[:depth])) for depth in range(1, len(drifted_angles) + 1)]
            (directory / "trajectory.json").write_text(json.dumps(trace, indent=2) + "\n")
        (directory / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
        audits.append(audit)
    fresh_corners = sorted((group for group in groups if group["champion"] == "fresh" and group["suite"] == "corners"),
                           key=lambda group: group["epsilon"])
    substantive = [group for group in fresh_corners if group["cases"] == 64 and group["cases"] - group["passed"] >= 7]
    proposed = substantive[0]["epsilon"] if substantive else None
    proposal = {"status": "proposal_only_not_frozen", "epsilon": proposed,
                "selection_rule": "Smallest tested scale failing at least 7 of the 64 fresh-champion corners (at least 10% of this deterministic finite set).",
                "thresholds_unchanged": {"error_min": 0.15, "spread_max": 0.008},
                "family_definition": "Original five perturbations crossed with zero drift plus all 64 independent six-knot +/-epsilon corners.",
                "physical_waveforms_per_witness": 325,
                "constraint_definition": "Nominal six knots obey original bounds; every actual corner-plus-original-family waveform obeys strict (0.1,1.47) angles and slew <=0.12.",
                "grading_definition": "Every waveform must have exact chi16 error >=0.15 and max consecutive chi4/8/16 spread <=0.008. Retain original nominal core score; worst-family is minimum over the 325-case suite.",
                "continuous_box_certificate": False,
                "random_points_are_evidence_not_secret_grading_tests": True,
                "original_generation_modified": False,
                "fresh_launches": 0}
    if proposed is not None:
        proposal["tested_witnesses_at_proposed_scale"] = [group for group in groups if group["epsilon"] == proposed and group["suite"] == "corners"]
        proposal["known_passing_witness"] = any(group["passed"] == 64 for group in proposal["tested_witnesses_at_proposed_scale"])
        proposal["feasibility_status"] = "known_witness" if proposal["known_passing_witness"] else "hard_open_candidate_needs_builder_C_feasibility_search"
    (HERE / "proposal.json").write_text(json.dumps(proposal, indent=2) + "\n")
    manifest = json.loads((ROOT / "freeze_manifest.json").read_text())
    changes = [name for name, digest in manifest["files"].items() if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
    source = ROOT / "attempts" / "frozen_v_1"
    destination = ROOT / "champions" / "generation_1"
    hashes = lambda directory: {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in directory.rglob("*") if path.is_file()}
    final = {"audits": audits, "all_independent_checks_passed": all(audit["passed"] and audit["failure_reproduces_across_drivers"] and audit["sweep_checker_max_difference"] < 2e-8 for audit in audits),
             "frozen_file_changes": changes, "champion_copy_still_byte_identical": hashes(source) == hashes(destination),
             "proposal": proposal}
    (HERE / "final_audit.json").write_text(json.dumps(final, indent=2) + "\n")
    print(json.dumps({"selected_cases": len(audits), "independent_checks_passed": final["all_independent_checks_passed"],
                      "proposed_epsilon": proposed, "frozen_file_changes": changes}))


if __name__ == "__main__":
    main()
