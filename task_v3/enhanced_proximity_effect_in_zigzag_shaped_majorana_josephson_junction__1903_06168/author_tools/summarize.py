import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = {
    "01_revision_repair": "Historical geometry/spectrum repair",
    "02_disorder_ensemble": "Calibrated full-size disorder spectra",
    "03_majorana_localization": "Bulk and finite-state localization",
    "04_geometry_design": "Robust manufacturable inverse geometry",
}


def read_optional(path):
    return json.loads(path.read_text()) if path.exists() else None


def main():
    rows = []
    for concept, description in CONCEPTS.items():
        run = ROOT/"pilots"/concept/"private/runs/initial"
        launch = read_optional(run/"launch.json")
        score = read_optional(run/"score.json")
        row = dict(concept=concept, description=description, model="ultima-alpha",
                   score_report=str((run/"score.json").relative_to(ROOT)))
        if launch:
            row.update(attempt_seconds=launch["elapsed_seconds"], returncode=launch["returncode"],
                       status=launch["status"], participant_unchanged=launch["participant_unchanged"])
        else:
            row["status"] = "running_or_not_started"
        if score:
            core = score.get("mean_core_score", score.get("core_score", score.get("score")))
            family_scores = {name: (value["score"] if isinstance(value,dict) else value)
                             for name,value in score.get("families",{}).items()}
            worst = score.get("worst_family_score", min(family_scores.values()) if family_scores else None)
            if not family_scores and "cases" in score:
                family_scores = {case["request_id"]:case["score"] for case in score["cases"] if "request_id" in case}
            row.update(core_score=core, worst_family_score=worst, families=family_scores,
                       grading_seconds=score.get("runtime_seconds"), core_feasibility=score.get("core_feasibility"))
            execution = read_optional(run/"execution.json")
            if execution:
                row["execution"] = execution
                row["maximum_request_seconds"] = max(case["runtime_seconds"] for case in execution)
                row["all_requests_exit_zero"] = all(case["returncode"] == 0 for case in execution)
        else:
            row.update(core_score=None, worst_family_score=None)
        if concept == "02_disorder_ensemble":
            checks = []
            for filename in ("discovery_score.json", "full_pool_holdout_score.json"):
                report = read_optional(run/filename)
                if report:
                    checks.append(dict(report=str((run/filename).relative_to(ROOT)),
                                       core_score=report["core_score"], worst_family_score=report["worst_family"],
                                       runtime_seconds=report["runtime_seconds"], cases=len(report["cases"]),
                                       all_completed=all(case["status"] == "ok" for case in report["cases"])))
            row["additional_pool_checks"] = checks
        rows.append(row)
    document = {"initial_pilots":rows, "initial_tournament_complete":all(row["core_score"] is not None for row in rows),
                "notes":["Missing scores are null, never treated as failures.",
                         "The interrupted stdin-infrastructure launch is excluded.",
                         "Confirmation sessions use the same user-requested model alias, not a different model family."]}
    document["geometry_scope_audits"] = []
    geometry = ROOT/"pilots/04_geometry_design"
    for name in ("scale_research", "highfield_research"):
        report = read_optional(geometry/"private"/name/"submission_score.json")
        if report:
            document["geometry_scope_audits"].append({key: value for key, value in report.items() if key != "measurements"})
    document["ratchets"] = []
    for ratchet in sorted(geometry.glob("ratchet_*")):
        run = ratchet/"private/runs/confirmation"
        launch = read_optional(run/"launch.json")
        score = read_optional(run/"score.json")
        calibrations = [read_optional(path) for path in sorted((ratchet/"private/reference").glob("*_calibration.json"))]
        record = dict(path=str(ratchet.relative_to(ROOT)), model="ultima-alpha",
                      status=launch["status"] if launch else "running_or_not_started",
                      reference_ready=len(calibrations) == 3 and all(item.get("ready") for item in calibrations),
                      core_score=score.get("core_score") if score else None,
                      worst_family_score=score.get("worst_family_score") if score else None,
                      core_feasibility=score.get("core_feasibility") if score else None)
        if launch:
            record.update(attempt_seconds=launch["elapsed_seconds"], participant_unchanged=launch["participant_unchanged"])
        if score:
            record["families"] = {case["request_id"]: case["score"] for case in score["cases"]}
        document["ratchets"].append(record)
    (ROOT/"tournament_results.json").write_text(json.dumps(document, indent=2)+"\n")
    print(json.dumps(document, indent=2))


if __name__ == "__main__":
    main()
