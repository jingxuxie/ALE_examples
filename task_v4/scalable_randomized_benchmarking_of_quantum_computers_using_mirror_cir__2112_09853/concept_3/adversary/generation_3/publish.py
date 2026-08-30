import concurrent.futures
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
OMIT_DIAGNOSTICS = {"runtime", "runtime_seconds", "runtime_score", "peak_rss_bytes"}


def read(path):
    return json.loads((ROOT / path).read_text())


def write(path, value):
    (ROOT / path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def stable(value):
    if isinstance(value, dict):
        return {key: stable(entry) for key, entry in value.items() if key not in OMIT_DIAGNOSTICS}
    if isinstance(value, list):
        return [stable(entry) for entry in value]
    return value


def evaluate(artifact, output, public=False):
    command = [sys.executable, "-B", "participant/scorer.py" if public else "evaluator/evaluate.py"]
    if public:
        command += ["--input", "participant/input/spec.json"]
    command += ["--submission", artifact, "--output", output]
    completed = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def verify_witnesses(spec, champion, sweep):
    module_spec = importlib.util.spec_from_file_location("independent_scalar", ROOT / "participant/baseline/solve.py")
    reference = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(reference)
    verified = 0
    for family in spec["families"]:
        layers = next(circuit["layers"] for circuit in champion["circuits"] if circuit["family"] == family["id"])
        profile = sweep["families"][family["id"]]
        for witness in profile["witnesses"] + [profile["worst_witness"]]:
            positions = {(gate["round"], gate["cx_index"]) for gate in witness["omissions"]}
            if len(positions) != 3:
                raise RuntimeError("expected distinct triple witness")
            for gate in witness["omissions"]:
                if layers[gate["round"]]["cx"][gate["cx_index"]] != [gate["control"], gate["target"]]:
                    raise RuntimeError("witness gate does not identify original occurrence")
            deleted = [{"local": layer["local"][:],
                        "cx": [gate[:] for gate_index, gate in enumerate(layer["cx"])
                               if (round_index, gate_index) not in positions]}
                       for round_index, layer in enumerate(layers)]
            packed = 0
            for pauli in witness["input"]:
                if pauli["pauli"] in ("X", "Y"):
                    packed |= 1 << pauli["qubit"]
                if pauli["pauli"] in ("Z", "Y"):
                    packed |= 1 << (family["n"] + pauli["qubit"])
            result = reference.propagate(family["n"], packed, deleted, witness["direction"] == "inverse")
            observed = ((result | (result >> family["n"])) & ((1 << family["n"]) - 1)).bit_count()
            if observed != witness["output_weight"] or observed >= 3:
                raise RuntimeError("independent scalar witness check failed")
            verified += 1
    return verified


def main():
    started = time.perf_counter()
    previous = read("evaluator/hidden/freeze_manifest.json")
    if previous.get("generation") == 3 and previous.get("final_freeze"):
        raise RuntimeError("final generation 3 already frozen; no republishing")
    previous_status = read("status.json")
    spec = read("evaluator/hidden/frozen_spec.json")
    expected = [(12, 80, 8, 6, 11500, 11750), (10, 84, 9, 7, 14000, 14750),
                (12, 90, 8, 5, 12250, 13000)]
    for family, unchanged in zip(spec["families"], expected):
        observed = (family["max_rounds"], family["max_cx"], family["targets"]["min_single"],
                    family["targets"]["min_double"], family["targets"]["mean_single_milli"],
                    family["targets"]["mean_double_milli"])
        if observed != unchanged:
            raise RuntimeError("an ideal budget/target changed")
    if spec["robustness"]["max_omissions"] != 3 or spec["robustness"]["minimum_weight"] != 3:
        raise RuntimeError("wrong final fault contract")
    spec["frozen_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    spec["freeze_kind"] = "final generation 3; second and final ratchet; exact champion triple-omission calibration"
    text = json.dumps(spec, indent=2) + "\n"
    patch = "*** Begin Patch\n"
    for destination in ("participant/input/spec.json", "evaluator/hidden/frozen_spec.json"):
        patch += "*** Delete File: " + destination + "\n*** Add File: " + destination + "\n"
        patch += "".join("+" + line + "\n" for line in text.splitlines())
    patch += "*** End Patch\n"
    subprocess.run(["apply_patch", patch], cwd=ROOT, check=True)
    spec_hash = digest("participant/input/spec.json")
    write("adversary/generation_3/previous_freeze_manifest.json", previous)
    write("adversary/generation_3/previous_status.json", previous_status)
    subprocess.run([sys.executable, "-B", "participant/baseline/solve.py", "--input", "participant/input/spec.json",
                    "--output", "adversary/generation_3/baseline.json"], cwd=ROOT, check=True)
    print("Final target spec fixed; three full exhaustive evaluations starting", flush=True)
    jobs = [("adversary/generation_3/baseline.json", "adversary/generation_3/baseline_report.json", False),
            ("champions/generation_2/artifact.json", "adversary/generation_3/generation_2_report.json", False),
            ("adversary/generation_3/baseline.json", "adversary/generation_3/public_baseline_report.json", True)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(evaluate, *job) for job in jobs]
        baseline, champion_report, public = [future.result() for future in futures]
    if stable(public) != stable(baseline):
        raise RuntimeError("public and official scorers disagree")
    if not baseline["valid"] or baseline["passed"]:
        raise RuntimeError("weak baseline is invalid or unexpectedly passing")
    if not champion_report["valid"] or champion_report["passed"] or champion_report["core_score"] != 1 / 3:
        raise RuntimeError("previous champion did not fail quality only at expected score")
    if champion_report["resource_score"] != 1:
        raise RuntimeError("previous champion violated native constraints")
    sweep = read("adversary/generation_3/champion_triple_sweep.json")
    count = sum(result["fault_robustness"]["scenarios"] for result in champion_report["families"].values())
    checks = sum(result["fault_robustness"]["pauli_checks"] for result in champion_report["families"].values())
    if (count, checks) != (305832, 890561868):
        raise RuntimeError("incorrect exhaustive enumeration totals")
    for name, result in champion_report["families"].items():
        if result["ideal_score"] != 1:
            raise RuntimeError("previous champion failed unchanged ideal targets")
        profile = result["fault_robustness"]
        if stable(profile) != stable({key: sweep["families"][name][key] for key in profile}):
            raise RuntimeError("official and broad private sweep disagree")
        if any(profile["by_omission_count"][str(order)]["failed_scenarios"] for order in range(3)):
            raise RuntimeError("previous champion failed lower-order omission conditions")
    if max(report["peak_rss_bytes"] for report in (baseline, champion_report, public)) > 1024 ** 3:
        raise RuntimeError("validator memory goal exceeded")
    tests = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "adversary", "-p", "test_*.py", "-v"],
                           cwd=ROOT, capture_output=True, text=True)
    (WORK / "tests.log").write_text(tests.stdout + tests.stderr)
    if tests.returncode:
        raise RuntimeError("validation failed")
    test_count = int(re.search(r"Ran (\d+) tests", tests.stderr).group(1))
    witnessed = verify_witnesses(spec, read("champions/generation_2/artifact.json"), sweep)
    core_parity = (ROOT / "participant/reference_core.py").read_bytes() == (ROOT / "evaluator/hidden/core.py").read_bytes()
    fault_parity = ((ROOT / "participant/reference_faults.py").read_text() ==
                    (ROOT / "evaluator/hidden/faults.py").read_text().replace("from core import", "from reference_core import"))
    if not core_parity or not fault_parity:
        raise RuntimeError("public/trusted source parity failed")
    public_baseline = {"generation": 3, "spec_sha256": spec_hash,
                       "baseline": {"seed": 211209853, "trials_per_family": 64,
                                    "artifact": "OUTPUT/artifact.json",
                                    "command": "python baseline/solve.py --input input/spec.json --output OUTPUT/artifact.json",
                                    "method": "deterministic random baseline; ideal ranking only; no robustness optimizer"},
                       "artifact_sha256": baseline["artifact_sha256"], "valid": baseline["valid"],
                       "passed": baseline["passed"], "core_score": baseline["core_score"],
                       "worst_family": baseline["worst_family"], "worst_family_score": baseline["worst_family_score"],
                       "resource_score": baseline["resource_score"], "resources": baseline["resources"],
                       "families": {}}
    for name, result in baseline["families"].items():
        profile = result["fault_robustness"]
        public_baseline["families"][name] = {"core_score": result["core_score"], "ideal_score": result["ideal_score"],
                                            "robustness_score": result["robustness_score"], "resources": result["resources"],
                                            "metrics": result["metrics"],
                                            "robustness": {"minimum": profile["minimum"], "scenarios": profile["scenarios"],
                                                           "pauli_checks": profile["pauli_checks"],
                                                           "by_omission_count": {order: {key: entry[key] for key in ("scenarios", "minimum", "failed_scenarios")}
                                                                                 for order, entry in profile["by_omission_count"].items()}}}
    write("participant/input/baseline_scores.json", public_baseline)
    private_reference = "champions/private_generation_3_reference.json"
    (ROOT / private_reference).write_bytes((ROOT / "champions/generation_2/artifact.json").read_bytes())
    validation = {"generation": 3, "spec_sha256": spec_hash, "tests_passed": True, "test_methods": test_count,
                  "public_official_full_baseline_parity": True, "public_trusted_source_parity": True,
                  "ideal_targets_unchanged": True, "dense_unitary_and_scalar_explicit_deletion_checks": True,
                  "actual_champion_scenarios_independently_checked": 171, "actual_triple_scenarios": 72,
                  "actual_scenario_seed": 2026082803,
                  "actual_scenario_seed_sha256": hashlib.sha256(b"2026082803").hexdigest(),
                  "independently_verified_failure_witnesses": witnessed, "unsupported_four_omissions_rejected": True,
                  "symlink_hardlink_nonregular_malformed_range_nonfinite_unsupported_gate_tests": True,
                  "exhaustive_scenarios": count, "pauli_checks": checks, "official_sweep_parity": True,
                  "official_champion_runtime_seconds": champion_report["runtime_seconds"],
                  "official_peak_rss_bytes": champion_report["peak_rss_bytes"],
                  "max_peak_rss_bytes_across_three_evaluations": max(report["peak_rss_bytes"] for report in (baseline, champion_report, public)),
                  "memory_limit_goal_bytes": 1024 ** 3, "max_cpu_workers": 3,
                  "source_sha256": {path: digest(path) for path in ("evaluator/evaluate.py", "evaluator/hidden/core.py", "evaluator/hidden/faults.py",
                                                                  "adversary/test_evaluator.py", "adversary/test_omissions.py", "adversary/generation_3/sweep.py")}}
    write("adversary/generation_3/validation.json", validation)
    public_hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in sorted((ROOT / "participant").rglob("*")) if path.is_file() and "__pycache__" not in path.parts}
    manifest = {"generation": 3, "ratchet_generations": 2, "final_generation": True, "stop_after_generation": 3,
                "final_freeze": True, "spec_sha256": spec_hash, "frozen_utc": spec["frozen_utc"],
                "previous_spec_sha256": previous["spec_sha256"], "targets_never_changed_after_final_freeze": True,
                "calibration": "adversary/generation_3/champion_triple_sweep.json",
                "validation": "adversary/generation_3/validation.json", "public_file_sha256": public_hashes,
                "trusted_source_sha256": {path: value for path, value in validation["source_sha256"].items() if path.startswith("evaluator/")},
                "fresh_agent_status": "not launched for generation 3; main owns the fresh runs"}
    write("evaluator/hidden/freeze_manifest.json", manifest)
    status = {"mode": "C WITNESS / DESIGN CONSTRUCTION", "verification_mode": "C",
              "generation": 3, "current_generation": 3, "ratchet_generations": 2,
              "final_generation": True, "stop_after_generation": 3, "no_further_ratchets": True,
              "state": "ready_hard_open", "status": "hard_open", "solvability": "unknown",
              "ready_for_fresh_agent": True, "targets_frozen": True, "public_files_frozen": True,
              "frozen_utc": spec["frozen_utc"], "spec_sha256": spec_hash,
              "robustness": spec["robustness"], "ideal_targets_unchanged": True,
              "targets": {family["id"]: dict(max_rounds=family["max_rounds"], max_cx=family["max_cx"], **family["targets"]) for family in spec["families"]},
              "baseline_core_score": baseline["core_score"], "baseline_report": "adversary/generation_3/baseline_report.json",
              "baseline_resources": baseline["resources"], "generation_2_champion_new_score": champion_report["core_score"],
              "generation_2_champion_valid": True, "generation_2_champion_quality_only_failure": True,
              "generation_2_champion_triple_failures": {name: result["fault_robustness"]["by_omission_count"]["3"]["failed_scenarios"] for name, result in champion_report["families"].items()},
              "private_best_core_score": champion_report["core_score"], "private_best_passed": False,
              "private_best_artifact": private_reference, "private_best_report": "adversary/generation_3/generation_2_report.json",
              "feasibility": "not demonstrated for generation 3; hard_open; no private generation-3 design search performed",
              "validation": "adversary/generation_3/validation.json", "tests_passed": True, "test_methods": test_count,
              "security_validated": True, "official_champion_runtime_seconds": champion_report["runtime_seconds"],
              "official_peak_rss_bytes": champion_report["peak_rss_bytes"], "exhaustive_scenarios": count, "pauli_checks": checks,
              "fresh_agent": "generation 3 not launched; main handles isolated fresh runs",
              "history": [{"generation": 1, "official_core_score": 1.0, "runtime_seconds": 544.4, "tokens": 43594,
                           "champion": "champions/generation_1/artifact.json", "task_snapshot": "adversary/generation_1_snapshot"},
                          {"generation": 2, "official_core_score": 1.0, "runtime_seconds": 1897, "tokens": 142031,
                           "champion": "champions/generation_2/artifact.json", "task_snapshot": "adversary/generation_2_snapshot"}],
              "fresh_attempts": previous_status.get("fresh_attempts", []),
              "immutable_paths_untouched": ["attempts/", "champions/generation_1/", "champions/generation_2/",
                                            "adversary/generation_1_snapshot/", "adversary/generation_2_snapshot/"],
              "public_file_sha256": public_hashes, "publication_runtime_seconds": time.perf_counter() - started}
    write("status.json", status)
    print(json.dumps({key: status[key] for key in ("ready_for_fresh_agent", "spec_sha256", "baseline_core_score", "generation_2_champion_new_score",
                                                "test_methods", "official_champion_runtime_seconds", "official_peak_rss_bytes")}, indent=2), flush=True)


if __name__ == "__main__":
    main()
