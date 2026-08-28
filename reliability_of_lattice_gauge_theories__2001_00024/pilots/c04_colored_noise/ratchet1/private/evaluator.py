import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

from scoring import WEIGHTS, score_result, summarize


RATCHET = Path(__file__).resolve().parents[1]
TASK_ROOT = RATCHET.parents[2]
sys.path.insert(0, str(TASK_ROOT / "authoring"))


def evaluate(submission, participant, split):
    from isolated_eval import run_solver

    paths = sorted((RATCHET / "private/challenge_pool" / split).glob("*.json"))
    if not paths:
        raise RuntimeError(f"No frozen {split} cases; this ratchet allocates screening and reserved confirmation only")
    records = []
    for path in paths:
        reserved = json.loads(path.read_text())
        case = reserved["case"]
        label = json.loads((RATCHET / "private/reference/outputs" / split / path.name).read_text())
        checksum = hashlib.sha256(json.dumps(case, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if checksum != label["case_sha256"]:
            raise RuntimeError(f"case/label hash mismatch: {path.name}")
        execution = run_solver(Path(submission).resolve(), Path(participant).resolve(), case,
                               timeout=60, memory_gib=6, startup_grace=30)
        if execution.get("ok") and isinstance(execution.get("result"), dict):
            record = score_result(case, execution["result"], label)
        else:
            record = dict(core=0.0, components={name: 0.0 for name in WEIGHTS},
                          raw_errors={name: None for name in WEIGHTS}, validation_errors={})
        record.update(case_id=case["case_id"], family=reserved["family"], ok=execution.get("ok", False),
                      seconds=execution.get("seconds"), wall_seconds=execution.get("wall_seconds"),
                      cpu_seconds=execution.get("cpu_seconds"), max_rss_kib=execution.get("max_rss_kib"),
                      cpu_affinity=execution.get("cpu_affinity"), timeout=execution.get("timeout", False),
                      error=execution.get("error"), stderr=execution.get("stderr"))
        records.append(record)
        print(f"{split} {case['case_id']} ok={record['ok']} core={record['core']:.6f}", file=sys.stderr, flush=True)
    report = summarize(records)
    report.update(split=split, submission=str(Path(submission).resolve()),
                  participant=str(Path(participant).resolve()), task_root=str(TASK_ROOT),
                  budget=dict(worker_wall_seconds=60, cpu_soft_seconds=61, cpu_hard_seconds=62,
                              startup_grace_seconds=30, parent_watchdog_seconds=90, memory_gib=6),
                  isolated_api_sha256=hashlib.sha256((TASK_ROOT / "authoring/isolated_eval.py").read_bytes()).hexdigest(),
                  isolated_worker_sha256=hashlib.sha256((TASK_ROOT / "authoring/eval_worker.py").read_bytes()).hexdigest())
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--participant", type=Path, default=RATCHET / "participant")
    parser.add_argument("--split", required=True, choices=("screening", "confirmation"))
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    report = evaluate(arguments.submission, arguments.participant, arguments.split)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "cases"}, allow_nan=False))


if __name__ == "__main__":
    main()
