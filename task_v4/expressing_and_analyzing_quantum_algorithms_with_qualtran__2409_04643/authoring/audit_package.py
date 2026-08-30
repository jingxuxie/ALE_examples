import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = {1: "schedules.json", 2: "counterexample.json", 3: "circuits.json"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("nonfinite numerical score output")
    if isinstance(value, dict):
        for item in value.values():
            assert_finite(item)
    elif isinstance(value, list):
        for item in value:
            assert_finite(item)


def frozen_files(directory):
    result = {}
    for section in ("participant", "evaluator"):
        for path in (directory / section).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and not path.name.endswith("score.json"):
                if path.is_symlink():
                    raise ValueError("linked frozen asset: " + str(path))
                result[str(path.relative_to(directory))] = digest(path)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    environment = os.environ.copy()
    environment.update({"OPENBLAS_NUM_THREADS": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    record = {"audited_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "freezes": [], "baselines": [], "attempts": [], "active_runs": []}
    for concept_index, artifact_name in ARTIFACTS.items():
        concept = ROOT / f"concept_{concept_index}"
        for manifest in sorted((concept / "adversary").glob("generation_*_freeze.json")):
            frozen = json.loads(manifest.read_text())
            archived = concept / "adversary/generations" / f"generation_{frozen['generation']}"
            directory = archived if (archived / "participant").is_dir() else concept
            actual = frozen_files(directory)
            expected = frozen["sha256"]
            differing = sorted(name for name in set(actual) | set(expected) if actual.get(name) != expected.get(name))
            if differing:
                raise ValueError(f"frozen files differ: {manifest}: {differing}")
            record["freezes"].append({"concept": concept_index, "generation": frozen["generation"],
                                     "files_checked": len(actual), "unchanged": True})
        output = concept / "adversary/final_baseline_replay"
        output.mkdir(exist_ok=True)
        command = [sys.executable, str(concept / "participant/baseline/solve.py"),
                   "--output", str(output / artifact_name)]
        if concept_index != 2:
            command.extend(["--input", str(concept / "participant/input")])
        subprocess.run(command, env=environment, check=True, timeout=60)
        with (output / "evaluation.log").open("w") as log:
            subprocess.run([sys.executable, str(concept / "evaluator/evaluate.py"),
                            "--submission", str(output), "--report", str(output / "score.json")],
                           env=environment, stdout=log, stderr=subprocess.STDOUT,
                           check=True, timeout=75)
        score = json.loads((output / "score.json").read_text())
        assert_finite(score)
        record["baselines"].append({"concept": concept_index,
                                    "artifact_sha256": digest(output / artifact_name),
                                    "score": score})
        for run in sorted((concept / "adversary").glob("run_v_*")):
            metadata = json.loads((run / "run.json").read_text())
            item = {"concept": concept_index, "attempt": run.name,
                    "generation": metadata["generation"], "completed": metadata["completed"]}
            if (run / "infrastructure_exclusion.json").exists():
                item["excluded"] = True
            elif not metadata["completed"]:
                record["active_runs"].append(str(run.relative_to(ROOT)))
            else:
                if not (run / "score.json").exists():
                    raise ValueError("completed attempt must be scored before final audit: " + str(run))
                assert_finite(json.loads((run / "score.json").read_text()))
                if not metadata["initial_output_empty"] or not metadata["participant_unchanged"]:
                    raise ValueError("invalid freshness or participant mutation: " + str(run))
                frozen = json.loads((concept / "adversary" / f"generation_{metadata['generation']}_freeze.json").read_text())
                if frozen["frozen_utc"] >= metadata["started_utc"]:
                    raise ValueError("freeze was not before launch: " + str(run))
                if metadata["model"] != "ultima-alpha" or metadata["time_limit_seconds"] != 3600:
                    raise ValueError("wrong model or time budget: " + str(run))
                if (Path(metadata["runtime"]) / "auth.json").exists():
                    raise ValueError("completed runtime still holds copied credentials: " + str(run))
                item.update({"freshness_valid": True, "participant_unchanged": True,
                             "time_limit_seconds": 3600, "elapsed_seconds": metadata["elapsed_seconds"],
                             "copied_credentials_removed": True})
            record["attempts"].append(item)
    record["completed"] = not record["active_runs"]
    record["passed"] = True
    (ROOT / "authoring/package_audit.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"passed": True, "completed": record["completed"],
                      "frozen_generations": len(record["freezes"]),
                      "baselines_replayed": len(record["baselines"]),
                      "active_runs": record["active_runs"]}, indent=2))
    if args.require_complete and not record["completed"]:
        raise SystemExit("active runs remain; no final hardness decision yet")


if __name__ == "__main__":
    main()
