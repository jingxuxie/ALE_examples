import argparse
import json
import os
from pathlib import Path
import subprocess
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept", type=Path)
    parser.add_argument("--attempts", type=int, nargs="+", required=True)
    arguments = parser.parse_args()
    concept = arguments.concept.resolve()
    pending = set(arguments.attempts)
    started = time.monotonic()
    while pending:
        if time.monotonic() - started > 3900:
            raise TimeoutError("Fresh attempt metadata did not complete")
        for number in sorted(pending):
            stem = concept / "attempts" / ("v_" + str(number))
            metadata = stem.with_suffix(".run.json")
            if not metadata.exists():
                continue
            try:
                document = json.loads(metadata.read_text())
            except json.JSONDecodeError:
                continue
            if "returncode" not in document:
                continue
            output = stem.with_suffix(".score.json")
            if not output.exists():
                evaluator = Path(document["participant"]).parent / "evaluator/evaluate.py"
                if concept.name == "concept_3":
                    command = ["python3", str(evaluator), str(stem / "witness.json"), "--output", str(output)]
                else:
                    command = ["python3", str(evaluator), "--submission", str(stem), "--output", str(output)]
                environment = dict(os.environ)
                for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
                    environment[variable] = "1"
                with stem.with_suffix(".evaluation.log").open("w") as log:
                    process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                             env=environment, timeout=300, check=False)
                if not output.exists():
                    raise RuntimeError("Evaluator did not write score: " + str(stem) + ", code=" + str(process.returncode))
            report = json.loads(output.read_text())
            summary = {key: report.get(key) for key in ("core_score", "worst_family_score", "passed", "valid", "evaluator_valid", "reason", "runtime_seconds")}
            print(json.dumps({"concept": concept.name, "attempt": number, "score": summary}), flush=True)
            pending.remove(number)
        if pending:
            time.sleep(10)


if __name__ == "__main__":
    main()
