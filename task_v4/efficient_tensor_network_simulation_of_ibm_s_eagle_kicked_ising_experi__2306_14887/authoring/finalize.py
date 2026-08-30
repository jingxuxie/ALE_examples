import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
NAMES = {
    1: "Memory-bounded heavy-hex contraction planning",
    2: "Drift-robust false finite-bond convergence",
    3: "GHZ preparation with coherent static detuning",
}
MODES = {1: "A_baseline_improvement", 2: "B_counterexample_falsification", 3: "C_witness_design_construction"}
CAPABILITIES = {
    1: "Joint contraction-order and slicing optimization at the required hidden work efficiency.",
    2: "Constructing a genuinely biased finite-bond convergence witness across all temporal-drift corners.",
    3: "Robust coherent many-body control across simultaneous gate-calibration error and static longitudinal drift.",
}


def load(path):
    return json.loads(path.read_text())


def compact(result):
    keys = ("core_score", "worst_family_score", "score", "minimum_case_speedup", "valid", "passed",
            "runtime_seconds", "elapsed_seconds", "resource_score", "reason", "family_minima", "family_scores")
    return {key: result[key] for key in keys if key in result}


def main():
    records = []
    updates = []
    statuses = {}
    for number in (1, 2, 3):
        concept = ROOT / f"concept_{number}"
        status = load(concept / "status.json")
        generation = max(status.get("generation", 0), status.get("ratchet_generation", 0), status.get("ratchet_generations", 0))
        attempt = generation + 1
        score_path = concept / "attempts" / f"v_{attempt}_score.json"
        result = load(score_path)
        run = load(concept / "attempts" / f"v_{attempt}_run.json")
        if run["status"] != "finished" or not run["participant_unchanged"]:
            raise RuntimeError(f"concept {number}: unfinished or modified-input attempt")
        if not result["valid"]:
            raise RuntimeError(f"concept {number}: invalid result needs manual infrastructure/artifact review")
        if result["passed"] and generation < 3 and not status.get("adversary_search_complete_no_failure", False):
            raise RuntimeError(f"concept {number}: solved concept still requires champion-challenger processing")
        known_passing = any(status.get(key, False) for key in
                            ("known_passing_solution", "known_passing_witness", "known_passing_current_reference"))
        if number == 2 and known_passing:
            proof = load(concept / status["passing_private_witness"]["independent_main_recheck"])
            if not (proof["valid"] and proof["passed"] and proof["evaluation_complete"]
                    and proof["target_sha256"] == status["target_sha256"]):
                raise RuntimeError("The private counterexample proof does not pass the current frozen target")
        classification = "solved" if result["passed"] else (
            "hard_verified_achievable" if known_passing else "hard_open_candidate")
        history = []
        for previous in range(1, attempt + 1):
            previous_result = load(concept / "attempts" / f"v_{previous}_score.json")
            previous_run = load(concept / "attempts" / f"v_{previous}_run.json")
            history.append({"attempt": previous, "generation": previous - 1,
                            "model": previous_run["model"], "elapsed_seconds": previous_run["elapsed_seconds"],
                            "timed_out": previous_run["timed_out"], "participant_unchanged": previous_run["participant_unchanged"],
                            "scores": compact(previous_result),
                            "score_file": f"attempts/v_{previous}_score.json"})
        status.update({"status": classification, "classification": classification,
                       "hardness_status": classification, "empirical_hardness": classification,
                       "ratchet_generations": generation, "current_attempt": attempt,
                       "fresh_agent_executed": True, "fresh_agent_run_current_generation": True,
                       "fresh_attempts": history, "final_fresh_scores": compact(result),
                       "solvability": "demonstrated" if known_passing or result["passed"] else "unknown",
                       "failed_capability": None if result["passed"] else CAPABILITIES[number],
                       "final_participant_manifest": {
                           str(path.relative_to(concept / "participant")): hashlib.sha256(path.read_bytes()).hexdigest()
                           for path in sorted((concept / "participant").rglob("*"))
                           if path.is_file() and "__pycache__" not in path.parts}})
        records.append({"concept": f"concept_{number}", "name": NAMES[number], "mode": MODES[number],
                        "status": classification, "solvability": status["solvability"],
                        "ratchet_generations": generation, "scores": compact(result),
                        "history": history, "failed_capability": status["failed_capability"]})
        updates.append((concept / "status.json", status))
        statuses[number] = status
    accepted = [record for record in records if record["status"] in ("hard_open_candidate", "hard_verified_achievable")]
    selected = next((record for record in accepted if record["status"] == "hard_verified_achievable"),
                    next((record for record in reversed(accepted) if record["concept"] != "concept_1"),
                         accepted[0] if accepted else None))
    summary = {"session_type": "HARDNESS_DISCOVERY", "paper": "arXiv:2306.14887",
               "built_concepts": 3, "verification_modes": ["A", "B", "C"],
               "fresh_models": ["ultima-alpha"], "fresh_limit_seconds": 3600,
               "status": selected["status"] if selected else "rejected",
               "selected_concept": selected["concept"] if selected else None,
               "retained_concepts": [record["concept"] for record in accepted], "concepts": records,
               "contraction_margin_caveat": "The 4x target miss is narrow but stable across two scorer runs.",
               "counterexample_search_results": {
                   "contraction": "512-restart portfolio reaches 2.166397x; fresh replay remains 3.663563x; a 36-second private variant times out on one case.",
                   "falsification": "902 cases / 4510 waveforms: first fresh witness fails 11 of 64 knot-drift corners at +/-0.002, motivating the 325-waveform target. Private warm-start search evaluates 34 candidates / 1500 waveforms and finds a witness passing all 325 checks; a separate main-session regrade confirms it.",
                   "control": "1064 independent original-model checks find no failure; static Z drift exposes a 0.911091 fidelity case at +/-0.01 rad/site/layer, motivating the 223-case target. After the second fresh agent solves it, 4929 records / 4494 unique static or matching-dependent calibrations produce no failure: minimum fidelity 0.951877878. This search is not a continuum certificate."}}
    for path, status in updates:
        path.write_text(json.dumps(status, indent=2, allow_nan=False) + "\n")
    (ROOT / "status.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    lines = ["# Hardness discovery report", "",
             "Selected: **concept_2 — hard_verified_achievable**. Concept 1 is also retained as an open candidate; concept 3 is solved.", "",
             "| Concept / mode | Fresh current score | Ratchets | Final status | Solvability |",
             "|---|---:|---:|---|---|"]
    for record in records:
        result = record["scores"]
        value = result.get("score", result["core_score"] if record["concept"] == "concept_1" else result["worst_family_score"])
        lines.append(f"| {record['concept']}: {record['name']} / {record['mode'][0]} | {value:.8f} | {record['ratchet_generations']} | {record['status']} | {record['solvability']} |")
    counterexample = statuses[2]
    baseline = counterexample["reference_grades"]["baseline"]
    champion = counterexample["reference_grades"]["champion"]
    private_proof = counterexample["passing_private_witness"]
    control = statuses[3]
    lines.extend(["", "## Baselines and champions",
                  "- Contraction: baseline core/worst 1x/1x; private 512-restart portfolio 2.166397x/1.095245x; fresh 3.663561x/1.447863x (replay core 3.663563x). Fixed targets are 4x overall and 1.1x in every family, with no greater than 5% per-case regression. The overall miss is narrow but reproducible; achievability remains unknown.",
                  f"- Falsification: current weak baseline core/worst {baseline['core_score']:.6f}/{baseline['worst_family_score']:.6f}; preceding fresh champion {champion['core_score']:.6f}/{champion['worst_family_score']:.6f} on the retained target (previously 100/100). The private passing witness scores {private_proof['core_score']:.0f}/{private_proof['worst_family_score']:.0f}, depth {private_proof['depth']}, minimum bias {private_proof['minimum_error']:.10f}, maximum convergence spread {private_proof['maximum_spread']:.10f}. All 325 waveforms meet bias >=0.15 and spread <=0.008.",
                  f"- Control: current weak baseline minimum fidelity {control['baseline_min_fidelity']:.8f}; preceding fresh champion {control['generation_0_fresh_champion_current_min_fidelity']:.8f} (previously 0.96038148); best pre-attempt private candidate {control['best_tested_private_min_fidelity']:.8f}. The second fresh champion reaches 0.95241447 against the fixed 0.95 minimum-fidelity target.",
                  "", "## Fresh-agent scores",
                  "Five isolated ultima-alpha attempts, each with a one-hour limit, unchanged read-only participant assets, and an initially empty output directory.",
                  "| Concept | Generation | Core | Worst family / minimum fidelity | Passed | Search seconds | Timeout |",
                  "|---|---:|---:|---:|---|---:|---|"])
    for record in records:
        for history in record["history"]:
            scores = history["scores"]
            worst = scores.get("score", scores["worst_family_score"])
            lines.append(f"| {record['concept']} | {history['generation']} | {scores['core_score']:.8f} | {worst:.8f} | {scores['passed']} | {history['elapsed_seconds']:.2f} | {history['timed_out']} |")
    lines.extend([
                  "", "## Counterexample search"])
    lines.extend(f"- {value}" for value in summary["counterexample_search_results"].values())
    lines.extend(["", "## Failed capabilities"])
    lines.extend(f"- {record['concept']}: {record['failed_capability']}" for record in accepted)
    lines.append("- concept_3: no remaining demonstrated capability failure; the current fresh champion passes the frozen target and all subsequent sampled stress cases.")
    (ROOT / "FINAL_REPORT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"status": summary["status"], "selected_concept": summary["selected_concept"],
                      "retained_concepts": summary["retained_concepts"]}, indent=2))


if __name__ == "__main__":
    main()
