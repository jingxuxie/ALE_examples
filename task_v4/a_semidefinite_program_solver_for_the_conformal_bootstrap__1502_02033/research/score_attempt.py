import argparse
import json
import os
from pathlib import Path
import stat
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept", choices=["concept_1", "concept_2", "concept_3"])
    parser.add_argument("--attempt", type=int, default=1)
    arguments = parser.parse_args()
    concept = ROOT / arguments.concept
    attempt = concept / "attempts" / f"v_{arguments.attempt}"
    metadata = json.loads(attempt.with_suffix(".metadata.json").read_text())
    if "finished_utc" not in metadata:
        raise RuntimeError("Do not score an ongoing attempt")
    if not metadata["participant_unchanged"] or not metadata["evaluator_unchanged"]:
        raise RuntimeError("Attempt integrity audit failed")
    filename = {"concept_1": "solution.py", "concept_2": "witness.json", "concept_3": "certificate.json"}[arguments.concept]
    artifact = attempt / filename
    output = attempt.with_suffix(".score.json")
    pending = attempt.with_suffix(".scoring.pending.json")
    if pending.exists():
        raise RuntimeError("An unfinished prior scoring report exists")
    try:
        if not stat.S_ISREG(artifact.lstat().st_mode) or artifact.resolve().parent != attempt.resolve():
            raise ValueError("final artifact must be a regular file inside the fresh output directory")
    except (OSError, ValueError) as error:
        report = {"core_score": 0.0, "worst_family_score": 0.0, "runtime_score": 0.0,
                  "passed": False, "valid": False, "reason": str(error)}
        output.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        return
    current_generation = json.loads((concept / "status.json").read_text()).get("generation", 1)
    packet = concept if metadata["generation"] == current_generation else concept / "adversary" / f"generation_{metadata['generation']}_packet"
    evaluator = packet / "evaluator" / "evaluate.py"
    if arguments.concept == "concept_1":
        command = ["python", str(evaluator), "--solution", str(artifact), "--output", str(pending)]
    elif arguments.concept == "concept_2":
        command = ["python", "-I", str(evaluator), str(artifact), "--output", str(pending)]
    else:
        command = ["python", str(evaluator), str(artifact), "--report", str(pending)]
    process = subprocess.run(command, env=dict(os.environ, OPENBLAS_NUM_THREADS="1",
                             OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1"),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    attempt.with_suffix(".evaluation.log").write_text(process.stdout + "\n" + process.stderr)
    if not pending.is_file():
        raise RuntimeError("Evaluator did not produce a report: " + process.stderr[-1000:])
    report = json.loads(pending.read_text())
    report["regular_artifact_verified"] = True
    report["generation"] = metadata["generation"]
    report["attempt"] = arguments.attempt
    report["model"] = metadata["model"]
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    pending.unlink()
    print(json.dumps({key: value for key, value in report.items() if key not in ["cases", "guard_profiles"]}, indent=2))


if __name__ == "__main__":
    main()
