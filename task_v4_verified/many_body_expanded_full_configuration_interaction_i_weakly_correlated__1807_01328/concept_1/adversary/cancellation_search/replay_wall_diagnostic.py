import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

from build_batch import CONCEPT, OWNED, immutable_manifest, require, write_json


sys.path.insert(0, str(CONCEPT / "evaluator"))
from evaluate import limits, sandbox_command
from trusted_protocol import run_policy, summarize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, choices=(1, 2), default=1)
    arguments = parser.parse_args()
    os.umask(0o077)
    batch = OWNED / f"batch_{arguments.batch:02d}"
    official = json.loads((batch / "score.json").read_text())
    require(not official.get("valid") and "wall" in official["reason"].lower(), "diagnostic replay requires an official wall-only failure")
    output = batch / "score_wall600_diagnostic.json"
    require(not output.exists(), "diagnostic score already exists")
    provenance = json.loads((batch / "provenance.json").read_text())
    require(immutable_manifest() == provenance["input_sha256"], "immutable inputs changed before diagnostic")
    command = sandbox_command(CONCEPT / "attempts/v_1")
    guard_index = max(index for index, argument in enumerate(command) if argument == "/resource_guard.py")
    require(command[guard_index - 1] == "/usr/bin/python3", "incorrect guard command occurrence")
    command[guard_index + 1:guard_index + 1] = ["--wall", "600"]
    models = json.loads((batch / "models.json").read_text())
    tables = np.load(batch / "cases.npz", allow_pickle=False)["energies"]
    started = time.monotonic()
    measured = None
    with tempfile.TemporaryFile() as error_log:
        try:
            records, elapsed = run_policy(command, models, tables, wall_seconds=600, preexec_fn=limits, stderr=error_log)
            report = summarize(records, elapsed)
        except Exception as error:
            report = summarize([], time.monotonic() - started, valid=False, reason=f"{type(error).__name__}: {error}")
        error_log.seek(0)
        diagnostics = error_log.read().decode("utf-8", errors="replace")
    (batch / "wall600_guard.log").write_text(diagnostics)
    resource_lines = [line for line in diagnostics.splitlines() if line.startswith("MBE_GUARD_RESOURCE ")]
    if resource_lines:
        measured = json.loads(resource_lines[-1].split(" ", 1)[1])
    accuracy_met = bool(report.get("valid") and report.get("rmse_hartree", float("inf")) <= 1e-5
                        and report.get("worst_family_rmse_hartree", float("inf")) <= 2.5e-5)
    resource_met = bool(measured and measured["reason"] == "ok" and measured["cpu_seconds"] <= 120
                        and measured["peak_rss_bytes"] <= 2147483648)
    report.update(
        diagnostic_only=True, passed=False, accuracy_targets_met=accuracy_met,
        same_cpu_query_memory_limits_satisfied=resource_met,
        relaxed_wall_diagnostic_passed=accuracy_met and resource_met,
        official_wall180_reason=official["reason"], official_score="score.json",
        cpu_seconds=None if measured is None else measured["cpu_seconds"],
        peak_policy_rss_bytes=None if measured is None else measured["peak_rss_bytes"],
        guard_resources=measured,
        limits={"cpu_seconds": 120, "wall_seconds": 600, "memory_bytes": 2147483648, "query_budget": 160},
        isolation="unchanged strict bubblewrap and PID1 guard, only outer and guard wall allowances are 600 seconds",
        controller_resets=1, sandbox_command=command,
        immutable_inputs_unchanged=immutable_manifest() == provenance["input_sha256"],
    )
    if report["valid"]:
        report["reason"] = "diagnostic only; accuracy targets met" if accuracy_met else "diagnostic only; energy accuracy target missed"
    write_json(output, report)
    print(json.dumps({key: value for key, value in report.items() if key not in ("records", "sandbox_command")}, indent=2), flush=True)


if __name__ == "__main__":
    main()
