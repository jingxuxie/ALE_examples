import hashlib
import importlib.util
import json
from pathlib import Path
import time


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("trusted_revalidation_evidence", HERE / "expand_revalidation.py")
EVIDENCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVIDENCE)
TRUSTED = EVIDENCE.TRUSTED
OUTPUT = HERE / "champion_2_revalidation"


def main():
    rows = EVIDENCE.repeat_evidence()
    private = EVIDENCE.solutions(HERE / "private_solution.json")
    cases = {entry["id"]: entry for entry in EVIDENCE.load(HERE / "cases.json")["cases"]}
    proofs = {entry["id"]: entry for entry in EVIDENCE.load(HERE / "provenance.json")["cases"]}
    details = []
    for row in rows:
        if not row.get("valid") or row.get("robust_gap", 0) <= 0:
            continue
        identifier = row["id"]
        batch_number = (int(identifier.rsplit("_", 1)[1]) - 1) // 2
        candidates = []
        for base in (HERE / "champion_2_audit", OUTPUT):
            response = base / f"batch_{batch_number:02d}" / "response.json"
            if response.exists():
                candidate = EVIDENCE.solutions(response)[identifier]
                candidates.append((TRUSTED.validate_solution(cases[identifier], candidate), candidate))
        champion_cost, champion = min(candidates, key=lambda item: item[0])
        reference = private[identifier]
        orbital_only = dict(champion, orbital=reference["orbital"])
        auxiliary_only = dict(champion, auxiliary=reference["auxiliary"])
        detail = {
            "id": identifier,
            "seed": proofs[identifier]["seed"],
            "parent_seeds": proofs[identifier]["parent_seeds"],
            "cluster": f"n{proofs[identifier]['dimension']}/{proofs[identifier]['strength_regime']}",
            "relative_strength": proofs[identifier]["relative_strength"],
            "champion_best_observed_cost": champion_cost,
            "private_feasible_cost": TRUSTED.validate_solution(cases[identifier], reference),
            "private_orbital_champion_auxiliary_cost": TRUSTED.validate_solution(cases[identifier], orbital_only),
            "champion_orbital_private_auxiliary_cost": TRUSTED.validate_solution(cases[identifier], auxiliary_only),
            "physics_proof": proofs[identifier],
            "interpretation": "Competing localized PSD charge families in independent orbital frames; crossover costs diagnose gauge coupling, not global optimality or a proven optimizer basin.",
        }
        details.append(detail)
    summary = EVIDENCE.load(OUTPUT / "summary.json")
    original_unchanged = all(
        hashlib.sha256((HERE / "champion_2_audit" / f"batch_{entry['batch']:02d}" / "report.json").read_bytes()).hexdigest()
        == entry["original_report_sha256"] for entry in summary["batches"])
    snapshot, mismatches = TRUSTED.source_snapshot()
    prior_snapshot = EVIDENCE.load(HERE / "source_hashes.json")
    champion = TRUSTED.ROOT / "champions/generation_2"
    manifest = EVIDENCE.load(TRUSTED.ROOT / "champions/generation_2_manifest.json")["sha256"]
    champion_mismatches = [name for name, expected in manifest.items()
                          if hashlib.sha256((champion / name).read_bytes()).hexdigest() != expected]
    repeated_positive = [row for row in rows if row.get("valid") and row["original_valid"] and row["robust_gap"] > 0]
    first_scored_positive = [row for row in rows if row.get("valid") and not row["original_valid"] and row["robust_gap"] > 0]
    result = {
        "completed_unix": time.time(),
        "requested_batch_repeats": 5,
        "valid_repeat_batches": sum(entry["report"].get("valid", False) for entry in summary["batches"]),
        "invalid_repeat_batches": sum(not entry["report"].get("valid", False) for entry in summary["batches"]),
        "records": rows,
        "robust_repeated_positive_cases": repeated_positive,
        "first_scored_positive_cases_not_yet_repeated": first_scored_positive,
        "rootcause_records": details,
        "case023_expansion_gate_met": False,
        "additional_physical_cases_generated": 0,
        "original_reports_unchanged": original_unchanged,
        "frozen_sources_match_prior_snapshot": snapshot == prior_snapshot,
        "frozen_manifest_mismatches": mismatches,
        "champion_manifest_mismatches": champion_mismatches,
        "no_participant_generation_created": True,
        "no_untrusted_code_imported": True,
        "quality_costs_independently_checked_by": "concept_1/evaluator/evaluate.py:validate_solution",
        "timing_interpretation": "Batches07/09 timeout twice; batch10 passes on repeat. Batch11 had one valid original observation then times out. This distinguishes observed repeatability, not the causal source of deadline variability. No timeout contributes a quality score.",
        "recommendation": "Do not build another A ratchet from this evidence. Keep A solved: case023's approximately1.05% observation is not robustly revalidated; any approximately0.51% repeatable gap is too small for the proposed1% aggregate target and leaves virtually no0.5% family margin.",
        "limits": "One exact repeat per requested batch; no global optimality claims; no additional search after the conditional gate failed. The original diagnostic baseline fields and reported passed flags are not champion-reference benchmark scores.",
    }
    (OUTPUT / "decision.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key not in ("records", "rootcause_records")}, indent=2), flush=True)
    for row in rows:
        print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
