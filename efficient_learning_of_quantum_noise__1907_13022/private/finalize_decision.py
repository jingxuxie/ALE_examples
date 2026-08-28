from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent.parent
PRIVATE = ROOT / "private"


def read(relative):
    return json.loads((ROOT / relative).read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    summary = read("private/tournament_summary.json")
    sparse = read("concept_01_sparse/private/reference/counterexample_audit/results.json")
    gateset = read("concept_02_gateset/private/reference/counterexample_audit/summary_console.json")
    experiment = read("concept_03_experiment/private/reference/policy_audit/results.json")
    graphical = read("concept_04_graphical/private/reference/counterexample_audit/results.json")
    coded = read("private/coded_probe/results.json")
    records = summary["records"]
    require(len(records) == len(list(ROOT.glob("concept_*"))) == 4, "Exactly four concepts required")
    require(len(list((PRIVATE / "runs/pilot").glob("*.json"))) == 4, "Exactly four initial model runs required")
    require(not (ROOT / "participant").exists(), "Rejected task must not be promoted")
    permitted_changes = {"concept_03_experiment": {"evaluator.py", "reference/reference_score.json"}}
    required_reports = [
        "REPORT.md", "private/CANDIDATES.md", "private/RESEARCH_AUDIT.md",
        "private/GRADER_AUDIT.md", "private/sources_manifest.json", "private/isolation_audit.json",
        "concept_01_sparse/private/reference/counterexample_audit/REPORT.md",
        "concept_02_gateset/private/reference/counterexample_audit/VERDICT.md",
        "concept_03_experiment/private/reference/policy_audit/REPORT.md",
        "concept_04_graphical/private/reference/counterexample_audit/REPORT.md",
        "private/coded_probe/REPORT.md", "private/coded_probe/test_coding.log",
        "private/coded_probe/upstream_tests.log",
    ]
    for relative in required_reports:
        require((ROOT / relative).is_file(), f"Missing evidence: {relative}")
    for filename in ("test_coding.log", "upstream_tests.log"):
        require((PRIVATE / "coded_probe" / filename).read_text().strip().endswith("OK"), f"Unsuccessful {filename}")
    checks = []
    for record in records:
        concept = record["concept"]
        run = read(f"private/runs/pilot/{concept}.json")
        frozen = PRIVATE / "runs/pilot/submissions" / f"{concept}.py"
        require(digest(frozen) == record["submission_sha256"] == run["submission_sha256"], "Frozen solver changed")
        require(record["model"] == run["model"] == "ultima-alpha", "Wrong model")
        require(run["returncode"] == 0 and not run["timed_out"] and run["seconds"] < 3600, "Invalid model completion")
        require(run["participant_unchanged"] and record["participant_unchanged"], "Public task changed during pilot")
        for relative, expected in run["participant_sha256"].items():
            require(digest(ROOT / concept / "participant" / relative) == expected, "Current public artifact changed")
        require(record["reference_mean"] > 0.9, "Numerical reference gate failed")
        require(not record["prelaunch_private_files_missing"], "Private artifact missing")
        require(set(record["prelaunch_private_files_changed"]) <= permitted_changes.get(concept, set()), "Undisclosed private amendment")
        for required in ("participant/TASK.md", "participant/input", "participant/workspace", "private/reference", "private/challenge_pool", "private/evaluator.py", "attempt"):
            require((ROOT / concept / required).exists(), f"Incomplete pilot: {concept}/{required}")
        for pool in ("core", "challenge"):
            require(not record["pools"][pool]["error_cases"], "Clerical error in model scores")
        checks.append(dict(concept=concept, frozen_sha256=digest(frozen), participant_unchanged=True,
                           disclosed_prelaunch_private_changes=record["prelaunch_private_files_changed"]))
    require(sparse["complete"] and sparse["summary"]["retained"] == 12, "Sparse audit incomplete")
    require(sparse["summary"]["protected_files_unchanged"], "Sparse audit mutated protected files")
    require(sparse["summary"]["frozen_minimum_f1"] == 1, "Unexpected sparse failure")
    require(gateset["qualified_count"] == gateset["case_count"] == 9, "Gate audit incomplete")
    require(gateset["identification_errors"] == 0 and gateset["protected_artifacts_unchanged"], "Gate audit failed")
    require(experiment["protected_files_unchanged"], "Experimental audit mutated protected files")
    require(len(graphical["cases"]) == 6 and not graphical["failure_cases"], "Graphical audit incomplete")
    require(graphical["protected_files_unchanged"], "Graphical audit mutated protected files")
    require(len(coded) == 3 and all(case["reference_eligible"] for case in coded), "Coded reference failed")
    require(all(case["frozen"]["recovery_score"] == 1 and case["frozen"]["score"] > 0.9 for case in coded), "Unexpected coded failure")
    by_concept = {record["concept"]: record for record in records}
    reasons = {
        "concept_01_sparse": "Robustly solved, including twelve fresh boundary cases and three coded-index probes; no genuine failure region.",
        "concept_02_gateset": "Robustly solved, including nine informative family shifts and exact structural/calibration identifiability.",
        "concept_03_experiment": "Low score is not a valid hardness certificate: public target omits a consequential private fit policy and true real-device channels are unknown.",
        "concept_04_graphical": "Exact blanket marginals enable generic conditional-logit recovery plus log-domain elimination; six fresh regions also solved.",
    }
    audits = {
        "concept_01_sparse": dict(boundary_summary=sparse["summary"], coded_probe_cases=len(coded),
                                  coded_reference_mean=sum(case["reference"]["score"] for case in coded) / len(coded),
                                  coded_frozen_mean=sum(case["frozen"]["score"] for case in coded) / len(coded),
                                  evidence=required_reports[6], coded_evidence="private/coded_probe/REPORT.md"),
        "concept_02_gateset": dict(summary=gateset, evidence=required_reports[7]),
        "concept_03_experiment": dict(independent_acquisitions=4, reference_is_latent_truth=False,
                                      evidence=required_reports[8]),
        "concept_04_graphical": dict(fresh_cases=6, frozen=graphical["frozen"], reference=graphical["reference"],
                                     evidence=required_reports[9]),
    }
    decisions = []
    for concept, record in by_concept.items():
        decisions.append(dict(concept=concept, accepted=False, status="rejected", reason=reasons[concept],
                              initial=record, counterexample_audit=audits[concept],
                              ratchets_used=0, ratchet_limit=2, confirmation_score=None,
                              confirmation_status="not_run_no_eligible_ratchet"))
    ranking = sorted(records, key=lambda record: (record["pools"]["core"]["worst_family"], record["pools"]["core"]["mean"]))
    now = datetime.now(timezone.utc).isoformat()
    decision = dict(schema_version=1, generated_utc=now, status="rejected_no_qualifying_task",
                    accepted=False, selected_concept=None, production_promoted=False,
                    paper="Efficient learning of quantum noise", arxiv="1907.13022",
                    model="ultima-alpha", pilot_time_limit_seconds=3600,
                    concepts_built=4, maximum_concepts=4, initial_fresh_attempts=4,
                    primary_screening_finalists=[record["concept"] for record in ranking[:2]],
                    valid_backup_audited="concept_02_gateset",
                    raw_ranking=[record["concept"] for record in ranking],
                    ratchets_total=0, second_model_attempts=0, final_confirmation_score=None,
                    confirmation_reason="No valid reference-wins/submission-fails region; no ratcheted task qualified.",
                    original_core_cases=sum(record["pools"]["core"]["cases"] for record in records),
                    original_challenge_cases=sum(record["pools"]["challenge"]["cases"] for record in records),
                    additional_fresh_numerical_cases=30, audited_real_acquisitions=4,
                    scope="Bounded rejection of the four built concepts; not a proof that all paper-derived tasks are easy.",
                    concepts=decisions, report="REPORT.md")
    require(decision["original_core_cases"] == 39 and decision["original_challenge_cases"] == 26, "Case totals changed")
    (ROOT / "decision.json").write_text(json.dumps(decision, indent=2, allow_nan=False) + "\n")
    source = PRIVATE / "sources/python-bchlib"
    commit = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    require(commit == "8d0656ab8f37e734428635501738d360ad80eebd", "BCH source changed")
    provenance = dict(repository="jkent/python-bchlib", commit=commit, source_version="2.1.3",
                      purpose="Private coded-index audit only; not a fifth concept or ratchet",
                      files={path.name: digest(path) for path in source.glob("bchlib*.so")},
                      license_sha256=digest(source / "COPYING"))
    (PRIVATE / "coded_probe/provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    evidence_hashes = {relative: digest(ROOT / relative) for relative in required_reports}
    evidence_hashes["private/finalize_decision.py"] = digest(Path(__file__).resolve())
    evidence_hashes["private/summarize_tournament.py"] = digest(PRIVATE / "summarize_tournament.py")
    evidence_hashes["decision.json"] = digest(ROOT / "decision.json")
    integrity = dict(schema_version=1, checked_utc=now, status="passed", checks=checks,
                     fresh_audit_protected_hashes_unchanged=True, model_count=4,
                     original_cases=65, additional_fresh_numerical_cases=30,
                     second_model_attempts=0, no_production_task=True,
                     coded_tests_passed=True, evidence_sha256=evidence_hashes)
    (PRIVATE / "final_integrity.json").write_text(json.dumps(integrity, indent=2) + "\n")
    print(json.dumps(dict(status=decision["status"], concepts=4, original_cases=65,
                          fresh_cases=30, ratchets=0, confirmation_attempts=0, integrity="passed"), indent=2))


if __name__ == "__main__":
    main()
