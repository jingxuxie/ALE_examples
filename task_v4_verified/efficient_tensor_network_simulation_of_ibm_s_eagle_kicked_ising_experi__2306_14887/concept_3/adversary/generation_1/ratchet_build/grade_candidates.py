import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    private_candidates = {
        "private_0005_not_a_001_witness": HERE.parent / "drift_0005_validated_candidate.json",
        "private_continuous_001": HERE.parent / "drift_001_private_candidate.json",
        "private_branch_refined_001": HERE.parent / "branch_refined_001_private_candidate.json",
        "private_discrete_branch_001": HERE.parent / "branch_private_candidate.json"
    }
    submissions = {"original_weak_baseline": ROOT / "participant" / "baseline",
                   "generation_0_fresh_champion": ROOT / "champions" / "generation_1",
                   "generation_0_private_builder": ROOT / "champions" / "builder_witness"}
    for name, path in private_candidates.items():
        destination = HERE / "private_submissions" / name
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination / "pulses.json")
        submissions[name] = destination
    grades = {}
    for name, submission in submissions.items():
        output = HERE / "grades" / (name + ".json")
        process = subprocess.run([sys.executable, str(ROOT / "evaluator" / "evaluate.py"),
                                  "--submission", str(submission), "--output", str(output)],
                                 capture_output=True, text=True, timeout=120,
                                 env=dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
                                          MKL_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1"))
        assert process.returncode == 0, process.stderr
        result = json.loads(output.read_text())
        assert result["valid"] and result["parity_checked_scenarios"] == 63
        assert result["nonzero_drift_scenarios"] == 160 and result["scenario_count"] == 223
        grades[name] = result
        print(json.dumps({"candidate": name, "minimum": result["score"], "passed": result["passed"],
                          "core_score": result["core_score"], "worst_family_score": result["worst_family_score"],
                          "runtime": result["runtime"]}), flush=True)
    (HERE / "grade_summary.json").write_text(json.dumps(grades, indent=2) + "\n")


if __name__ == "__main__":
    main()
