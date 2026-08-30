import datetime
import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_3"
PACKET = CONCEPT / "adversary/generation_2_packet"


def load(path):
    return json.loads(path.read_text())


def main():
    attempts = []
    for label in ("v_2", "v_2_r2"):
        score = load(CONCEPT / "attempts" / (label + ".score.json"))
        finished = load(CONCEPT / "attempts" / (label + ".exit.json"))
        assert not score["pass"] and score["cases"]
        assert finished["timed_out"] and finished["wall_seconds"] >= 3600
        assert all(case["gate_count"] <= case["max_gates"] for case in score["cases"])
        attempts.append({"attempt": label, "passed": False, "core_score": score["core"],
                         "worst_family_score": score["worst_fidelity"], "cases": score["cases"],
                         "wall_seconds": finished["wall_seconds"], "timed_out": True,
                         "score_file": "attempts/" + label + ".score.json"})
    witness = load(PACKET / "adversary/main_certificate_recheck.json")
    independent = load(PACKET / "adversary/main_independent_audit.json")
    negative_controls = load(PACKET / "adversary/report.json")
    assert witness["pass"] and independent["pass"] and negative_controls["pass"]
    manifest = load(PACKET / "evaluator/private/frozen_manifest.json")
    for relative, expected in manifest["participant_sha256"].items():
        assert hashlib.sha256((PACKET / "participant" / relative).read_bytes()).hexdigest() == expected
    archive = CONCEPT / "adversary/generation_1_live_archive"
    if not archive.exists():
        archive.mkdir()
        for name in ("participant", "evaluator"):
            (CONCEPT / name).rename(archive / name)
            shutil.copytree(PACKET / name, CONCEPT / name)
        shutil.copy2(CONCEPT / "status.json", archive / "status.json")
    for name in ("participant", "evaluator"):
        for path in (PACKET / name).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                assert (CONCEPT / name / path.relative_to(PACKET / name)).read_bytes() == path.read_bytes()
    baseline = load(PACKET / "attempts/baseline_score.json")
    shutil.copy2(PACKET / "attempts/baseline_score.json", CONCEPT / "attempts/generation_2_baseline_score.json")
    status = {
        "concept_id": "concept_3", "verification_mode": "C_witness_construction",
        "generation": 2, "ratchet_generations": 1, "status": "hard_verified_achievable",
        "decided_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "active_packet": ".", "tested_packet": "adversary/generation_2_packet",
        "mission": "Compact spin-preserving fermionic excitation-circuit synthesis",
        "target": {"minimum_fidelity_every_case": 0.999999999, "gate_caps": [24, 28, 32]},
        "baseline_core_score": baseline["core"], "private_witness_core_score": witness["core"],
        "fresh_model": "ultima-alpha", "fresh_limit_seconds": 3600, "fresh_attempts": attempts,
        "solvability": "demonstrated_by_private_exact_circuits_and_independent_matrix_audit",
        "reason": "Both isolated full-hour attempts produce valid capped circuits but fail every fidelity target.",
        "substantive_capability": "Joint discrete excitation/order discovery and continuous-angle optimization after sparse-support and rank-drop cues disappear.",
        "generation_1_fresh_scores": [1.0, 0.9999999999999998],
        "champion_archive": "champions/generation_1",
        "counterexample_search": {"private_pool_cases": 18, "broad_seconds_per_case": 60,
                                  "deep_seconds_per_finalist": 300, "selected_failures": 3,
                                  "bounded_champion_worst_fidelity": 0.837040769743351,
                                  "full_hour_champion_failure_claimed": False,
                                  "extended_original_controls_reproduced": "2 of 3; bounded portability is partial"},
        "certificate": "evaluator/private/certificates.json",
        "main_certificate_recheck": "adversary/generation_2_packet/adversary/main_certificate_recheck.json",
        "main_independent_audit": "adversary/generation_2_packet/adversary/main_independent_audit.json",
        "frozen_manifest": "evaluator/private/frozen_manifest.json",
        "evaluator_valid": True, "frozen_target_unchanged_during_attempts": True,
    }
    (CONCEPT / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps({key: status[key] for key in ("status", "generation", "ratchet_generations", "solvability")}))


if __name__ == "__main__":
    main()
