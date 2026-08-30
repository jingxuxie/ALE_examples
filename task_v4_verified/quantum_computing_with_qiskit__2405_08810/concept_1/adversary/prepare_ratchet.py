import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

from generate_barriers import make_barrier
from generate import load_baseline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from phase_model import check


def main():
    focused = ROOT / "adversary" / "focused_barriers"
    score_paths = [ROOT / "adversary" / "scored" / "v_1" / "stress_score.json", focused / "champion_score.json"]
    deadline = time.monotonic() + 1200
    while not all(path.exists() for path in score_paths):
        if time.monotonic() > deadline:
            raise TimeoutError("wait for complete champion challenge-space scoring")
        time.sleep(5)
    reports = [json.loads(path.read_text()) for path in score_paths]
    if not all(report["valid"] for report in reports):
        raise ValueError("resource or semantic failure requires investigation before ratcheting")
    cases = json.loads((focused / "cases.json").read_text())
    witnesses = json.loads((focused / "witnesses.json").read_text())
    champion = reports[1]
    assert len(cases) == len(witnesses) == len(champion["cases"]) == 32
    targets = {"core_score": 0.82, "worst_family_score": 0.80}
    family_witnesses = {}
    gaps = []
    for case, witness, result in zip(cases, witnesses, champion["cases"]):
        assert case["id"] == witness["id"] == result["id"]
        metrics = check(case["input"], witness["circuit"])
        reduction = 1 - metrics["cost"] / case["baseline"]["cost"]
        family_witnesses.setdefault(case["family"], []).append(reduction)
        gaps.append({"id": case["id"], "family": case["family"], "champion_cost": result["cost"], "witness_cost": metrics["cost"], "residual_cost_improvement": 1 - metrics["cost"] / result["cost"]})
    witness_family_scores = {family: sum(values) / len(values) for family, values in family_witnesses.items()}
    witness_core = sum(sum(values) for values in family_witnesses.values()) / 32
    assert witness_core >= targets["core_score"] and min(witness_family_scores.values()) >= targets["worst_family_score"]
    assert champion["core_score"] < targets["core_score"] or champion["worst_family_score"] < targets["worst_family_score"]
    baseline = load_baseline()
    examples = []
    public_generation_record = []
    for family_index, family in enumerate(("lattice", "shared_dense")):
        for example_index in range(2):
            for trial in range(100):
                seed = 0xA429F04E19031 + family_index * 123733 + example_index * 170557 + trial * 12143
                example, witness = make_barrier(seed, family, 28, 14 + 2 * example_index, 8 + 16 * example_index)
                baseline_metrics = check(example, baseline.compile_circuit(example))
                witness_metrics = check(example, witness)
                if 1 - witness_metrics["cost"] / baseline_metrics["cost"] >= 0.82:
                    examples.append(example)
                    public_generation_record.append({"seed": seed, "circuit": witness, "metrics": witness_metrics})
                    break
            else:
                raise ValueError("public examples need independently certified headroom")
    hidden = ROOT / "evaluator" / "hidden"
    shutil.copy2(focused / "cases.json", hidden / "cases.json")
    shutil.copy2(focused / "witnesses.json", hidden / "generation_witnesses.json")
    (hidden / "targets.json").write_text(json.dumps(targets, indent=2) + "\n")
    (ROOT / "participant" / "input" / "examples.jsonl").write_text("".join(json.dumps(example) + "\n" for example in examples))
    (ROOT / "participant" / "input" / "targets.json").write_text(json.dumps(targets, indent=2) + "\n")
    ratchet = ROOT / "adversary" / "ratchet_1"
    ratchet.mkdir(exist_ok=False)
    (ratchet / "public_example_witnesses.json").write_text(json.dumps(public_generation_record, separators=(",", ":")) + "\n")
    counterexamples = sorted(gaps, key=lambda item: item["residual_cost_improvement"], reverse=True)
    record = {
        "ratchet_generation": 1,
        "fixed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "targets": targets,
        "baseline": "unchanged original public compiler portfolio; champion source remains private",
        "old_champion_original_core": 0.6357079703817478,
        "old_champion_focused_core": champion["core_score"],
        "old_champion_focused_worst_family": champion["worst_family_score"],
        "old_champion_focused_family_scores": champion["family_scores"],
        "witness_core": witness_core,
        "witness_family_scores": witness_family_scores,
        "mean_normalized_cost_reduction_required_from_champion": 1 - (1 - targets["core_score"]) / (1 - champion["core_score"]),
        "broad_search_cases": len(reports[0]["cases"]),
        "initial_basis_screen_cases": 24,
        "focused_search_cases": 32,
        "witness_beats_champion_cases": sum(item["residual_cost_improvement"] > 0 for item in gaps),
        "counterexamples": counterexamples,
        "root_cause_cluster": "term-first local parity actions fail to amortize deferred native basis setup across correlated rotations; weak support-count lookahead and restore-only basis synthesis",
        "selection": "All 32 headroom-filtered focused candidates retained, not just individual champion failures. Two balanced physical graph families. Exact planted circuits certify cost headroom; no submitted compiler must recover a specific circuit or factorization.",
        "solvability": "general passing compiler unknown; private per-instance construction witnesses are not a generic solver",
        "cases_sha256": hashlib.sha256((hidden / "cases.json").read_bytes()).hexdigest(),
    }
    (ratchet / "commitment.json").write_text(json.dumps(record, indent=2) + "\n")
    (ROOT / "status.json").write_text(json.dumps({"concept": "hardware_aware_phase_compilation", "verification_mode": "A", "status": "ratchet_ready_pending_fresh", "ratchet_generations": 1, "target": targets, "baseline_score": 0.0, "previous_champion_focused_core": champion["core_score"], "previous_champion_focused_worst_family": champion["worst_family_score"], "solvability": "general_compiler_unknown"}, indent=2) + "\n")
    print(json.dumps({key: value for key, value in record.items() if key != "counterexamples"}, indent=2))


if __name__ == "__main__":
    main()
