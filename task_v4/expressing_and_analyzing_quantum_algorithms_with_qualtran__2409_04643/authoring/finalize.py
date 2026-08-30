import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from audit_package import assert_finite

ROOT = Path(__file__).resolve().parents[1]
NAMES = {1: "Resource-aware bloq scheduling", 2: "Compact silent GQSP failure", 3: "Compact coherent lookup synthesis"}
MODES = {1: "A: baseline improvement", 2: "B: counterexample/falsification", 3: "C: witness/design construction"}
CAPABILITIES = {
    1: "Optimizing weighted live-register frontiers while preserving every DAG dependency.",
    2: "Constructing a dense low-degree polynomial with robust all-configuration compiler instability, while certifying global contraction, accurate completion, and nonzero phase guards.",
    3: "Recovering shared nonlinear structure from complete truth tables and synthesizing exact low-AND, low-depth, compact-affine networks under clean-workspace caps.",
}


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def summary(score):
    keys = ("core_score", "worst_family_score", "worst_case_score", "correctness_score",
            "resource_score", "minimum_rms_error", "degree", "admissible", "valid", "passed",
            "runtime_seconds", "reason")
    return {key: score[key] for key in keys if key in score}


def attempt_summary(record):
    result = {key: record[key] for key in ("attempt_index", "generation", "model", "elapsed_seconds",
                                         "timed_out", "returncode", "participant_unchanged", "artifact_sha256")}
    result.update(summary(record["score"]))
    result["score_file"] = f"concept_{record['concept']}/adversary/run_v_{record['attempt_index']}/score.json"
    return result


def evaluate_witness(concept, submission, label):
    output = concept / "adversary" / f"final_{label}_score.json"
    environment = os.environ.copy()
    environment.update({"OPENBLAS_NUM_THREADS": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    result = subprocess.run([sys.executable, str(concept / "evaluator/evaluate.py"),
                             "--submission", str(submission), "--report", str(output)],
                            capture_output=True, text=True, env=environment, check=True, timeout=75)
    score = read(output)
    assert_finite(score)
    return {"artifact_directory": str(submission.relative_to(ROOT)),
            "score_file": str(output.relative_to(ROOT)), "score": summary(score)}


def main():
    audit = read(ROOT / "authoring/package_audit.json")
    if not audit["passed"] or not audit["completed"]:
        raise SystemExit("a successful completed package audit is required")
    registry = read(ROOT / "authoring/attempt_registry.json")
    if any(not record["completed"] for record in registry if not record.get("excluded")):
        raise SystemExit("do not finalize active attempts")
    records = []
    for index in (1, 2, 3):
        concept = ROOT / f"concept_{index}"
        status = read(concept / "status.json")
        generation = status["generation"]
        attempts = [record for record in registry if record["concept"] == index and not record.get("excluded")]
        current = [record for record in attempts if record["generation"] == generation]
        if not current:
            raise SystemExit("every final generation requires a completed fresh attempt")
        baseline = next(record["score"] for record in audit["baselines"] if record["concept"] == index)
        witness = None
        if index == 1:
            if generation != 2:
                raise SystemExit("review private scheduling witness selection after another ratchet")
            witness = evaluate_witness(concept, concept / "adversary/generation_2_witness", "private_witness")
        elif index == 3:
            witness = evaluate_witness(concept, concept / "adversary/private_witness", "private_witness")
        else:
            candidates = list((concept / "adversary/final_compact_refinement").glob("seed_*/score.json"))
            if candidates:
                best_path = max(candidates, key=lambda path: read(path).get("minimum_rms_error", 0))
                witness = evaluate_witness(concept, best_path.parent, "private_best_candidate")
        fresh_pass = any(record["score"]["passed"] for record in current)
        if index == 3 and fresh_pass:
            raise SystemExit("a solved design task requires champion stress/ratchet before finalizing")
        private_pass = bool(witness and witness["score"]["passed"])
        final_status = "solved" if fresh_pass else "hard_verified_achievable" if private_pass else "hard_open_candidate"
        champions = []
        for historical_generation in sorted({record["generation"] for record in attempts}):
            cohort = [record for record in attempts if record["generation"] == historical_generation]
            winner = max(cohort, key=lambda record: (record["score"]["passed"], record["score"]["core_score"],
                                                    record["score"].get("minimum_rms_error", 0)))
            if winner["score"]["passed"]:
                destination = concept / "champions" / f"generation_{historical_generation}"
                if not destination.exists():
                    shutil.copytree(concept / "attempts" / f"v_{winner['attempt_index']}", destination)
                champions.append({"generation": historical_generation,
                                  "attempt_index": winner["attempt_index"],
                                  "score": summary(winner["score"]),
                                  "directory": str(destination.relative_to(ROOT))})
            archive = concept / "adversary/generations" / f"generation_{historical_generation}" / "status.json"
            if archive.exists():
                archived = read(archive)
                archived.update({"status": "solved", "hardness_decision": "solved", "phase": "archived_after_champion_ratchet",
                                 "fresh_attempts": [attempt_summary(record) for record in cohort],
                                 "solvability": "demonstrated_by_fresh_agent"})
                write(archive, archived)
        status.update({"status": final_status, "final_status": final_status, "hardness_decision": final_status,
                       "phase": "complete", "baseline": summary(baseline),
                       "fresh_attempts": [attempt_summary(record) for record in current],
                       "champions": champions, "privileged_evidence": witness,
                       "solvability": "demonstrated" if fresh_pass or private_pass else "unknown",
                       "retained": final_status.startswith("hard_"),
                       "substantive_capability": CAPABILITIES[index],
                       "hardness_scope": "Empirical ultima-alpha attempts under a one-hour construction budget; not a proof of universal computational hardness."})
        if index == 1:
            stress = read(concept / "adversary/stress_generation_2/report.json")
            if stress["core_gain"] >= 1.06 and stress["minimum_case_gain"] >= 1.02:
                raise SystemExit("a qualifying scheduling gap was found; complete its ratchet before finalizing")
            status["counterexample_search"] = {
                "first_champion": "adversary/stress_generation_1/report.json",
                "second_champion": "adversary/stress_generation_2/report.json",
                "second_champion_trials": stress["trials"],
                "second_champion_core_gain": stress["core_gain"],
                "second_champion_maximum_case_gain": stress["maximum_case_gain"],
                "stop_reason": "The fresh agent solved the focused ratchet; the final continuation sweep did not find another gap meeting the fixed 1.06 geometric-mean and 1.02 every-case criterion."}
        elif index == 2:
            refinement = read(concept / "adversary/final_compact_refinement/report.json")
            status["counterexample_search"] = {
                "degree_8_to_14_original_champion_trials": 35000,
                "directed_champion_trials_degrees_8_10_12_13": 40000,
                "final_degree_12_refinement_trials": refinement["total_trials"],
                "final_private_minimum_rms_error": refinement["best_minimum_rms_error"],
                "prior_degree_14_and_48_witnesses_do_not_prove_current_solvability": True,
                "stop_reason": "Three task generations reached; current degree-8-through-12 target remains fixed."}
        else:
            status["counterexample_search"] = {
                "negative_checker_tests": 30, "positive_full_row_checks": 14336,
                "private_designs": 6,
                "root_cause": "Fresh construction meets the target." if fresh_pass else
                              "Fresh networks reproduce the tables but do not satisfy the compact shared nonlinear resource bounds."}
        write(concept / "status.json", status)
        records.append({"concept": index, "name": NAMES[index], "verification_mode": MODES[index],
                        "task": f"concept_{index}/participant/TASK.md", "generation": generation,
                        "ratchet_generations": status["ratchet_generations"],
                        "status": final_status, "solvability": status["solvability"],
                        "baseline": summary(baseline), "champions": champions,
                        "fresh_attempts": status["fresh_attempts"], "privileged_evidence": witness,
                        "counterexample_search": status["counterexample_search"],
                        "substantive_capability": CAPABILITIES[index]})
    accepted = [record for record in records if record["status"].startswith("hard_")]
    verified = [record for record in accepted if record["status"] == "hard_verified_achievable"]
    selected = (verified or accepted or [None])[0]
    report = {"paper": {"title": "Expressing and Analyzing Quantum Algorithms with Qualtran", "arxiv": "2409.04643"},
              "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "model": "ultima-alpha", "construction_limit_seconds": 3600,
              "timeout_cleanup_grace_seconds": 10,
              "concepts_screened": 10, "concepts_built": 3,
              "concepts": records, "accepted_hard_concepts": [record["concept"] for record in accepted],
              "selected_concept": selected["concept"] if selected else None,
              "final_status": selected["status"] if selected else "rejected",
              "solvability": selected["solvability"] if selected else "not_applicable",
              "excluded_infrastructure_runs": [record for record in registry if record.get("excluded")],
              "audit": "authoring/package_audit.json",
              "independent_audits": ["authoring/audits/concept_2_audit.json", "authoring/audits/concept_3_audit.json"],
              "validation_limits": "authoring/VALIDATION.md"}
    write(ROOT / "status.json", report)
    write(ROOT / "report.json", report)
    print(json.dumps({"selected_concept": report["selected_concept"],
                      "final_status": report["final_status"],
                      "concept_statuses": {record["concept"]: record["status"] for record in records}}, indent=2))


if __name__ == "__main__":
    main()
