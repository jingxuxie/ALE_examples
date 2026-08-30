import hashlib
import json
from datetime import datetime, timezone

import numpy as np

from physics import HERE, ROOT, champion, confirm


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    controls = champion()
    names = ("static_recheck", "matching_broad", "spatial_phase_cases", "continuous_candidates", "quadratic_corner_cases")
    arrays = [np.load(HERE / (name + ".npz")) for name in names]
    rows = np.concatenate([archive["scenarios"] for archive in arrays])
    scores = np.concatenate([archive["fidelities"] for archive in arrays])
    matching_difference = np.max(np.abs(rows[:, 15:27] - rows[:, 27:39]), axis=1)
    static_indices = np.flatnonzero(matching_difference < 1e-14)
    unequal_indices = np.flatnonzero(matching_difference >= 1e-14)
    cases = {}
    for label, indices in (("lowest_tested", np.arange(len(rows))), ("lowest_static", static_indices),
                           ("lowest_genuinely_matching_dependent", unequal_indices)):
        worst = int(indices[np.argmin(scores[indices])])
        case = confirm(controls, rows[worst], scores[worst], label)
        (HERE / (label + ".json")).write_text(json.dumps(case, indent=2, allow_nan=False) + "\n")
        cases[label] = case
    unique = np.unique(rows, axis=0)
    continuous = json.loads((HERE / "continuous_report.json").read_text())
    variants = json.loads((HERE / "variant_report.json").read_text())
    quadratic = json.loads((HERE / "quadratic_corner_report.json").read_text())
    audit = json.loads((HERE / "simulator_audit.json").read_text())
    regrade = json.loads((HERE / "current_checker_regrade.json").read_text())
    protected = json.loads((HERE / "protected_before.json").read_text())
    altered = [relative for relative, expected in protected.items()
               if not (ROOT / relative).is_file() or digest(ROOT / relative) != expected]
    archive = json.loads((HERE / "archive_manifest.json").read_text())
    archive_mismatch = []
    for relative, expected in archive["files"].items():
        for directory in ("attempts/frozen_v_2", "champions/generation_2"):
            path = ROOT / directory / relative
            if not path.is_file() or digest(path) != expected:
                archive_mismatch.append(str(path.relative_to(ROOT)))
    champion_files = {str(path.relative_to(ROOT / "champions/generation_2"))
                      for path in (ROOT / "champions/generation_2").rglob("*") if path.is_file()}
    integrity = {"protected_files_checked": len(protected), "protected_files_changed_or_missing": altered,
                 "archive_files_checked": len(archive["files"]), "archive_mismatches": archive_mismatch,
                 "unexpected_champion_files": sorted(champion_files - set(archive["files"])),
                 "original_attempts_preserved_in_place": not any(path.startswith("attempts/") for path in altered),
                 "passed": not altered and not archive_mismatch and champion_files == set(archive["files"])}
    (HERE / "integrity_report.json").write_text(json.dumps(integrity, indent=2) + "\n")
    summary = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "private_sidecar_only": True,
               "target": 0.95, "matching_drift_bound_radians_per_site_per_layer": 0.01,
               "exact_test_records": len(rows), "unique_exact_calibrations": len(unique),
               "genuinely_unequal_matching_test_records": len(unequal_indices),
               "failure_records_below_095": int(np.sum(scores < 0.95)),
               "minimum_exact_fidelity": float(scores.min()), "minimum_unequal_matching_fidelity": float(scores[unequal_indices].min()),
               "minimum_margin_above_095": float(scores.min() - 0.95),
               "source_counts": {name: len(archive["scenarios"]) for name, archive in zip(names, arrays)},
               "continuous_adversarial_restarts": continuous["restarts"],
               "continuous_objective_evaluations": sum(record["evaluations"] for record in continuous["optimizer_records"]),
               "quadratic_surrogate_corners_per_calibration": quadratic["surrogate_only_corners_per_calibration"],
               "quadratic_calibrations": quadratic["calibrations"],
               "quadratic_exact_confirmation_cases": quadratic["exact_cases"],
               "surrogate_ranking_is_not_exhaustive_exact_validation": True,
               "current_frozen_checker": regrade, "simulator_audit": audit, "integrity": integrity,
               "feasibility": "Archived champion passes every tested matching-dependent case; no whole-box certificate.",
               "proposed_ratchet_decision": "HOLD_NO_SEPARATING_COUNTEREXAMPLE_FOUND",
               "no_participant_evaluator_status_or_freeze_changes": integrity["passed"],
               "private_variants": variants["refinements"], "cases": cases}
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    outcome = "No champion failure found" if summary["failure_records_below_095"] == 0 else "Counterexample found"
    comparison = "\n".join(f'- Continuous refinement starting from `{record["label"]}`: '
                           f'minimum {record["validation_minimum"]:.12f} on {record["validation_cases"]} saved cases; '
                           f'{record["below_095"]} below target.' for record in variants["refinements"])
    report = f'''# Generation-two private challenge: {outcome}

The exact v2 frozen submission was copied, not moved, into `champions/generation_2`.
The unchanged trusted evaluator reproduces fidelity **{regrade["score"]:.15f}**, core **{regrade["core_score"]:.15f}**, and a valid pass on 223 original frozen cases.

## Model tested

All current graph, 24-layer pulse constraints, gain and ZZ ranges, and target 0.95 remain unchanged.
The proposed model assigns a separate time-static 12-site RZ-angle vector to each of the two alternating bond matchings.
Each component remains in [-0.01, 0.01] radians per site per layer. After each layer's ZZ and RX gates, apply the corresponding matching's RZ field, including after layer 23.
Equal even/odd vectors exactly recover the current static model. This is not independent shot noise or arbitrary per-layer noise.

## Coverage and results

- 751 static records: the original 223, 16 previously reported difficult cases rechecked independently, and 512 newly seeded corner/interior cases.
- 2,914 proposed-model structured and random cases: 1,350 amplitude-plane, 540 cross-spatial-pattern, 512 random vertex, and 512 near-boundary cases.
- 384 cyclic spatial-offset/sign cases at 16 prior difficult calibrations.
- 64 exact-adjoint continuous adversarial restarts in all 39 calibration coordinates, using {summary["continuous_objective_evaluations"]} objective/gradient evaluations.
- Rank 8,388,608 sign corners modulo simultaneous sign inversion with a quadratic surrogate at 17 calibrations; check the top 48 each using exact dynamics ({quadratic["exact_cases"]} exact confirmations). The huge surrogate count is **not** an exact exhaustive robustness check.
- Combined saved endpoint records: **{len(rows)}**, representing **{len(unique)} unique exact calibrations**; **{summary["failure_records_below_095"]} failures**.
- Worst compiled fidelity **{scores.min():.15f}**, independently confirmed **{cases["lowest_tested"]["independent"]["fidelity"]:.15f}**.
- Worst genuinely unequal matching-field fidelity **{scores[unequal_indices].min():.15f}**.

## Observed weakness, not a failing cluster

The lowest found point is in the old equal-vector static subcase: both RX gains -0.025, ZZ common -0.015, every edge residual -0.005, and the same structured +/-0.01 spatial field for both matchings. Its cat-basis population is {cases["lowest_tested"]["independent"]["cat_basis_population"]:.12f}, relative cat phase {cases["lowest_tested"]["independent"]["cat_relative_phase_radians"]:.9f} radians. The measured loss is mainly leakage outside the two cat-basis states, not a large GHZ relative phase.
Uniform opposite-matching drift is less harmful than uniform equal drift in the initial probes. Independent spatial patterns, cyclic offsets, continuous searches, and quadratic-ranked local sign patterns have not exposed a new matching-specific failure. This is evidence about tested points, not a proof that every unequal matching field is easier.

## Private feasibility comparisons

All 16 period-four simultaneous-pi branch patterns preserve nominal zero-calibration fidelity to roundoff. The 15 nontrivial patterns have small-training-set minima between {min(record["training_minimum"] for record in variants["branch_screen"][1:]):.12f} and {max(record["training_minimum"] for record in variants["branch_screen"][1:]):.12f}, below the original champion's {variants["branch_screen"][0]["training_minimum"]:.12f}. They worsen calibrated robustness without further redesign.
{comparison}
These are deliberately bounded, small-training-set comparisons, not evidence of impossibility. They demonstrate that nominally equivalent branch changes and local refinement need independent broad validation. All private pulses remain in this adversary directory; nothing is exposed to the next participant.
The archived champion itself already provides a passing witness for every proposed-model case tested here.

## Audit and disposition

The compiled all-4096-amplitude simulator is checked against independent tensor-axis gate contractions, not participant code. Maximum fidelity discrepancy {audit["max_compiled_independent_error"]:.3g}; pulse-gradient finite-difference error {audit["max_pulse_gradient_error"]:.3g}; calibration-gradient error {audit["max_calibration_gradient_error"]:.3g}. Equal-field reduction agrees with the current trusted checker within {audit["max_equal_vector_current_checker_error"]:.3g}. No nonzero-drift parity invariant is imposed.
Integrity audit: {integrity["protected_files_checked"]} protected files and {integrity["archive_files_checked"]} champion/source files checked; passed = {integrity["passed"]}.
**Do not promote a matching-only final ratchet on this evidence:** no separating failure was found. No claim of continuum robustness is made. Live participant, evaluator, hidden suite, status, freeze, and original attempts remain unchanged.

## Reproduction

From the concept_3 directory, compile `adversary/generation_2/statevector.cpp` using `g++ -O3 -std=c++17 -fPIC -shared` with output `adversary/generation_2/statevector.so`.
Run `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python adversary/generation_2/reproduce.py --case adversary/generation_2/lowest_tested.json`.
Use `lowest_genuinely_matching_dependent.json` for a case outside the old equal-field model. `physics.py` reruns simulator and gradient audits; `challenge.py`, `quadratic_corners.py`, and `variants.py` regenerate private search evidence. These scripts never run fresh-model calls or modify the live task.
'''
    (HERE / "REPORT.md").write_text(report)
    print(json.dumps({key: summary[key] for key in ("exact_test_records", "unique_exact_calibrations", "failure_records_below_095", "minimum_exact_fidelity", "minimum_unequal_matching_fidelity", "proposed_ratchet_decision")}))
    print(json.dumps(integrity))


if __name__ == "__main__":
    main()
