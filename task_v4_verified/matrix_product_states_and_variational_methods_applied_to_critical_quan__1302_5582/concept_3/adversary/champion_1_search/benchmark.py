import sys

sys.dont_write_bytecode = True

import argparse
import ast
import copy
import hashlib
from pathlib import Path
import time

import numpy as np

from benchlib import CONCEPT, SIDECAR, evaluate, participant_unchanged, prepare, read, run_isolated, score, write


BATCHES = ("iid_0", "iid_1", "iid_2", "edge_0", "edge_1")


def audit():
    path = CONCEPT / "attempts/v_1/predict.py"
    source = path.read_text()
    tree = ast.parse(source)
    imports = sorted({node.module if isinstance(node, ast.ImportFrom) else alias.name
                      for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
                      for alias in node.names})
    evaluation_path = CONCEPT / "attempts/v_1_audit/evaluation.json"
    original = read(evaluation_path) if evaluation_path.exists() else None
    report = {"source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "source": str(path.relative_to(CONCEPT)), "imports": imports,
              "reported_evaluation_path": str(evaluation_path.relative_to(CONCEPT)),
              "reported_evaluation": original,
              "static_finding": "self-contained legitimate direct phi4 solver; no private-path access, hardcoded labels, or lookup tables observed",
              "used_case_fields": ["id", "sites", "mu2", "lambda", "kappa"],
              "unused_case_fields": ["family", "spectra"], "training_file_opened": False,
              "local_fock_states": 80, "retained_local_states": 16,
              "global_parity_dimensions": {"2": 128, "3": 2048},
              "mechanism": "onsite eigenbasis including bond self-energy, then exact diagonalization of projected intersite coupling",
              "original_contract_violation_found": False,
              "agent_launches": 0}
    write(SIDECAR / "audit.json", report)


def invariance_check(submission, limits, inputs):
    small = {"schema_version": 1, "cases": inputs["cases"][:12]}
    first, first_timing = run_isolated(submission, small, limits)
    changed = copy.deepcopy(small)
    for ordinal, case in enumerate(changed["cases"]):
        case.pop("spectra")
        case["family"] = "unused_family"
        case["id"] = "fresh_relabel_%03d" % ordinal
    changed["cases"].reverse()
    second, second_timing = run_isolated(submission, changed, limits, empty_training=True)
    if first is None or second is None:
        raise RuntimeError("Invariance probe did not run successfully")
    first_values = [row["targets"] for row in first["predictions"]]
    second_values = [row["targets"] for row in reversed(second["predictions"])]
    exact = first_values == second_values
    report = {"passed": exact, "identical_numeric_predictions": exact,
              "ablations": ["all spectra removed", "training cases emptied", "IDs relabelled", "family names replaced", "input order reversed"],
              "first_timing": first_timing, "ablated_timing": second_timing}
    write(SIDECAR / "invariance.json", report)
    if not exact:
        raise AssertionError("Physical-only solver unexpectedly depends on ignored fields")


def scaling(submission, limits, all_inputs):
    results = []
    for sites in (2, 3):
        selected = [case for case in all_inputs["cases"] if case["sites"] == sites]
        for count in (12, 36, 72):
            inputs = {"schema_version": 1, "cases": selected[:count]}
            payload, timing = run_isolated(submission, inputs, limits)
            results.append(dict(timing, sites=sites, cases=count, extrapolated_to_72=False))
            write(SIDECAR / "resource_scaling.json", {"runs": results})
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true")
    arguments = parser.parse_args()
    submission, limits = prepare()
    audit()
    deadline = time.monotonic() + 2400
    results = {}
    all_cases, all_labels, all_predictions = [], [], []
    invariance_done = False
    for batch in BATCHES:
        folder = SIDECAR / "private/batches" / batch
        while not (folder / "inputs.json").exists():
            if not arguments.watch or time.monotonic() > deadline:
                raise RuntimeError("Fresh batch not ready: " + batch)
            time.sleep(2)
        inputs = read(folder / "inputs.json")
        labels = read(folder / "labels.json")
        result_path = SIDECAR / "results" / (batch + ".json")
        prediction_path = SIDECAR / "results" / (batch + "_predictions.json")
        if (result_path.exists() and prediction_path.exists()
                and read(result_path)["timing"].get("solver_profile_available")):
            result, payload = read(result_path), read(prediction_path)
        else:
            if result_path.exists():
                write(SIDECAR / "pre_profile_results" / result_path.name,
                      {"superseded": True, "reason": "wait4 measures bubblewrap launcher, not solver CPU/RSS on this host",
                       "original_result": read(result_path)})
            payload, timing = run_isolated(submission, inputs, limits)
            result = {"batch": batch, "timing": timing}
            if payload is not None:
                result["metrics"] = score(payload, inputs, labels)
                write(prediction_path, payload)
            write(result_path, result)
        if "metrics" not in result:
            raise RuntimeError("Original-domain resource failure: " + batch)
        results[batch] = result
        all_cases.extend(inputs["cases"])
        all_labels.extend(labels["predictions"])
        all_predictions.extend(payload["predictions"])
        print({"batch": batch, "score": result["metrics"]["score"],
               "max_log_error": result["metrics"]["max_log_error"], "timing": result["timing"]}, flush=True)
        if not invariance_done:
            invariance_check(submission, limits, inputs)
            invariance_done = True
        write(SIDECAR / "progress.json", {"completed_batches": len(results), "certified_evaluated_cases": len(all_cases),
                                          "original_domain_failures": sum(not entry["metrics"]["primary_success"] for entry in results.values())})
    pooled_inputs = {"schema_version": 1, "cases": all_cases}
    pooled_labels = {"schema_version": 1, "predictions": all_labels}
    pooled_predictions = {"schema_version": 1, "predictions": all_predictions}
    metrics = score(pooled_predictions, pooled_inputs, pooled_labels)
    original_ids = set()
    original_physics = set()
    for filename in ("participant/input/train.json", "participant/input/validation_inputs.json", "evaluator/hidden/test_inputs.json"):
        for case in read(CONCEPT / filename)["cases"]:
            original_ids.add(case["id"])
            scale = (case["lambda"] / 6) ** (1 / 3)
            original_physics.add((case["sites"], round(case["mu2"] / scale ** 2, 12), round(case["kappa"] / scale ** 2, 12)))
    fresh_physics = set()
    for case in all_cases:
        scale = (case["lambda"] / 6) ** (1 / 3)
        fresh_physics.add((case["sites"], round(case["mu2"] / scale ** 2, 12), round(case["kappa"] / scale ** 2, 12)))
    assert not original_ids.intersection(case["id"] for case in all_cases)
    assert not fresh_physics.intersection(original_physics)
    assert len(fresh_physics) == len(all_cases)
    runtimes = scaling(submission, limits, pooled_inputs)
    report = {"status": "complete", "round": 1, "cases": len(all_cases), "batches": results,
              "pooled_metrics": metrics, "resource_scaling": runtimes,
              "same_physics_original_domain": True, "fresh_disjoint_ids_and_dimensionless_hamiltonians": True,
              "participant_unchanged": participant_unchanged(),
              "original_domain_primary_failures": sum(not result["metrics"]["primary_success"] for result in results.values()),
              "leakage_evidence": False,
              "interpretation": "No original-target ratchet is justified without a real accuracy/resource failure; new dimensions require an explicit new generation.",
              "agent_launches": 0}
    write(SIDECAR / "round_1_report.json", report)
    print({"complete": True, "cases": len(all_cases), "score": metrics["score"],
           "worst_log_error": metrics["max_log_error"], "participant_unchanged": report["participant_unchanged"]}, flush=True)


if __name__ == "__main__":
    main()
