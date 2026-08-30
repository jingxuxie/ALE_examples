"""Private bounded-investigation handoff, without changing main task status."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

PACKET = Path(__file__).resolve().parents[1]
AUTHORING = PACKET / "authoring"


def load(name):
    return json.loads((AUTHORING / name).read_text())


def main():
    portfolio = load("portfolio_certification_final.json")
    exact_proof = load("exact_relaxed_state_exclusion.json")
    derivative = load("private_derivative_audit.json")
    relaxations = {}
    for name in ("relaxed_exact_right", "relaxed_nearby", "relaxed_bounds_lower", "relaxed_bounds_upper", "relaxed_rayleigh"):
        data = load(name + "_summary.json")
        relaxations[name] = {"starts": len(data["records"]),
                             "feasible_relaxed_outputs": sum(record["feasible_in_relaxation"] for record in data["records"]),
                             "smallest_observed_feasible_gradient": data["best_relaxed_gradient_norm"],
                             "not_a_global_bound": True}
    searches = {}
    for name in ("reduced_v3", "reduced_r2", "reduced_gen1", "reduced_gen2", "finite_v3_soft", "finite_author_soft",
                 "joint_scaled_v3", "joint_scaled_author"):
        data = load(name + "/summary.json")
        searches[name] = {key: value for key, value in data.items() if key != "records"}
        if "records" in data:
            searches[name]["stages"] = len(data["records"])
    mismatches = []
    pinned_count = 0
    for filename in ("freeze.json", "evaluator_freeze.json"):
        manifest = json.loads((PACKET / filename).read_text())
        for relative, digest in manifest["sha256"].items():
            pinned_count += 1
            if hashlib.sha256((PACKET / relative).read_bytes()).hexdigest() != digest:
                mismatches.append(relative)
    earlier = load("active_generation_3_hashes.json")
    historical_mismatches = [relative for relative, digest in earlier.items()
                            if relative.startswith(("adversary/generation_3_snapshot/", "champions/generation_3/"))
                            and hashlib.sha256((PACKET.parents[1] / relative).read_bytes()).hexdigest() != digest]
    if mismatches or historical_mismatches:
        raise RuntimeError("frozen or historical hash mismatch; do not claim isolation")
    now = datetime.now(timezone.utc)
    started = datetime.fromisoformat("2026-08-28T12:36:04+00:00")
    passed = bool(portfolio["privileged_witness_found"])
    report = {"completed_at_utc": now.isoformat(), "elapsed_wall_minutes": (now - started).total_seconds() / 60,
              "worker_feasibility_outcome": "verified_witness" if passed else "unresolved",
              "passing_243_point_witness_found": passed, "universal_impossibility_proof_found": False,
              "global_gradient_lower_bound_proved": False, "fresh_attempt_results_used": False,
              "active_v4_or_v4_r2_submissions_or_source_read": False, "fresh_agents_launched": 0,
              "main_readiness_or_final_status_modified": False, "empirical_hardness_decision": "reserved for main worker",
              "relaxation_runs": relaxations, "stationary_and_finite_searches": searches,
              "independent_portfolio": portfolio,
              "exact_fixed_state_exclusion": {"passed": exact_proof["passed"], "scope": exact_proof["scope"],
                                               "coefficients": exact_proof["decimal_approximations"]},
              "private_derivative_audit_passed": derivative["passed"],
              "frozen_packet_integrity": {"pinned_files_checked": pinned_count, "mismatches": mismatches,
                                           "historical_snapshot_or_champion_mismatches": historical_mismatches},
              "interpretation": "No universal derivative bound was proved. Even a derivative bound would require additional finite-curvature control to exclude the actual frozen probes. Numerical local minima are not an impossibility or hardness certificate."}
    (AUTHORING / "investigation_report.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    lines = ["# Bounded private generation-four investigation", "",
             "Outcome: " + ("verified privileged witness" if passed else "no passing witness and no universal impossibility proof") + ".",
             "Main owns the empirical fresh-attempt and final status decision; no readiness/status file was changed.", "",
             "## Scope and isolation", "",
             "Only generation-four `authoring/` was changed. No active v4/v4_r2 submission or source was read, and no agents were launched.",
             f"All {pinned_count} frozen public/trusted source hashes remain intact. Historical generation-three snapshot/champion hashes also match.",
             f"Elapsed bounded investigation: {(now - started).total_seconds() / 60:.2f} wall minutes.", "",
             "## Search evidence", "",
             f"The state-level portfolio contains {sum(data['starts'] for data in relaxations.values())} multistarts. These are relaxations/local searches, not global bounds.",
             "Exact-target nearby-state searches observed gradient norm about 0.1020343 on both population branches; no minimum was globally certified.",
             "Hamiltonian-only implicit derivatives, actual two-neighbor optimization, and simultaneous three-root stationarity searches used only completed old witnesses or private seeds.",
             "Two direct finite-probe searches reached best three-point maximum energy errors "
             f"{searches['finite_author_soft']['best_max_finite_energy_error']:.12g} and {searches['finite_v3_soft']['best_max_finite_energy_error']:.12g}; the target remains 0.0001.",
             "These are search diagnostics, not accepted full-stencil witnesses. Exact scorer results, including any other failures, are in `portfolio_certification_final.json`.", "",
             "## Obstruction evidence", "",
             "An exact rational certificate excludes one near-optimal relaxed tuple from every exactly stationary CCSD/Hermitian positive-gap realization: opposite signs of two Rayleigh coefficients demand opposite signs of the energy error.",
             "The certificate is restricted to that stored tuple. It is not a universal theorem over the task domain; see `OBSTRUCTION_NOTES.md` and `exact_relaxed_state_exclusion.json`.",
             "Neither a global gradient lower bound nor the additional finite-curvature bound needed for a finite-probe impossibility result was established.", "",
             "## Independent checks", ""]
    for record in portfolio["records"]:
        lines.append(f"- {record['label']}: pass={record['passed']}, core={record['core_score']}, reason={record['reason']}, runtime={record['runtime_seconds']:.3f}s.")
    lines += ["", "`private_derivative_audit.json` validates the private smooth search surrogate. Every artifact is evaluated with the unchanged exact frozen DAD and strict JSON/path checker.",
              "The initial zero-DAD nondifferentiability audit is retained separately; no frozen oracle, evaluator, threshold, or manifest was changed to accommodate it.", "",
              "All source, logs, state relaxations, candidate snapshots, and reports are private to this directory."]
    (AUTHORING / "INVESTIGATION_REPORT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({key: report[key] for key in ("worker_feasibility_outcome", "elapsed_wall_minutes", "passing_243_point_witness_found",
                        "universal_impossibility_proof_found", "frozen_packet_integrity")}, indent=2))


if __name__ == "__main__":
    main()
