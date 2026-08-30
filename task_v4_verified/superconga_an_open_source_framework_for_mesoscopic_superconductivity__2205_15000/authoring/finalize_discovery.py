import datetime
import hashlib
import json
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def load(relative):
    return json.loads((ROOT / relative).read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(relative, value):
    (ROOT / relative).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def score(relative):
    value = load(relative)
    value = value.get("summary", value)
    keys = ("core_score", "worst_family_score", "runtime_score", "valid", "passed", "reason")
    return {**{key: value[key] for key in keys}, "report": relative}


def verify_hashes(base, expected):
    for relative, checksum in expected.items():
        path = base / relative
        if not path.is_file() or digest(path) != checksum:
            raise RuntimeError("integrity mismatch: " + str(path))
    return len(expected)


def audit_attempt(concept_name, generation, label, current_generation):
    concept = ROOT / concept_name
    prefix = concept_name + "/attempts/" + label
    launch = load(prefix + ".launch.json")
    finished = load(prefix + ".exit.json")
    if launch["model"] != "ultima-alpha" or launch["limit_seconds"] != 3600:
        raise RuntimeError("unexpected fresh configuration")
    if not launch["output_initially_empty"] or not launch["ephemeral"]:
        raise RuntimeError("attempt was not isolated and fresh")
    if finished["returncode"] != 0 or finished["timed_out"]:
        raise RuntimeError("abnormal fresh exit requires manual review")
    packet = concept if generation == current_generation else concept / "champions" / ("generation_" + str(generation))
    verified = verify_hashes(packet / "participant", launch["participant_sha256"])
    deadline = datetime.datetime.fromisoformat(launch["started_utc"]).timestamp() + 3600
    files = {}
    for relative in finished["artifacts"]:
        path = concept / "attempts" / label / relative
        if path.suffix not in (".py", ".json", ".md") or "__pycache__" in path.parts:
            continue
        if path.is_symlink() or path.stat().st_mtime > deadline:
            raise RuntimeError("late or linked final artifact: " + str(path))
        files[relative] = digest(path)
    return {"concept": concept_name, "generation": generation, "label": label,
            "model": launch["model"], "effort": launch["effort"],
            "limit_seconds": launch["limit_seconds"], "wall_seconds": finished["wall_seconds"],
            "exit_code": finished["returncode"], "participant_hashes_verified": verified,
            "output_initially_empty": True, "ephemeral": True,
            "artifacts_written_before_deadline": True, "artifact_sha256": files,
            "score": score(prefix + ".evaluation.json")}


def pair(value):
    return "{:.4f} / {:.4f}".format(value["core_score"], value["worst_family_score"])


def main():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    specifications = (("concept_1", 1, "v_1", 2), ("concept_1", 2, "v_2", 2),
                      ("concept_2", 1, "v_1", 3), ("concept_2", 2, "v_2", 3),
                      ("concept_2", 2, "v_2_r2", 3), ("concept_2", 3, "v_3", 3),
                      ("concept_2", 3, "v_3_r2", 3), ("concept_3", 1, "v_1", 1))
    attempts = [audit_attempt(*specification) for specification in specifications]
    final_gl = score("concept_1/attempts/v_2.evaluation.json")
    gl_review = load("concept_1/adversary/ratchet_2/report.json")
    if not final_gl["passed"] or gl_review["proposal"] is not None:
        raise RuntimeError("GL review requires another decision before finalization")
    if gl_review["status"] not in ("resource_inconclusive", "no_meaningful_ratchet"):
        raise RuntimeError("GL private replay is unfinished")
    baseline_gl = score("concept_1/attempts/generation_2_baseline.json")
    privileged_gl = score("concept_1/attempts/generation_2_privileged.json")
    if not privileged_gl["passed"]:
        raise RuntimeError("claimed resource-bounded GL achievability was not demonstrated")
    gl_state = {
        "concept": "gl_vortex_state_optimization", "verification_mode": "A_BASELINE_IMPROVEMENT",
        "status": "solved", "final_status": "solved", "phase": "complete",
        "valid": True, "retained": False, "updated_utc": now,
        "generation": 2, "task_generations": 2, "ratchet_generations": 1,
        "fresh_model_sessions_run": 2, "target": load("concept_1/evaluator/hidden/target.json"),
        "baseline": baseline_gl, "baseline_entrypoint": "participant/baseline/solve.py",
        "current_champion": {**final_gl, "artifact": "champions/generation_2"},
        "known_achievable": {**privileged_gl, "artifact": "champions/in_budget_generation_2"},
        "solvability": "demonstrated by both the fresh generation-2 submission and a private input-only solver within the actual 60-second resource limits",
        "fresh_attempts": [attempt for attempt in attempts if attempt["concept"] == "concept_1"],
        "generation_history": [
            {"generation": 1, "status": "solved", "baseline": score("concept_1/attempts/baseline_sandbox_report.json"),
             "private_in_budget": score("concept_1/attempts/qualified_portfolio_report.json"),
             "fresh": score("concept_1/attempts/v_1.evaluation.json"), "champion": "champions/generation_1"},
            {"generation": 2, "status": "solved", "baseline": baseline_gl,
             "private_in_budget": privileged_gl, "fresh": final_gl, "champion": "champions/generation_2"}
        ],
        "counterexample_search": {
            "ratchet_1": {"physical_cases": 24, "persistent_meaningful_cases": 6,
                          "installed_cases": 3, "report": "adversary/ratchet_1/REPORT.md",
                          "unchanged_champion_warm_core_repeats": [0.068777081799, 1.48197e-11]},
            "ratchet_2": {"status": gl_review["status"], "physical_cases_preserved": 24,
                          "selected_replay_cases": gl_review["selected_replay_count"],
                          "solver_processes_launched": gl_review["solver_processes_launched"],
                          "stable_qualifying_cases": gl_review["stable_meaningful_cases"],
                          "proposal_installed": False, "report": "adversary/ratchet_2/REPORT.md",
                          "diagnostic_broad_score": gl_review["diagnostic_broad_score"],
                          "score_note": "Not an official generation-2 score; outside its focused prior. Resource-inconclusive trials do not establish new hardness or broad robustness."}
        },
        "decision_basis": "The fresh solver meets every frozen generation-2 energy, stationarity and resource gate. The subsequent broader replay did not validate a further hard generation under its declared controls.",
        "failure_capability": None,
        "validation": {"unit_tests": 19, "test_log": "attempts/generation_2_tests_final.txt",
                       "release_manifest": "evaluator/release_manifest.json"},
        "limits": ["Attained witnesses are not asserted global ground states.",
                   "The broader review is resource-inconclusive, not evidence of a universally robust solver.",
                   "This is a near-Tc GL surrogate, not native SuperConga quasiclassical output."]
    }
    parent_review = ROOT / "concept_1/adversary/ratchet_2/parent_review.json"
    if parent_review.is_file():
        gl_state["counterexample_search"]["ratchet_2"]["parent_review"] = str(parent_review.relative_to(ROOT))
        gl_state["counterexample_search"]["ratchet_2"]["parent_review_conclusion"] = "The two vortex-pinning gaps survive normally terminating repeats with ample unused budget. However, preexisting generation-1 champion fields retrospectively close 0.953946 and 0.798063 of these gaps, leaving only 0.055357 and 0.110349 energy units. These are regressions to previously demonstrated capability, not a promising new hard generation. Historical initial arrays differ; this is not a new exact-input runtime qualification."
    save("concept_1/status.json", gl_state)
    spectral_state = load("concept_2/status.json")
    tomography_state = load("concept_3/status.json")
    if spectral_state["status"] != "hard_verified_achievable" or tomography_state["status"] != "solved":
        raise RuntimeError("unexpected concept verdicts")
    integrity_counts = {}
    gl_manifest = load("concept_1/evaluator/release_manifest.json")
    for field in ("participant", "evaluator"):
        integrity_counts["gl_" + field] = verify_hashes(ROOT / "concept_1", gl_manifest[field]["files"])
    integrity_counts["spectral_freeze"] = verify_hashes(ROOT / "concept_2", load("concept_2/evaluator/hidden/freeze.json")["sha256"])
    tomography_manifest = load("concept_3/evaluator/hidden/checker_revision_2.json")
    for field in ("sha256", "unchanged_scientific_participant_and_archive_sha256", "new_report_sha256"):
        integrity_counts["tomography_" + field] = verify_hashes(ROOT / "concept_3", tomography_manifest[field])
    tests = {}
    logs = {"concept_1": "concept_1/attempts/generation_2_tests_final.txt",
            "concept_2": "concept_2/attempts/final_tests.txt",
            "concept_3": "concept_3/attempts/checker_revision_2/validation_release.txt"}
    for concept_name, relative in logs.items():
        text = (ROOT / relative).read_text()
        count = re.search(r"Ran (\d+) tests", text)
        if count is None or not text.rstrip().endswith("OK"):
            raise RuntimeError("test suite did not pass: " + relative)
        tests[concept_name] = {"count": int(count.group(1)), "passed": True, "report": relative, "sha256": digest(ROOT / relative)}
        participant = ROOT / concept_name / "participant"
        for required in ("TASK.md", "input", "workspace", "baseline"):
            if not (participant / required).exists():
                raise RuntimeError("missing participant component")
        if any(path.is_symlink() for path in participant.rglob("*")):
            raise RuntimeError("public packet contains a symlink")
    target_keys = {}
    for generation in (1, 2, 3):
        packet = ROOT / "concept_2" if generation == 3 else ROOT / "concept_2/champions" / ("generation_" + str(generation))
        with np.load(packet / "participant/input/target.npz", allow_pickle=False) as target:
            if target.files != ["ldos"]:
                raise RuntimeError("spectral public target has extra fields")
            target_keys[str(generation)] = {"keys": target.files, "shape": list(target["ldos"].shape)}
    baseline_tomography = score("concept_3/attempts/checker_revision_2/baseline_full12.json")
    champion_tomography = score("concept_3/attempts/checker_revision_2/champion_full12.json")
    state = {
        "paper": "SuperConga: An open-source framework for mesoscopic superconductivity",
        "arxiv": "2205.15000", "session_type": "HARDNESS_DISCOVERY",
        "status": "hard_verified_achievable", "final_status": "hard_verified_achievable",
        "phase": "complete", "completed_utc": now, "valid": True,
        "retained_concepts": ["concept_2"], "primary_task": "concept_2/participant/TASK.md",
        "solvability": "demonstrated for the retained spectral design by an independently checked private feasible artifact",
        "concepts_built": 3, "internal_concepts_considered": 10,
        "verification_modes": ["A_BASELINE_IMPROVEMENT", "C_WITNESS_OR_DESIGN_CONSTRUCTION", "E_ACTIVE_EXPERIMENT_DESIGN"],
        "fresh_model": "ultima-alpha", "fresh_limit_seconds": 3600,
        "fresh_sessions": len(attempts), "fresh_attempts": attempts,
        "task_generations": {"concept_1": 2, "concept_2": 3, "concept_3": 1},
        "ratchet_generations": {"concept_1": 1, "concept_2": 2, "concept_3": 0},
        "concept_statuses": {"concept_1": "solved", "concept_2": "hard_verified_achievable", "concept_3": "solved"},
        "current_scores": {
            "concept_1": {"baseline": baseline_gl, "private_solver": privileged_gl, "fresh_champion": final_gl},
            "concept_2": {"baseline": spectral_state["baseline"], "private_witness": spectral_state["privileged_witness"],
                          "fresh_attempts": [attempt["score"] for attempt in attempts if attempt["concept"] == "concept_2" and attempt["generation"] == 3]},
            "concept_3": {"baseline": baseline_tomography, "fresh_champion_repaired_evaluation": champion_tomography}
        },
        "counterexample_search_reports": ["concept_1/adversary/ratchet_1/REPORT.md", "concept_1/adversary/ratchet_2/REPORT.md",
                                          "concept_1/adversary/ratchet_2/PARENT_REVIEW.md",
                                          "concept_2/adversary/ratchet_1/REPORT.md", "concept_2/adversary/ratchet_2/REPORT.md",
                                          "concept_3/adversary/ratchet_1/GOAL_PACKET.json"],
        "failed_capability": spectral_state["failure_capability"],
        "integrity_checks": integrity_counts, "unit_tests": tests,
        "public_spectral_targets": target_keys, "isolation_validation": "authoring/isolation_validation.json",
        "report": "FINAL_REPORT.md", "release_manifest": "release_manifest.json",
        "qualification": "Empirical finite-budget hardness, not a proof of computational complexity. All reduced-model assumptions are declared in the participant packets."
    }
    save("status.json", state)
    rows = []
    for generation in (1, 2):
        history = gl_state["generation_history"][generation - 1]
        rows.append("| GL optimization — A | {} | {} | {} | {} | solved |".format(generation, pair(history["baseline"]), pair(history["private_in_budget"]), pair(history["fresh"])))
    for generation in (1, 2, 3):
        packet = "concept_2" if generation == 3 else "concept_2/champions/generation_" + str(generation)
        fresh = [pair(attempt["score"]) for attempt in attempts if attempt["concept"] == "concept_2" and attempt["generation"] == generation]
        rows.append("| BdG inclusion design — C | {} | {} | {} | {} | {} |".format(generation, pair(score(packet + "/evaluator/hidden/baseline_score.json")), pair(score(packet + "/evaluator/hidden/feasible_score.json")), "; ".join(fresh), "hard_verified_achievable" if generation == 3 else "solved"))
    rows.append("| LDOS active tomography — E | 1 | {} | {} | {} | solved |".format(pair(baseline_tomography), pair(champion_tomography), pair(champion_tomography)))
    report = """# Final hardness report

## Concepts and scores

Three concepts were built in modes **A, C, E**. The GL and BdG models are declared
mesoscopic superconductivity surrogates, not reproductions of native SuperConga.
All score pairs are **core / worst family or operating condition**.

| Concept / mode | Task generation | Baseline | Private feasible solver/design or champion | Fresh ultima-alpha | Decision |
| --- | ---: | --- | --- | --- | --- |
""" + "\n".join(rows) + """

The fixed targets are GL **0.65 / 0.45**, spectral design **0.96 / 0.94**,
and tomography **0.70 / 0.50** plus its reconstruction-quality gates.
Eight isolated, ephemeral fresh sessions received participant-only access and
initially empty outputs, each with a 3600-second limit. All exited normally.
The two final spectral trials used 3586.70 and 3534.77 seconds; both artifacts
were fabrication-valid and written before their deadlines.

The final GL champion takes 36.39–56.89 seconds per case, below 60 seconds.
Tomography's corrected champion has mean CPU 14.28 seconds and maximum 48.26,
below 90 seconds; correcting process-tree CPU accounting did not change its
perfect quality score. The retained spectral witness verifies in under one second.

## Counterexample search

- **GL:** the first 24-case sweep isolated six persistent collective-winding
  gaps; three became generation 2. The old champion's two warm core scores were
  0.0688 and approximately zero. The new fresh solver scores 1/1. A subsequent
  bounded 13-case replay from a preserved 24-case corpus used 21 solver launches:
  eight cases closed their gaps, two showed stationary vortex-pinning gaps,
  and three hit resource deadlines. The declared repeat-load qualification
  was inconclusive. The two pinning regressions nevertheless survive six normal
  repeats with ample unused budget, so time truncation does not explain them.
  Previously recorded generation-1 champion fields close 0.9539 and 0.7981 of
  these gaps, leaving only 0.0554 and 0.1103 energy units. This is previously
  demonstrated capability, not a promising novel hard target. Historical initial
  arrays differ, so no new exact-input runtime qualification is claimed.
  No third generation was installed, and no broad-robustness claim is made.
- **Spectral:** the first ratchet screened 15 physical cases in 62 runs;
  the selected old-champion score was 0.0700/0.0586, but both new fresh agents
  solved generation 2. The second ratchet screened 19 cases including controls.
  Its full-strength selected-case replay completed 48 six-stage continuation
  seeds plus 24 auxiliary fits: 71,948 function evaluations and 60,341 CPU-seconds,
  with no pass. Best fabrication-valid champion score was 0.2942/0.2812.
  The generation-2 control still solved; matched smaller-island and fourfold
  spectral-grid refinement controls supported a genuine inverse-design gap.
  One incomplete large-geometry screen was not counted as a failed run.
- **Tomography:** 183 isolated review episodes included a 96-case broad sweep
  with 91 successes. Candidate failures did not survive unchanged replay;
  reduced-query controls also failed to establish a harder generation.

## Ratchet generations

Installed ratchets: **GL 1; spectral 2; tomography 0**.
Corresponding task generations: **2, 3, 1**. No concept exceeds the generation cap.

## Final status and solvability

**Retain `concept_2` as `hard_verified_achievable`.** Its private fabrication-feasible
design independently scores essentially 1/1, while two fresh one-hour attempts
remain at 0.5736/0.5196 and 0.5604/0.5314 against 0.96/0.94 targets.
Solvability is **demonstrated**, not unknown. GL and tomography remain **solved**
on their frozen official tasks; broader inconclusive searches do not change that.

## Substantive failed capability

Global binary inverse spectral design: recovering a connected-superconductor,
exact-material-budget pattern whose interacting inclusion resonances reproduce
all three public fingerprints. The failures are large spectral errors, not
missing files, hidden trivia, malformed artifacts, or infrastructure timeouts.
This is empirical one-hour hardness, not an impossibility or complexity proof.
"""
    (ROOT / "FINAL_REPORT.md").write_text(report)
    release_files = {}
    for concept_name in ("concept_1", "concept_2", "concept_3"):
        for directory in ("participant", "evaluator"):
            for path in sorted((ROOT / concept_name / directory).rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts:
                    release_files[str(path.relative_to(ROOT))] = digest(path)
        release_files[concept_name + "/status.json"] = digest(ROOT / concept_name / "status.json")
    for relative in ("status.json", "FINAL_REPORT.md", "README.md", "authoring/provenance.json", "authoring/concept_selection.md"):
        release_files[relative] = digest(ROOT / relative)
    for relative in state["counterexample_search_reports"]:
        release_files[relative] = digest(ROOT / relative)
    release_files["concept_1/adversary/ratchet_2/parent_review.json"] = digest(parent_review)
    for attempt in attempts:
        for suffix in ("launch", "exit", "evaluation"):
            relative = attempt["concept"] + "/attempts/" + attempt["label"] + "." + suffix + ".json"
            release_files[relative] = digest(ROOT / relative)
    save("release_manifest.json", {"created_utc": now, "files": release_files,
                                   "file_count": len(release_files), "scope": "Final participant/evaluator packets, decisions, provenance and fresh-attempt records; private search logs remain separately archived."})
    print(json.dumps({"status": state["status"], "retained": state["retained_concepts"],
                      "fresh_sessions": len(attempts), "tests": sum(test["count"] for test in tests.values()),
                      "release_files": len(release_files)}, indent=2))


if __name__ == "__main__":
    main()
