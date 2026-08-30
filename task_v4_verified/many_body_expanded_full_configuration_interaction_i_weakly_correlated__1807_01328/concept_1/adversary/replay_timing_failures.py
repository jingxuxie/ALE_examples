import json
import sys
import tempfile
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from evaluate import limits, sandbox_command
from trusted_protocol import run_policy, summarize


def replay(batch):
    tables = np.load(batch / "cases.npz", allow_pickle=False)["energies"]
    models = json.loads((batch / "models.json").read_text())
    command = sandbox_command(ROOT / "champions/generation_1/submission")
    insertion = max(index for index, value in enumerate(command) if value == "/resource_guard.py") + 1
    command[insertion:insertion] = ["--wall", "600"]
    started = time.monotonic()
    with tempfile.TemporaryFile() as error_log:
        try:
            records, elapsed = run_policy(command, models, tables, wall_seconds=600,
                                          preexec_fn=limits, stderr=error_log)
            error_log.seek(0)
            lines = error_log.read().decode("utf-8", errors="replace").splitlines()
            if not lines or not lines[-1].startswith("MBE_GUARD_RESOURCE "):
                raise RuntimeError("missing trusted namespace accounting")
            measured = json.loads(lines[-1].split(" ", 1)[1])
            report = summarize(records, elapsed)
            report.update(cpu_seconds=measured["cpu_seconds"], peak_policy_rss_bytes=measured["peak_rss_bytes"])
            if measured["reason"] != "ok":
                report.update(passed=False, reason=measured["reason"], resource_score=0.0)
        except Exception as error:
            error_log.seek(0)
            report = summarize([], time.monotonic() - started, valid=False, reason=str(error))
            report["worker_diagnostics"] = error_log.read().decode("utf-8", errors="replace")[-6000:]
    report.update(diagnostic_only=True, diagnostic_wall_limit_seconds=600,
                  official_wall_limit_seconds=180, cpu_limit_seconds=120,
                  official_replay_passed=bool(report["passed"] and report["runtime_seconds"] <= 180),
                  original_report="score.json", interpretation="Accuracy diagnostic only; original wall-time failures are not reclassified.")
    (batch / "timing_diagnostic.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key not in ("records", "worker_diagnostics")}), flush=True)
    return report


def main():
    search = ROOT / "adversary/champion_search"
    reports = []
    for index in range(5):
        batch = search / f"batch_{index}"
        official = json.loads((batch / "score.json").read_text())
        reports.append(official if official["valid"] else replay(batch))
    records = [record for report in reports for record in report.get("records", [])]
    family_rmse = {family: float(np.sqrt(np.mean([record["error"] ** 2 for record in records if record["family"] == family])))
                   for family in sorted({record["family"] for record in records})}
    summary = {"diagnostic_only": True, "case_count": len(records), "requested_case_count": 600,
               "all_batches_valid": all(report["valid"] for report in reports),
               "accuracy_passed_batches": sum(report["passed"] for report in reports),
               "rmse_hartree": float(np.sqrt(np.mean([record["error"] ** 2 for record in records]))),
               "family_rmse_hartree": family_rmse, "worst_family_rmse_hartree": max(family_rmse.values()),
               "maximum_absolute_error_hartree": max(abs(record["error"]) for record in records),
               "over_25_microhartree": sum(abs(record["error"]) > 2.5e-5 for record in records),
               "cpu_limit_seconds_per_batch": 120, "relaxed_wall_seconds_for_replays": 600,
               "original_wall_only_failures": 2,
               "interpretation": "Scientific accuracy search with CPU/query/memory unchanged. Two original wall failures are preserved separately; not evidence of substantive hardness."}
    (search / "timing_diagnostic_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
