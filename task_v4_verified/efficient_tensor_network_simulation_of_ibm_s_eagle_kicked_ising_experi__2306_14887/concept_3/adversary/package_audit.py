"""Validate the launch layout, staged public runner, and evaluator CLI schema."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")


def run(command, directory):
    return subprocess.run(command, cwd=directory, env=ENVIRONMENT,
                          capture_output=True, text=True, timeout=120)


def main():
    expected = {"TASK.md", "input", "workspace", "baseline"}
    actual = {path.name for path in (ROOT / "participant").iterdir()}
    assert actual == expected, actual
    scenario_path = ROOT / "evaluator" / "hidden" / "scenarios.json"
    assert hashlib.sha256(scenario_path.read_bytes()).hexdigest() == "1ed90b3a74283f39434eb67f3caf41a0bbb3587ee7ae3a8155e8b21327d02d94"
    assert (ROOT / "participant" / "baseline" / "pulses.json").read_bytes() == (ROOT / "attempts" / "baseline_nominal" / "pulses.json").read_bytes()
    required_fields = {"valid", "passed", "score", "core_score", "worst_family_score",
                       "resource_score", "runtime", "runtime_seconds", "reason"}
    for path in (ROOT / "attempts" / "baseline_nominal" / "evaluation.json",
                 ROOT / "champions" / "builder_witness" / "evaluation.json"):
        result = json.loads(path.read_text())
        assert required_fields <= result.keys(), path
        assert result["resource_score"] == 1 and result["runtime"] >= 0
        assert result["core_score"] == result["family_minima"]["core"]
        assert result["worst_family_score"] == result["family_minima"]["worst_family"]
    invalid_cases = []
    with tempfile.TemporaryDirectory(dir=ROOT / "adversary") as temporary:
        directory = Path(temporary)
        staged = directory / "participant"
        shutil.copytree(ROOT / "participant", staged, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        public = run([sys.executable, "workspace/score_public.py", "--submission", "baseline"], staged)
        assert public.returncode == 0, public.stderr
        public_score = json.loads(public.stdout)["public_min_fidelity"]
        assert abs(public_score - 0.889679564487807) < 1e-10
        smoke = run([sys.executable, "baseline/run_baseline.py", "--mode", "random", "--trials", "1",
                     "--output", str(directory / "smoke_submission")], staged)
        assert smoke.returncode == 0, smoke.stderr
        submission = directory / "invalid"
        submission.mkdir()
        for name, bad_value in (("nan", float("nan")), ("boolean", True), ("string", "0")):
            payload = {"schema_version": 1, "angles": [[bad_value, 0]] * 24}
            (submission / "pulses.json").write_text(json.dumps(payload))
            output = directory / (name + ".json")
            process = run([sys.executable, str(ROOT / "evaluator" / "evaluate.py"),
                           "--submission", str(submission), "--output", str(output)], directory)
            assert process.returncode == 2, process.stderr
            result = json.loads(output.read_text())
            assert required_fields <= result.keys()
            assert not result["valid"] and not result["passed"]
            assert all(result[field] == 0 for field in ("score", "core_score", "worst_family_score", "resource_score"))
            assert result["runtime"] >= 0 and result["reason"].startswith("Invalid artifact:")
            invalid_cases.append(name)
    report = {"passed": True, "participant_layout": sorted(actual),
              "hidden_scenario_bytes_unchanged": True, "baseline_bytes_unchanged": True,
              "staged_public_min_fidelity": public_score, "staged_baseline_runner_passed": True,
              "valid_result_schema_passed": True, "invalid_cli_cases": invalid_cases,
              "fresh_agent_launched": False}
    (ROOT / "adversary" / "package_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
