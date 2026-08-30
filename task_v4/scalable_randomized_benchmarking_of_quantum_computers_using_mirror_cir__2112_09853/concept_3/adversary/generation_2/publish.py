import copy
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent


def read(path):
    return json.loads((ROOT / path).read_text())


def write(path, value):
    (ROOT / path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def without_runtime(value):
    if isinstance(value, dict):
        return {key: without_runtime(entry) for key, entry in value.items()
                if key not in ("runtime", "runtime_seconds", "runtime_score")}
    if isinstance(value, list):
        return [without_runtime(entry) for entry in value]
    return value


def evaluate(artifact, output, public=False):
    command = [sys.executable, "-B", "participant/scorer.py" if public else "evaluator/evaluate.py"]
    if public:
        command += ["--input", "participant/input/spec.json"]
    command += ["--submission", artifact, "--output", output]
    completed = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def main():
    previous = read("evaluator/hidden/freeze_manifest.json")
    if previous.get("generation") == 2 and previous.get("final_freeze"):
        raise RuntimeError("generation 2 already frozen; no republishing")
    spec = read("evaluator/hidden/frozen_spec.json")
    expected = [(12, 80, 8, 6, 11500, 11750), (10, 84, 9, 7, 14000, 14750),
                (12, 90, 8, 5, 12250, 13000)]
    for family, unchanged in zip(spec["families"], expected):
        observed = (family["max_rounds"], family["max_cx"], family["targets"]["min_single"],
                    family["targets"]["min_double"], family["targets"]["mean_single_milli"],
                    family["targets"]["mean_double_milli"])
        if observed != unchanged:
            raise RuntimeError("an ideal budget/target changed")
    spec["frozen_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    spec["freeze_kind"] = "final generation 2, after exhaustive actual-champion omission calibration"
    text = json.dumps(spec, indent=2) + "\n"
    patch = "*** Begin Patch\n"
    for destination in ("participant/input/spec.json", "evaluator/hidden/frozen_spec.json"):
        patch += "*** Delete File: " + destination + "\n*** Add File: " + destination + "\n"
        patch += "".join("+" + line + "\n" for line in text.splitlines())
    patch += "*** End Patch\n"
    subprocess.run(["apply_patch", patch], cwd=ROOT, check=True)
    spec_hash = hashlib.sha256(text.encode()).hexdigest()
    write("adversary/generation_2/previous_freeze_manifest.json", previous)
    source_artifacts = [read("champions/generation_1/artifact.json"), read("champions/private_achievability.json")]
    source_reports = [read("adversary/generation_2/generation_1_report.json"), read("adversary/generation_2/private_v1_report.json")]
    best = {"schema_version": 1, "circuits": []}
    for family in spec["families"]:
        def ranking(index):
            result = source_reports[index]["families"][family["id"]]
            failures = sum(entry["failed_scenarios"] for entry in result["fault_robustness"]["by_omission_count"].values())
            return result["core_score"], -failures
        selected = max(range(len(source_artifacts)), key=ranking)
        best["circuits"].append(copy.deepcopy(next(circuit for circuit in source_artifacts[selected]["circuits"] if circuit["family"] == family["id"])))
    write("champions/private_generation_2_best.json", best)
    baseline = evaluate("adversary/generation_2/baseline.json", "adversary/generation_2/baseline_report.json")
    champion = evaluate("champions/generation_1/artifact.json", "adversary/generation_2/generation_1_report.json")
    best_report = evaluate("champions/private_generation_2_best.json", "champions/private_generation_2_report.json")
    public = evaluate("adversary/generation_2/baseline.json", "adversary/generation_2/public_baseline_report.json", public=True)
    if without_runtime(public) != without_runtime(baseline):
        raise RuntimeError("public and official scorers disagree")
    tests = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "adversary", "-p", "test_*.py", "-v"],
                           cwd=ROOT, capture_output=True, text=True)
    (WORK / "tests.log").write_text(tests.stdout + tests.stderr)
    if tests.returncode:
        raise RuntimeError("validation failed")
    test_count = int(re.search(r"Ran (\d+) tests", tests.stderr).group(1))
    baseline["baseline"] = {"seed": 211209853, "trials_per_family": 64,
                            "artifact": "adversary/generation_2/baseline.json", "method": "weak random-restart reference"}
    write("participant/input/baseline_scores.json", baseline)
    public_core_matches = (ROOT / "participant/reference_core.py").read_text() == (ROOT / "evaluator/hidden/core.py").read_text()
    public_faults_matches = (ROOT / "participant/reference_faults.py").read_text() == (ROOT / "evaluator/hidden/faults.py").read_text().replace("from core import", "from reference_core import")
    if not public_core_matches or not public_faults_matches:
        raise RuntimeError("public physics implementation differs from trusted implementation")
    validation = {"generation": 2, "tests_passed": True, "test_methods": test_count,
                  "spec_sha256": spec_hash, "ideal_budgets_and_targets_unchanged": True,
                  "public_official_reports_identical_except_runtime": True,
                  "public_trusted_physics_source_parity": True,
                  "fault_validation": {"small_subsets": "every zero/single/double subset, explicit deletion and independent scalar arithmetic",
                    "dense_unitary": "every fault subset of a 3-CNOT 3-qubit circuit, both directions",
                    "actual_champion_scenarios": 99, "test_seed": 2026082802,
                    "test_seed_sha256": hashlib.sha256(b"2026082802").hexdigest(),
                    "grading": "exhaustive, no Monte Carlo"},
                  "scenario_counts": {name: value["fault_robustness"]["scenarios"] for name, value in champion["families"].items()},
                  "total_pauli_checks": sum(value["fault_robustness"]["pauli_checks"] for value in champion["families"].values()),
                  "source_sha256": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in
                     ("evaluator/evaluate.py", "evaluator/hidden/core.py", "evaluator/hidden/faults.py", "adversary/test_evaluator.py", "adversary/test_omissions.py")}}
    write("adversary/generation_2/validation.json", validation)
    manifest = {"generation": 2, "ratchet_generations": 1, "final_freeze": True,
                "spec_sha256": spec_hash, "frozen_utc": spec["frozen_utc"],
                "previous_spec_sha256": previous["spec_sha256"],
                "targets_never_changed_after_final_freeze": True,
                "calibration": "adversary/generation_2/champion_omission_sweep.json",
                "fresh_agent_status": "not launched for generation 2; main owns the fresh run"}
    write("evaluator/hidden/freeze_manifest.json", manifest)
    status = {"mode": "C WITNESS / DESIGN CONSTRUCTION", "generation": 2, "ratchet_generations": 1,
              "state": "ready_hard_open" if not best_report["passed"] else "ready_demonstrated",
              "ready_for_fresh_agent": True, "targets_frozen": True, "public_files_frozen": True,
              "frozen_utc": spec["frozen_utc"], "spec_sha256": spec_hash,
              "robustness": spec["robustness"], "ideal_targets_unchanged": True,
              "targets": {family["id"]: {"max_rounds": family["max_rounds"], "max_cx": family["max_cx"], **family["targets"]} for family in spec["families"]},
              "baseline_core_score": baseline["core_score"], "baseline_report": "adversary/generation_2/baseline_report.json",
              "baseline_resources": baseline["resources"],
              "generation_1_champion_new_score": champion["core_score"],
              "generation_1_history": {"official_core_score": 1.0, "runtime_seconds": 544.4, "tokens": 43594,
                  "champion": "champions/generation_1/artifact.json", "task_snapshot": "adversary/generation_1_snapshot",
                  "immutable_paths_untouched": ["attempts/", "champions/generation_1/", "adversary/generation_1_snapshot/"]},
              "private_best_core_score": best_report["core_score"], "private_best_passed": best_report["passed"],
              "private_best_artifact": "champions/private_generation_2_best.json",
              "private_best_report": "champions/private_generation_2_report.json",
              "feasibility": "demonstrated" if best_report["passed"] else "not demonstrated for generation 2; hard_open",
              "validation": "adversary/generation_2/validation.json", "tests_passed": True,
              "test_methods": test_count, "security_validated": True,
              "official_champion_runtime_seconds": champion["runtime_seconds"],
              "fresh_agent": "generation 2 not launched; main handles fresh run",
              "public_file_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                     for path in (ROOT / "participant").rglob("*") if path.is_file() and "__pycache__" not in path.parts}}
    write("status.json", status)
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
