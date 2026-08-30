"""Public-example-only bwrap checks; never imports the hidden evaluator."""

import os
import sys

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PORTFOLIO = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "evaluator"))
sys.path.insert(0, str(PORTFOLIO / "v1"))
from sandbox_runner import run_submission
from contractor import load_mps, measure


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", default="v1")
    parser.add_argument("--stages", nargs="+", default=["short", "long"])
    args = parser.parse_args()
    submission = PORTFOLIO / args.variant
    report = {"scope": "public examples only", "variant": args.variant, "results": [],
              "source_hashes": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in sorted(submission.glob("*.py"))},
              "full_budgeted_solver_certification": False}
    for example in sorted((ROOT / "participant/input").glob("example_*.json")):
        for stage in args.stages:
            request = json.loads(example.read_text())
            request.update(budget_seconds=6.0 if stage == "short" else 40.0,
                           wall_seconds=30.0 if stage == "short" else 120.0)
            scratch = PORTFOLIO / "public_runs" / args.variant / (example.stem + "-" + stage)
            outcome = run_submission(submission, ROOT / "participant", scratch, request)
            record = {"example": example.name, "stage": stage, "execution": outcome}
            if outcome["process_valid"]:
                try:
                    record["measurement"] = measure(load_mps(outcome["state_path"], request), request)
                    record["valid"] = True
                except Exception as error:
                    record.update(valid=False, error=str(error))
            else:
                record["valid"] = False
            report["results"].append(record)
            (PORTFOLIO / (args.variant + "_public_report.json")).write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
