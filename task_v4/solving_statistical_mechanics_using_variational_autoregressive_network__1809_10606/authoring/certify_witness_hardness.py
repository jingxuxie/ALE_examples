from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from run_fresh import digest_tree


ROOT = Path(__file__).resolve().parents[1]
GENERATION = ROOT / "concept_2/generations/generation_3"
DESTINATION = GENERATION / "adversary/final_replay"
GATES = (
    ("entropy", "entropy_min", "minimum"),
    ("reverse_kl", "reverse_kl_min", "minimum"),
    ("reward_variance", "reward_variance_max", "maximum"),
    ("gradient_infinity", "gradient_infinity_max", "maximum"),
    ("energy_error_per_spin", "energy_error_per_spin_max", "maximum"),
    ("target_sector_mass", "target_sector_mass_min", "minimum"),
    ("proposal_sector_mass", "proposal_sector_mass_max", "maximum"),
)


def load(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay(name, submission, expected_pass):
    report_path = DESTINATION / (name + ".json")
    subprocess.run(
        [sys.executable, "-I", str(GENERATION / "evaluator/evaluate.py"),
         "--submission", str(submission), "--output", str(report_path)],
        env={**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
             "PYTHONDONTWRITEBYTECODE": "1"},
        check=True, timeout=125, capture_output=True, text=True,
    )
    report = load(report_path)
    assert report["valid"] and report["evaluator_valid"]
    assert report["passed"] is expected_pass
    assert report["resource_score"] == 1
    specification = load(GENERATION / "participant/input/spec.json")
    margins = {}
    for metric, bound_name, direction in GATES:
        value = report["metrics"][metric]
        bound = specification[bound_name]
        margin = value - bound if direction == "minimum" else bound - value
        margins[metric] = {"value": value, "bound": bound, "direction": direction,
                           "signed_passing_margin": margin}
    return {"submission": str(submission.relative_to(ROOT)),
            "witness_sha256": digest(submission / "witness.json"),
            "report": str(report_path.relative_to(ROOT)),
            "report_sha256": digest(report_path), "passed": report["passed"],
            "core_score": report["core_score"], "gates": margins,
            "failing_gates": report["failing_gates"], "resources": report["resource"]}


def main():
    DESTINATION.mkdir(exist_ok=True)
    baseline = DESTINATION / "baseline"
    subprocess.run([sys.executable, "-B", str(GENERATION / "participant/baseline/run.py"),
                    "--output", str(baseline)], check=True, timeout=10,
                   capture_output=True, text=True)
    controls = [replay("baseline", baseline, False)]
    unchanged = []
    for version in (1, 2):
        run = GENERATION / "attempts" / ("v_" + str(version) + "_run")
        metadata = load(run / "metadata.json")
        submission = GENERATION / "attempts" / ("v_" + str(version))
        assert metadata["status"] in ("finished", "time_limit")
        assert metadata["model"] == "ultima-alpha"
        assert metadata["time_limit_seconds"] == 3600
        assert digest_tree(submission) == metadata["submission_sha256"]
        assert digest_tree(GENERATION / "participant") == metadata["participant_sha256"]
        assert digest_tree(GENERATION / "evaluator") == metadata["evaluator_sha256"]
        control = replay("fresh_v_" + str(version), submission, False)
        original = load(run / "score.json")
        repeated = load(ROOT / control["report"])
        delta = max(abs(value - original["metrics"][name])
                    for name, value in repeated["metrics"].items())
        assert delta < 1e-10
        control.update(original_report=str((run / "score.json").relative_to(ROOT)),
                       replay_max_metric_difference=delta,
                       fresh_elapsed_seconds=metadata["elapsed_seconds"])
        controls.append(control)
        unchanged.append(str((run / "metadata.json").relative_to(ROOT)))
    controls.append(replay("private_passing", GENERATION / "adversary/postfresh_refinement/final_best", True))
    independent = load(GENERATION / "adversary/postfresh_refinement/validation.json")
    assert independent["passed"] and independent["maximum_metric_error"] < 1e-10
    certificate = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "hard_verified_achievable", "solvability": "demonstrated",
        "task": str(GENERATION.relative_to(ROOT)),
        "verification": "Exhaustive 65,536-state evaluation; no submitted code is executed.",
        "spec_sha256": digest(GENERATION / "participant/input/spec.json"),
        "evaluator_sha256": digest_tree(GENERATION / "evaluator"),
        "unchanged_fresh_provenance": unchanged,
        "controls": controls, "independent_numerics": independent,
        "valid": True,
    }
    destination = GENERATION / "adversary/hardness_certificate.json"
    destination.write_text(json.dumps(certificate, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"certificate": str(destination), "status": certificate["status"],
                      "controls": [{"name": entry["report"], "passed": entry["passed"],
                                    "core_score": entry["core_score"]} for entry in controls]}))


if __name__ == "__main__":
    main()
