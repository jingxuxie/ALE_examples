import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
PACKET = ROOT.parents[1]
sys.path.insert(0, str(PACKET / "evaluator"))
from evaluate import limits, sandbox_command
from trusted_protocol import run_policy, summarize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", default="candidate_a")
    parser.add_argument("--data", type=Path)
    parser.add_argument("--name", default="candidate_a_fixed")
    arguments = parser.parse_args()
    candidate = ROOT / arguments.candidate
    data = arguments.data or PACKET / "evaluator/hidden"
    deadline = json.loads((ROOT / "budget.json").read_text())["deadline_unix"]
    if time.time() >= deadline - 60:
        raise RuntimeError("portfolio deadline too close for a new benchmark")
    models = json.loads((data / "models.json").read_text())
    tables = np.load(data / "cases.npz", allow_pickle=False)["energies"]
    command = sandbox_command(candidate)
    started = time.monotonic()
    with (ROOT / (arguments.name + "_worker.log")).open("w+") as worker_log:
        try:
            records, elapsed = run_policy(command, models, tables, wall_seconds=min(600, max(1, deadline-time.time())),
                                          preexec_fn=limits, stderr=worker_log)
            report = summarize(records, elapsed)
        except Exception as error:
            report = summarize([], time.monotonic() - started, valid=False, reason=f"{type(error).__name__}: {error}")
        worker_log.flush()
        worker_log.seek(0)
        lines = worker_log.read().splitlines()
    measurements = [json.loads(line.split(" ",1)[1]) for line in lines if line.startswith("MBE_GUARD_RESOURCE ")]
    measured = measurements[-1] if measurements else None
    if measured is None or measured["reason"] != "ok":
        report["passed"] = False
    report.update(
        candidate=arguments.candidate, data_source=str(data), cpu_seconds=None if measured is None else measured["cpu_seconds"],
        peak_policy_rss_bytes=None if measured is None else measured["peak_rss_bytes"], guard_resources=measured,
        cpu_limit=120, query_limit=160, memory_limit_bytes=2147483648, official_guard_wall_limit=600,
        external_portfolio_deadline_only=True, sandbox_command=command,
        isolated=True, controller_resets=1, frozen_evaluator_modified=False,
        resource_accounting="unchanged trusted E2 PID1 guard including descendants",
        submission_sha256={path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(candidate.iterdir()) if path.is_file()},
        actual_query_traces=[json.loads(line) for line in lines if line.startswith('{"portfolio_queries"')],
    )
    (ROOT / (arguments.name + "_score.json")).write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key:value for key,value in report.items() if key not in ("records","actual_query_traces","sandbox_command","submission_sha256")},indent=2),flush=True)


if __name__ == "__main__":
    main()
