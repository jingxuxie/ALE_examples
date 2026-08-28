import json
from pathlib import Path


root = Path(__file__).resolve().parent.parent
rows = []
for kind in ["weighted", "fractional", "resolved", "ewoc"]:
    run_path = root / "author" / "runs" / (kind + "_pilot.json")
    report_path = root / "author" / "reports" / (kind + "_pilot.json")
    row = {"kind": kind, "run": "active_or_not_started", "mean_core": None, "mean": None, "worst_family": None}
    if run_path.exists():
        run = json.loads(run_path.read_text())
        row.update(run="finished", exit=run["returncode"], timeout=run["timed_out"], submission=run["submission_exists"], agent_seconds=run["wall_seconds"])
    if report_path.exists():
        report = json.loads(report_path.read_text())
        row.update(mean_core=report["mean_core_score"], mean=report["mean_score"], worst_family=report["worst_family_score"])
        row["worst_branches"] = sorted(report["family_scores"].items(), key=lambda item: item[1])[:4]
    rows.append(row)
print(json.dumps(rows, indent=2))
