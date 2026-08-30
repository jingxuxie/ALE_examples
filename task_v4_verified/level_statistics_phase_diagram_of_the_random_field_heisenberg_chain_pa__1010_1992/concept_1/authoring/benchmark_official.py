import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))

from evaluate import score, validate_predictions
from sandbox import run_submission


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    cases = [json.loads(line) for line in (ROOT / "participant/input/validation.jsonl").read_text().splitlines()]
    inputs = {"cases": [{key: case[key] for key in ("id", "L", "fields")} for case in cases]}
    targets = json.loads((ROOT / "evaluator/targets.json").read_text())
    runs = []
    for repeat in range(args.repeats):
        try:
            payload, resources = run_submission(ROOT / "participant/workspace", inputs,
                                                timeout=3, startup_timeout=60, streaming=True,
                                                memory_mb=2048, participant=ROOT / "participant")
            result = score(cases, validate_predictions(payload, cases), targets)
            result.update({"resources": resources, "split": "public_validation",
                           "official_isolated_evaluation": True,
                           "targets_finalized": targets["frozen"]})
        except Exception as error:
            result = {"error": type(error).__name__, "detail": str(error),
                      "official_isolated_evaluation": False}
        runs.append(result)
        output = {"runs": runs, "all_within_limits": all("error" not in run for run in runs),
                  "complete": len(runs) == args.repeats, "hidden_labels_used": False}
        (ROOT / "participant/input/official_streaming_benchmark.json").write_text(json.dumps(output, indent=2) + "\n")
        print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
