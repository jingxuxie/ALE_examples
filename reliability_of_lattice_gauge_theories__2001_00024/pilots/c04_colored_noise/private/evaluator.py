import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

from scoring import WEIGHTS, score_result, summarize


PILOT = Path(__file__).resolve().parents[1]
TASK_ROOT = PILOT.parents[1]
sys.path.insert(0, str(TASK_ROOT / "authoring"))


def evaluate(submission, participant, split):
    from isolated_eval import run_solver

    records = []
    paths = sorted((PILOT / "private/challenge_pool" / split).glob("*.json"))
    if not paths:
        raise RuntimeError(f"no frozen cases for {split}")
    for path in paths:
        reserved = json.loads(path.read_text())
        case = reserved["case"]
        label_path = PILOT / "private/reference/outputs" / split / path.name
        label = json.loads(label_path.read_text())
        digest = hashlib.sha256(json.dumps(case, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if digest != label["case_sha256"]:
            raise RuntimeError(f"case/label hash mismatch: {path.name}")
        execution = run_solver(Path(submission).resolve(), Path(participant).resolve(), case,
                               timeout=60, memory_gib=6)
        if execution["ok"] and isinstance(execution.get("result"), dict):
            scored = score_result(case, execution["result"], label)
        else:
            scored = dict(core=0.0, components={name: 0.0 for name in WEIGHTS},
                          raw_errors={name: None for name in WEIGHTS}, validation_errors={})
        scored.update(case_id=case["case_id"], family=reserved["family"], ok=execution["ok"],
                      seconds=execution["seconds"], max_rss_kib=execution.get("max_rss_kib"),
                      error=execution.get("error"))
        records.append(scored)
    return summarize(records)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--participant", type=Path, default=PILOT / "participant")
    parser.add_argument("--split", choices=("screening", "challenge", "confirmation"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    report = evaluate(arguments.submission, arguments.participant, arguments.split)
    report.update(split=arguments.split, submission=str(arguments.submission.resolve()))
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "cases"}, allow_nan=False))


if __name__ == "__main__":
    main()
