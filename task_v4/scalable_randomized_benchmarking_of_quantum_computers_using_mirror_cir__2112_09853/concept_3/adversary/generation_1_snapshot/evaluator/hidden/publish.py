import copy
import hashlib
import importlib.util
import json
import secrets
import subprocess
import sys
import time
from pathlib import Path

from core import circuit_weights, load_json, score_metrics, summarize, validate_submission


ROOT = Path(__file__).resolve().parents[2]


def read(relative):
    return json.loads((ROOT / relative).read_text())


def write(relative, value):
    (ROOT / relative).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    previous = read("evaluator/hidden/freeze_manifest.json")
    if previous.get("final_freeze"):
        raise RuntimeError("final targets are already frozen; publishing again is prohibited")
    spec = read("evaluator/hidden/provisional_spec.json")
    spec["frozen_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    spec["freeze_kind"] = "final, after harder calibration requested by user"
    spec["baseline_scores_file"] = "baseline_scores.json"
    for family, minima, means in zip(spec["families"], ((8, 6), (9, 7), (8, 5)),
                                     ((11500, 11750), (14000, 14750), (12250, 13000))):
        family["targets"] = {"min_single": minima[0], "min_double": minima[1],
                             "mean_single_milli": means[0], "mean_double_milli": means[1]}
    text = json.dumps(spec, indent=2) + "\n"
    patch = "*** Begin Patch\n"
    for destination in ("participant/input/spec.json", "evaluator/hidden/frozen_spec.json"):
        patch += "*** Delete File: " + destination + "\n*** Add File: " + destination + "\n"
        patch += "".join("+" + line + "\n" for line in text.splitlines())
    patch += "*** End Patch\n"
    subprocess.run(["apply_patch", patch], cwd=ROOT, check=True)
    spec_hash = hashlib.sha256(text.encode()).hexdigest()
    old_seeds = read("evaluator/hidden/fresh_seeds.json")
    write("evaluator/hidden/provisional_fresh_seeds.json", old_seeds)
    new_seeds = [str(secrets.randbits(128)) for _ in spec["families"]]
    write("evaluator/hidden/fresh_seeds.json", new_seeds)
    manifest = {"final_freeze": True, "frozen_utc": spec["frozen_utc"], "spec_sha256": spec_hash,
                "superseded_provisional_sha256": previous["spec_sha256"],
                "supersession_reason": "Explicit user request before any fresh agent run; earlier attempts are calibration-only.",
                "targets_never_changed_after_final_freeze": True,
                "fresh_seed_sha256": [hashlib.sha256(seed.encode()).hexdigest() for seed in new_seeds],
                "fresh_seed_status": "reserved; no post-final-freeze author search has run",
                "fresh_agent_status": "not launched; main owns the fresh run"}
    write("evaluator/hidden/freeze_manifest.json", manifest)
    sources = [read("evaluator/hidden/hard_artifact.json"),
               read("evaluator/hidden/cold_control_artifact.json")]
    candidates = {}
    for artifact in sources:
        for circuit in artifact["circuits"]:
            candidates.setdefault(circuit["family"], []).append(circuit)
    for file_name, family_id in (("grid_tight_result.json", "grid20"), ("bridge_tight_result.json", "bridge18")):
        circuit = read("evaluator/hidden/" + file_name)["artifact"]
        circuit["family"] = family_id
        candidates[family_id].append(circuit)
    selected = []
    for family in spec["families"]:
        def rank(circuit):
            metrics = summarize(family["n"], circuit_weights(family["n"], circuit["layers"]))
            score, failed = score_metrics(metrics, family["targets"])
            return score, -len(failed), sum(value["mean"] for strata in metrics.values() for value in strata.values())
        selected.append(max(candidates[family["id"]], key=rank))
    artifact = {"schema_version": 1, "circuits": selected}
    validate_submission(artifact, spec)
    write("champions/best.json", artifact)
    baseline_started = time.perf_counter()
    subprocess.run([sys.executable, "participant/baseline/solve.py", "--input", "participant/input/spec.json",
                    "--output", "attempts/baseline.json"], cwd=ROOT, check=True)
    baseline_seconds = time.perf_counter() - baseline_started
    for submission, report_path in (("attempts/baseline.json", "attempts/baseline_report.json"),
                                     ("champions/best.json", "champions/best_report.json"),
                                     ("evaluator/hidden/cold_control_artifact.json", "evaluator/hidden/cold_control_final_report.json")):
        completed = subprocess.run([sys.executable, "evaluator/evaluate.py", "--submission", submission,
                                    "--output", report_path], cwd=ROOT, check=True, capture_output=True, text=True)
        json.loads(completed.stdout)
    baseline = read("attempts/baseline_report.json")
    best = read("champions/best_report.json")
    public_baseline = {"seed": 211209853, "trials_per_family": 64, "generation_runtime_seconds": baseline_seconds,
                       "spec_sha256": spec_hash, "artifact_sha256": baseline["artifact_sha256"],
                       "core_score": baseline["core_score"], "worst_family": baseline["worst_family"],
                       "worst_family_score": baseline["worst_family_score"], "resource_score": baseline["resource_score"],
                       "runtime_seconds": baseline["runtime_seconds"], "runtime_score": baseline["runtime_score"],
                       "valid": baseline["valid"], "passed": baseline["passed"],
                       "resources": baseline["resources"], "families": baseline["families"]}
    write("participant/input/baseline_scores.json", public_baseline)
    module_spec = importlib.util.spec_from_file_location("public_reference", ROOT / "participant/baseline/solve.py")
    reference = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(reference)
    independent = {}
    ablations = {}
    for family, circuit in zip(spec["families"], selected):
        expected = reference.measurements(family, circuit)
        observed = [weights.tolist() for strata in circuit_weights(family["n"], circuit["layers"]) for weights in strata]
        if expected != observed:
            raise RuntimeError("independent integer arithmetic disagrees")
        independent[family["id"]] = {"exact_equal": True, "checked_paulis": sum(map(len, observed))}
        deletion_passes = 0
        for layer_index, layer in enumerate(circuit["layers"]):
            for gate_index in range(len(layer["cx"])):
                metrics = summarize(family["n"], circuit_weights(family["n"], circuit["layers"], (layer_index, gate_index)))
                deletion_passes += not score_metrics(metrics, family["targets"])[1]
        round_passes = 0
        for layer_index in range(len(circuit["layers"])):
            shortened = circuit["layers"][:layer_index] + circuit["layers"][layer_index + 1:]
            metrics = summarize(family["n"], circuit_weights(family["n"], shortened))
            round_passes += not score_metrics(metrics, family["targets"])[1]
        ablations[family["id"]] = {"passing_single_cnot_deletions": deletion_passes,
                                  "single_cnot_scenarios": sum(len(layer["cx"]) for layer in circuit["layers"]),
                                  "passing_single_round_deletions": round_passes,
                                  "round_scenarios": len(circuit["layers"]),
                                  "interpretation": "local sensitivity of this circuit only; not a lower bound for other designs"}
    seed_audit = {}
    for filename in ("calibration_seeds.json", "frontier_seeds.json", "hard_seeds.json", "cold_control_seeds.json"):
        record = read("evaluator/hidden/" + filename)
        actual = [hashlib.sha256(seed.encode()).hexdigest() for seed in record["seeds"]]
        if actual != record["sha256"]:
            raise RuntimeError("private seed commitment mismatch")
        seed_audit[filename] = {"verified": True, "sha256": actual}
    for filename in ("grid_tight_seed.json", "bridge_tight_seed.json"):
        record = read("evaluator/hidden/" + filename)
        actual = hashlib.sha256(record["seed"].encode()).hexdigest()
        if actual != record["sha256"]:
            raise RuntimeError("private seed commitment mismatch")
        seed_audit[filename] = {"verified": True, "sha256": actual}
    tests = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "adversary", "-p", "test_*.py", "-v"],
                           cwd=ROOT, capture_output=True, text=True)
    (ROOT / "adversary/tests.log").write_text(tests.stdout + tests.stderr)
    if tests.returncode:
        raise RuntimeError("validation suite failed")
    validation = {"tests_passed": True, "test_methods": 17, "test_log": "adversary/tests.log",
                  "spec_copies_identical": (ROOT / "participant/input/spec.json").read_bytes() == (ROOT / "evaluator/hidden/frozen_spec.json").read_bytes(),
                  "spec_sha256": spec_hash, "independent_exact_comparison": independent, "seed_audit": seed_audit,
                  "code_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                  for name in ("evaluator/evaluate.py", "evaluator/hidden/core.py", "participant/baseline/solve.py")}}
    write("adversary/validation.json", validation)
    write("evaluator/hidden/resource_ablations.json", ablations)
    hard = read("evaluator/hidden/hard_calibration.json")
    private_times = {}
    for family, result in zip(spec["families"], hard["results"]):
        passing_history = []
        for entry in result["history"]:
            minimum = entry["minima"]
            means = entry["means"]
            targets = family["targets"]
            if (min(minimum[::2]) >= targets["min_single"] and min(minimum[1::2]) >= targets["min_double"]
                    and min(means[::2]) * 1000 >= targets["mean_single_milli"]
                    and min(means[1::2]) * 1000 >= targets["mean_double_milli"]):
                passing_history.append(entry)
        private_times[family["id"]] = {"warm_started": True, "iterations": result["iterations"],
            "runtime_seconds": result["runtime_seconds"],
            "first_archived_pass": passing_history[0] if passing_history else None,
            "note": "first archived pass, not an exact first-hitting-time claim; prior warm-start calibration is additional work"}
    status = {"mode": "C WITNESS / DESIGN CONSTRUCTION", "state": "ready_hard_open" if not best["passed"] else "ready_demonstrated",
              "ready_for_fresh_agent": True, "targets_frozen": True, "frozen_utc": spec["frozen_utc"],
              "spec_sha256": spec_hash, "feasibility": "demonstrated" if best["passed"] else "not demonstrated for all families",
              "not_demonstrated_families": [name for name, value in best["families"].items() if not value["passed"]],
              "fresh_agent": "not launched; main handles run_allowlisted_codex --model ultima-alpha",
              "private_best_artifact": "champions/best.json", "private_best_report": "champions/best_report.json",
              "private_best_core_score": best["core_score"], "private_best_passed": best["passed"],
              "baseline_artifact": "attempts/baseline.json", "baseline_report": "attempts/baseline_report.json",
              "baseline_core_score": baseline["core_score"], "baseline_generation_seconds": baseline_seconds,
              "baseline_resources": baseline["resources"], "private_calibration": private_times,
              "targets": {family["id"]: {"max_rounds": family["max_rounds"], "max_cx": family["max_cx"], **family["targets"]} for family in spec["families"]},
              "validation": "adversary/validation.json", "tests_passed": True,
              "difficulty_status": "substantial private calibration; fresh-agent difficulty not yet measured",
              "resource_frontier_status": "empirical sensitivity only, no optimality or impossibility claim"}
    write("status.json", status)
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
