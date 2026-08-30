import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = {1: "schedules.json", 2: "counterexample.json", 3: "circuits.json"}


def main():
    records = []
    environment = os.environ.copy()
    environment["OPENBLAS_NUM_THREADS"] = "1"
    for concept_index, artifact_name in ARTIFACTS.items():
        concept = ROOT / f"concept_{concept_index}"
        for run in sorted((concept / "adversary").glob("run_v_*")):
            metadata = json.loads((run / "run.json").read_text())
            record = {"concept": concept_index, "attempt_index": metadata.get("attempt_index", int(run.name.split("_")[-1])),
                      "generation": metadata["generation"], "completed": metadata["completed"]}
            exclusion = run / "infrastructure_exclusion.json"
            if exclusion.exists():
                record.update({"excluded": True, "exclusion": json.loads(exclusion.read_text())})
                records.append(record)
                continue
            if not metadata["completed"]:
                records.append(record)
                continue
            if not metadata.get("participant_unchanged"):
                raise RuntimeError("participant changed during attempt: " + str(run))
            source = concept / "attempts" / f"v_{record['attempt_index']}"
            snapshot = run / "scored_submission"
            snapshot.mkdir(exist_ok=True)
            if (source / artifact_name).is_file() and not (snapshot / artifact_name).exists():
                if (source / artifact_name).is_symlink():
                    raise RuntimeError("refusing to snapshot a linked artifact")
                shutil.copy2(source / artifact_name, snapshot / artifact_name)
            archived = concept / "adversary/generations" / f"generation_{metadata['generation']}" / "evaluator/evaluate.py"
            evaluator = archived if archived.is_file() else concept / "evaluator/evaluate.py"
            with (run / "evaluation.log").open("w") as log:
                subprocess.run([sys.executable, str(evaluator), "--submission", str(snapshot), "--report", str(run / "score.json")],
                               env=environment, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=75)
            score = json.loads((run / "score.json").read_text())
            record.update({"excluded": False, "score": score, "model": metadata["model"],
                           "elapsed_seconds": metadata["elapsed_seconds"], "timed_out": metadata["timed_out"],
                           "returncode": metadata["returncode"], "participant_unchanged": True,
                           "evaluator": str(evaluator.relative_to(ROOT)),
                           "artifact_sha256": hashlib.sha256((snapshot / artifact_name).read_bytes()).hexdigest() if (snapshot / artifact_name).exists() else None})
            records.append(record)
            print(concept_index, record["attempt_index"], record["generation"], score["core_score"], score["passed"], flush=True)
    (ROOT / "authoring/attempt_registry.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
