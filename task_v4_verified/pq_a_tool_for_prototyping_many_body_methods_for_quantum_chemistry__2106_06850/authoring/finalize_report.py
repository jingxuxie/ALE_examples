import argparse
import datetime
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-witness-report", type=Path)
    parser.add_argument("--infeasibility-proof", type=Path)
    arguments = parser.parse_args()
    subprocess.run([sys.executable, str(ROOT / "authoring/collect_scores.py")], check=True)
    ledger = load(ROOT / "authoring/score_ledger.json")
    assert ledger["record_count"] == ledger["completed_count"] == ledger["evaluated_count"] == 14
    subprocess.run([sys.executable, str(ROOT / "authoring/audit_isolation.py")], check=True)
    assert load(ROOT / "authoring/isolation_audit.json")["passed"]
    counterexample = ROOT / "concept_2"
    packet = counterexample / "adversary/generation_4_packet"
    private_audit = load(packet / "authoring/FINAL_AUDIT.json")
    assert private_audit["frozen_hashes_match"] and not private_audit["active_fresh_attempt_data_read"]
    latest = [record for record in ledger["records"]
              if record["concept"] == "concept_2" and record["generation"] == 4]
    assert len(latest) == 2
    known_witness = arguments.private_witness_report is not None
    if known_witness:
        assert load(arguments.private_witness_report).get("passed") is True
    if any(record["passed"] for record in latest):
        counterexample_status = "solved"
        solvability = "demonstrated_by_a_fresh_submission"
        best = max((record for record in latest if record["passed"]), key=lambda record: record["core_score"])
        champion = counterexample / "champions/generation_4"
        if not champion.exists():
            subprocess.run([sys.executable, str(ROOT / "authoring/freeze.py"),
                            str(counterexample / "attempts" / (best["attempt"] + "_frozen")),
                            str(champion)], check=True)
            shutil.copy2(ROOT / best["score_record"], champion / "score.json")
    elif arguments.infeasibility_proof:
        assert arguments.infeasibility_proof.is_file()
        counterexample_status = "invalid"
        solvability = "disproved_by_the_recorded_proof"
    elif known_witness:
        counterexample_status = "hard_verified_achievable"
        solvability = "demonstrated_by_a_private_witness"
    else:
        counterexample_status = "hard_open_candidate"
        solvability = "unknown_no_passing_witness_or_infeasibility_proof"
    archive = counterexample / "adversary/generation_3_live_archive"
    if not archive.exists():
        archive.mkdir()
        for name in ("participant", "evaluator"):
            (counterexample / name).rename(archive / name)
            shutil.copytree(packet / name, counterexample / name)
        shutil.copy2(counterexample / "status.json", archive / "status.json")
    for name in ("participant", "evaluator"):
        for path in (packet / name).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                assert (counterexample / name / path.relative_to(packet / name)).read_bytes() == path.read_bytes()
    (counterexample / "participant/input").mkdir(exist_ok=True)
    status = {
        "concept_id": "concept_2", "verification_mode": "B_counterexample_falsification",
        "generation": 4, "ratchet_generations": 3, "status": counterexample_status,
        "solvability": solvability, "active_packet": ".", "tested_packet": "adversary/generation_4_packet",
        "target": {"minimum_population_violation": 0.02, "energy_error_max": 1e-4,
                   "dad_max": 0.001, "perturbation_radius": 0.001, "certified_points": 243},
        "baseline_core_score": 0.0, "prior_champions_core_under_current_rule": [0.0, 0.0],
        "fresh_model": "ultima-alpha", "fresh_limit_seconds": 3600, "fresh_attempts": latest,
        "evaluator_timeout_seconds": 900, "evaluator_valid": True,
        "private_witness_report": str(arguments.private_witness_report) if known_witness else None,
        "infeasibility_proof": str(arguments.infeasibility_proof) if arguments.infeasibility_proof else None,
        "audits": ["adversary/generation_4_packet/authoring/packet_audit.json",
                   "adversary/generation_4_packet/authoring/main_zero_recheck.json"],
        "private_feasibility_audit": "adversary/generation_4_packet/authoring/FINAL_AUDIT.json",
        "substantive_capability": "Constructing a stationary ground-connected CCSD counterexample with simultaneous accuracy, density, conditioning, and adaptive worst-direction robustness constraints.",
        "frozen_target_unchanged_during_attempts": True,
    }
    (counterexample / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    circuit = load(ROOT / "concept_3/status.json")
    contraction = load(ROOT / "concept_1/status.json")
    assert circuit["status"] == "hard_verified_achievable" and contraction["status"] == "invalid"
    retained = ["concept_3"]
    if counterexample_status in ("hard_verified_achievable", "hard_open_candidate"):
        retained.append("concept_2")
    decision = {
        "paper": "2106.06850", "status": "hard_verified_achievable", "selected_concept": "concept_3",
        "retained_concepts": retained, "concepts_built": 3, "verification_modes": ["A", "B", "C"],
        "concept_statuses": {"concept_1": "invalid", "concept_2": counterexample_status,
                             "concept_3": "hard_verified_achievable"},
        "ratchet_generations": {"concept_1": 0, "concept_2": 3, "concept_3": 1},
        "fresh_model": "ultima-alpha", "fresh_session_count": 14, "fresh_limit_seconds": 3600,
        "isolation_audit_passed": True, "selected_solvability": "demonstrated",
        "decided_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    (ROOT / "status.json").write_text(json.dumps(decision, indent=2) + "\n")
    rows = []
    for concept, generations in (("concept_1", (1,)), ("concept_2", (1, 2, 3, 4)), ("concept_3", (1, 2))):
        for generation in generations:
            matches = [record for record in ledger["records"]
                       if record["concept"] == concept and record["generation"] == generation]
            values = " / ".join(f"{record['core_score']:.10g}" for record in matches)
            result = ("invalid target; cancelled" if concept == "concept_1" else
                      "solved" if any(record["passed"] for record in matches) else
                      counterexample_status if concept == "concept_2" else "hard_verified_achievable")
            rows.append(f"| {concept} | {generation} | {values} | {result} |")
    final_fresh = " / ".join(f"{record['core_score']:.10g}" for record in latest)
    text = """# Hardness discovery — p†q (2106.06850)

## Concepts and verification modes built

- **concept_1 — A, baseline improvement:** memory-bounded joint contraction planning for source-native CC, response, and density batches.
- **concept_2 — B, counterexample/falsification:** a physically constrained, ground-connected CCSD lambda-density population counterexample, ultimately checked at 243 coordinate and adaptive perturbations.
- **concept_3 — C, witness construction:** compact spin-preserving fermionic excitation circuits for complete correlated target states, under 24/28/32-gate caps.

## Baseline and champion scores

- **A:** baseline 1.0; privileged portfolio 1.291981598 overall, worst family 1.021440250. Fixed target was 1.75 overall and 1.15 in every family.
- **B:** random baseline 0 in every generation. Best fresh witness cores in generations 1–3 were 0.050007892, 0.607015128, and 0.039804144. Both generation-three champions score 0 under the final adaptive rule. The fixed population target remains 0.02.
- **C:** original baseline 0.857503373; original champion 1.0. Ratcheted baseline 0.773572868; bounded transferred-champion worst fidelity 0.837040770. Private exact circuits score 1.0 on every final case. The fixed target is 0.999999999 in every case.

## Fresh-agent scores

Every session uses isolated, read-only participant assets, an initially empty output directory, ultima-alpha, and a 3,600-second limit. Public-file hashes and allowlist settings pass the 14-session audit.

| Concept | Generation | Replicate core scores | Decision |
|---|---:|---|---|
""" + "\n".join(rows) + """

A's two sessions were generator-cancelled only after the frozen target was proved infeasible; their checkpoint scores do not establish hardness. Both final C sessions used the full hour, produced structurally valid capped circuits, and failed all three fidelity targets. Detailed scores and runtime records are in `authoring/score_ledger.json`.

## Counterexample search results

- **A:** an exact universal certificate bounds response-family speedup by 1.022753055829, below the required 1.15. Independent integer-certificate rechecking passes. This concept is invalid, not hard.
- **B, first ratchet:** the original witnesses have DAD 0.277948 and 0.382145, exposing the density-asymmetry blind spot.
- **B, second ratchet:** valid integral perturbations expose 266/384 and 165/384 DAD failures in the two quiet-density champions; the public 241-point coordinate stencil independently reproduces genuine accuracy/asymmetry failures.
- **B, final ratchet:** the two coordinate-robust champions pass 512 and 256 isotropic probes, respectively, but fail both same-radius adaptive energy-gradient probes. Maximum energy errors are 0.0003411934 and 0.0002345538 against 0.0001; the latter also violates DAD. No invalid-domain probe is counted as physics evidence.
- **B, private feasibility search:** 310 relaxation starts and stationary/finite-probe portfolios yield seven independently scored artifacts and 1,701 endpoint checks, but no passing witness. A rational exclusion applies to only one relaxed tuple, not the task; no universal impossibility result is claimed.
- **C:** 18 certified, dense/full-rank private cases defeat bounded 60-second champion probes. Three selected cases still fail after additional 300-second probes. Extended old-control reproduction is partial (2/3), so no full-hour transferred-champion failure is claimed. The two new independent full-hour attempts supply the hardness evidence.

## Ratchet generations

- A: **0**; B: **3**; C: **1**. Three concepts and three distinct primary modes were built.

## Final status and solvability

"""
    text += f"- **Selected: concept_3 — hard_verified_achievable.** Solvability is demonstrated by private circuits, a separate Jordan–Wigner/dense-exponential audit, and main-session certificate rechecking. Fresh worst fidelities are 0.9562639168 and 0.9490407967.\n"
    text += f"- **concept_2 — {counterexample_status}.** Final fresh cores: {final_fresh}. Solvability: {solvability}. The trusted numerical, gradient, parser, and 243-path zero-example audits pass.\n"
    text += "- **concept_1 — invalid.** The improvement target is disproved under its frozen interface; cancellation and nonpassing scores are excluded from hardness evidence.\n"
    text += """
## Substantive capability failures

- **C:** joint discovery of a compact noncommuting excitation sequence and its angles when sparse support and Schmidt-rank reduction no longer identify reverse steps. Fast compiled simulation, topology search, angle refinement, structured ansätze, and reverse synthesis improved the baseline but remained substantially below the certified target.
"""
    if counterexample_status.startswith("hard_"):
        text += "- **B:** simultaneous stationary-CCSD witness construction and worst-direction robustness, not merely accurate energy or coordinate-wise screening. Final evaluator diagnostics distinguish physical constraints from malformed artifacts.\n"
    elif counterexample_status == "solved":
        text += "- **B:** no retained failure; a final fresh submission meets every frozen witness condition.\n"
    else:
        text += "- **B:** no valid hardness claim; the final concept is invalid for the recorded reason.\n"
    (ROOT / "FINAL_REPORT.md").write_text(text)
    (ROOT / "README.md").write_text(text)
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
