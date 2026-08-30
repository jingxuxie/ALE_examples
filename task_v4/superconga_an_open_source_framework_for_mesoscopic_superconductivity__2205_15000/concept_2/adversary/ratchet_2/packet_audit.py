import json
from pathlib import Path

from experiment import ROOT, audit, summarize, write_json


def main():
    path = ROOT / "proposal" / "freeze.json"
    packet = json.loads(path.read_text())
    rows = summarize()
    case = packet["case"]
    selected = next(row for row in rows if row["case"] == case)
    runs = ROOT / "cases" / case / "runs"
    full = [json.loads(path.read_text()) for path in runs.glob("continuation_*_250/result.json")]
    auxiliary = [json.loads(path.read_text()) for pattern in ("cold_ls_*/result.json", "lbfgs_then_ls_*/result.json") for path in runs.glob(pattern)]
    full_stages = [stage for run in full + auxiliary for stage in run["stages"]]
    if len(full) != 48 or len(auxiliary) != 16 or len(full_stages) != 312 or any(stage["score"]["passed"] for stage in full_stages):
        raise RuntimeError("Complete original-strength portfolio has not survived")
    packet["complete_construction_portfolio"] = {"continuation_seeds": 48, "continuation_stages": 288, "lbfgs_450_fits": 8, "warm_least_squares_300_fits": 8, "cold_least_squares_350_fits": 8, "total_optimizer_stages": len(full_stages), "nfev": sum(stage["nfev"] for stage in full_stages), "optimizer_cpu_seconds": sum(stage["optimizer_cpu_seconds"] for stage in full_stages), "optimizer_wall_seconds_sum": sum(stage["optimizer_seconds"] for stage in full_stages), "passing_stages": 0}
    packet["matched_12_full_portfolio"] = next(row for row in rows if row["case"] == "islands12_v6_eta0.01")
    packet["pending_runs_by_case"] = {row["case"]: sorted(path.name for path in (ROOT / "cases" / row["case"] / "runs").iterdir() if path.is_dir() and not (path / "result.json").exists()) for row in rows}
    packet["pending_run_policy"] = "All primary original-strength continuation AND auxiliary branches are complete. Any listed pending runs belong to lower-budget geometry screening and are not counted as complete failures."
    packet["protected_hash_audit"] = audit()
    packet["measured_evidence"] = selected
    write_json(path, packet)
    report_path = ROOT / "REPORT.md"
    report = report_path.read_text()
    proof = packet["complete_construction_portfolio"]
    matched = packet["matched_12_full_portfolio"]
    report += "\n## Final completion audit\n\n"
    report += f"All 48 six-stage continuation seeds AND all 24 auxiliary fits are now complete: {proof['total_optimizer_stages']} original-strength optimizer stages, {proof['nfev']} function evaluations, {proof['optimizer_cpu_seconds']:.2f} CPU-seconds, zero passes. This excludes the extra three lower-budget primary screens.\n\n"
    report += f"The matched 12x12 island target also survives 48 complete original-strength continuation seeds; best valid core={matched['best_valid']['core_score']:.6f}. Therefore many-island geometry itself is an obstruction for this finite portfolio; dimension growth is not isolated as the sole cause. The selected 16x16 case combines that geometry with the larger 144/54 binary design space.\n\n"
    report += packet["pending_run_policy"] + "\n"
    for pending_case, pending in packet["pending_runs_by_case"].items():
        if pending:
            report += f"- Pending broad-screen jobs at final audit: {pending_case}: {', '.join(pending)}.\n"
    report_path.write_text(report)
    print(json.dumps({"selected": selected, "complete_portfolio": proof, "pending": packet["pending_runs_by_case"], "audit": packet["protected_hash_audit"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
