import argparse
import json
import os
from datetime import datetime, timezone

from build_batch import CONCEPT, OWNED, ROOT, immutable_manifest, require, sha256, write_json


PACKET = CONCEPT / "adversary/ratchet_1"
HIDDEN = PACKET / "evaluator/hidden"
SOURCE = OWNED / "batch_02"
PUBLIC_FILES = (
    "participant/TASK.md", "participant/workspace/INTERFACE.md",
    "participant/workspace/pair_model.py", "participant/workspace/practice.py",
    "participant/workspace/protocol.py", "participant/baseline/solution.py",
    "participant/input/practice.npz", "participant/input/practice_models.json",
    "participant/input/practice_diagnostics.json",
)


def public_audit():
    actual = {str(path.relative_to(PACKET)) for path in (PACKET / "participant").rglob("*") if path.is_file()}
    require(actual == set(PUBLIC_FILES), "unexpected solver-facing asset")
    require(not any(path.is_symlink() for path in PACKET.rglob("*")), "packet contains symlinks")
    unchanged = [relative for relative in PUBLIC_FILES if relative not in (
        "participant/TASK.md", "participant/workspace/INTERFACE.md", "participant/workspace/protocol.py"
    )]
    for relative in unchanged:
        require(sha256(PACKET / relative) == sha256(CONCEPT / relative), "original practice, model, or weak baseline was changed")
    old_protocol = (CONCEPT / "participant/workspace/protocol.py").read_text()
    require((PACKET / "participant/workspace/protocol.py").read_text() == old_protocol.replace("wall_seconds=180", "wall_seconds=600"), "public protocol changed beyond wall allowance")
    for relative in ("participant/TASK.md", "participant/workspace/INTERFACE.md"):
        content = (PACKET / relative).read_text().lower()
        for forbidden in ("witness", "champion", "jacobian", "nullspace", "cancellation_search", "network4", "network5"):
            require(forbidden not in content, "private construction or policy information leaked into public docs")
    return {
        "passed": True, "public_allowlist": list(PUBLIC_FILES),
        "unchanged_original_assets": {relative: sha256(PACKET / relative) for relative in unchanged},
        "public_protocol_change": "wall_seconds default only: 180 to 600",
        "old_champion_copied": False, "private_witness_copied": False, "search_code_copied": False,
        "source_artifacts_forbidden_to_solver": True,
    }


def target_diff(target):
    previous = json.loads((CONCEPT / "evaluator/hidden/target.json").read_text())
    keys = ("rmse_hartree_max", "worst_family_rmse_hartree_max", "query_budget_per_system",
            "maximum_queried_virtuals", "cpu_seconds", "wall_seconds", "memory_bytes")
    return {
        "old_generation": 1, "new_generation": 2,
        "numeric_contract": {key: {"old": previous[key], "new": target[key], "changed": previous[key] != target[key]} for key in keys},
        "submission_limit_bytes": {"old": 134217728, "new": 134217728, "changed": False},
        "hidden_suite": {"old": "original independent sampler suite", "new": "fixed validated batch_02 with 20 conditioned mixed systems plus 100 ordinary controls"},
        "domain_contract": {"old": "IID from example sampler", "new": "explicit conditioned, non-IID six-stratum effective-model domain with rounded coefficient bounds"},
        "wall_change_reason": "Declared before any fresh launch to reduce shared-host scheduling noise; aggregate CPU/query/memory/accuracy constraints unchanged",
        "original_root_modified": False,
    }


def prepare():
    require(not (PACKET / "freeze_manifest.json").exists(), "packet already frozen")
    source_score = json.loads((SOURCE / "score.json").read_text())
    require(source_score["valid"] and not source_score["passed"] and len(source_score["records"]) == 120, "source batch lacks genuine official accuracy failure")
    require(source_score["cpu_seconds"] <= 120 and source_score["runtime_seconds"] <= 180, "source batch did not satisfy original resources")
    source_provenance = json.loads((SOURCE / "provenance.json").read_text())
    require(immutable_manifest() == source_provenance["input_sha256"], "original assets changed")
    for filename in ("cases.npz", "models.json"):
        require(sha256(HIDDEN / filename) == sha256(SOURCE / filename), "hidden suite copy differs from validated batch")
    target = {
        "generation": 2, "verification_mode": "E", "frozen_before_fresh_attempt": False,
        "rmse_hartree_max": 1e-5, "worst_family_rmse_hartree_max": 2.5e-5,
        "query_budget_per_system": 160, "maximum_queried_virtuals": 6,
        "cpu_seconds": 120, "wall_seconds": 600, "memory_bytes": 2147483648,
        "submission_bytes_max": 134217728, "hidden_case_count": 120,
        "known_passing_policy": None,
        "hidden_domain": {
            "model": "real effective three-pair seniority-zero Hamiltonian; not ab initio Coulomb integrals",
            "npairs": 3, "nvirtual": 8, "occupied_energy_eh": [-.45, -.22, 0.0],
            "virtual_energy_interval_eh": [.85, 2.4], "hopping_absolute_bound_eh": .9,
            "density_absolute_bound_eh": .65, "reference_weight_min": .94, "gap_min_eh": .35,
            "symmetric_zero_diagonal_hopping_density": True,
            "stratum_counts": source_provenance["family_counts"],
            "conditioned_signed_cancellation_included": True, "IID_claim": False,
            "example_sampler_is_illustrative_not_exhaustive": True,
        },
        "target_rationale": "Recover the full model correlation energy over the declared fixed six-stratum domain under unchanged accuracy and deterministic resource constraints",
    }
    write_json(HIDDEN / "target.json", target)
    write_json(HIDDEN / "target_diff.json", target_diff(target))
    diagnostics = json.loads((SOURCE / "diagnostics.json").read_text())
    retained = ("index", "family", "energy", "reference_weight", "gap", "residual",
                "independent_full_energy_error_eh", "independent_full_residual")
    write_json(HIDDEN / "diagnostics.json", [{key: item[key] for key in retained} for item in diagnostics])
    write_json(HIDDEN / "source_validation.json", json.loads((SOURCE / "validation_summary.json").read_text()))
    write_json(HIDDEN / "source_diversity.json", json.loads((SOURCE / "diversity.json").read_text()))
    write_json(HIDDEN / "provenance.json", {
        "private": True, "source_generation": 1, "packet_generation": 2,
        "source_batch": str(SOURCE.relative_to(ROOT)),
        "fixed_suite_sha256": {filename: sha256(HIDDEN / filename) for filename in ("cases.npz", "models.json")},
        "source_batch_score_sha256": sha256(SOURCE / "score.json"),
        "source_batch_summary_sha256": sha256(SOURCE / "summary.json"),
        "source_batch_provenance_sha256": sha256(SOURCE / "provenance.json"),
        "source_generation_provenance": source_provenance,
        "construction_source_sha256": {str(path.relative_to(ROOT)): sha256(path) for path in sorted(OWNED.glob("*.py"))},
        "original_E_target_sha256": sha256(CONCEPT / "evaluator/hidden/target.json"),
        "source_case_selection": "Fixed before E2 benchmark; no further candidate batches or outcome-selected replacements",
        "clustering_disclosure": "Two seed-derived conditioned neighborhoods, not twenty independent witness seeds; author subgroup remains tightly clustered in old CAS2 and fourth-order observables despite distinct coefficient vectors",
        "public_asset_policy": "Only original 36 practice assets, public simulator/protocol/practice runner, original weak baseline, and new neutral contract",
        "wall600_is_official_new_generation_contract": True,
    })
    write_json(HIDDEN / "public_asset_audit.json", public_audit())
    write_json(PACKET / "status.json", {
        "concept": "adaptive_cas_experiment_design", "verification_mode": "E", "generation": 2,
        "status": "validation_pending", "fresh_attempt_count": 0, "fresh_agents_launched": 0,
        "attempts_empty": True, "no_fresh_launch": True, "hardness_established": False,
        "solvability_demonstrated": False, "known_passing_solution": None,
        "participant_task": "participant/TASK.md", "target_frozen": None,
    })
    print("E2 metadata prepared; validation and resource-accounted benchmarks required before readiness.", flush=True)


def freeze():
    require(not (PACKET / "freeze_manifest.json").exists(), "refusing to refreeze packet")
    require(not list((PACKET / "attempts").iterdir()), "fresh attempt appeared before freeze")
    source_provenance = json.loads((SOURCE / "provenance.json").read_text())
    require(immutable_manifest() == source_provenance["input_sha256"], "original assets changed before freeze")
    for filename, flag in (("validation.json", "valid"), ("protocol_validation.json", "passed"), ("resource_validation.json", "passed")):
        require(json.loads((HIDDEN / filename).read_text())[flag], "standalone validation failed")
    benchmarks = {}
    known = None
    for label, filename in (("original_weak_baseline", "baseline_score.json"), ("unchanged_original_E_champion", "original_champion_score.json")):
        report = json.loads((HIDDEN / filename).read_text())
        require(report["valid"] and len(report["records"]) == 120, "benchmark is incomplete or invalid")
        require(report["cpu_seconds"] <= 120 and report["runtime_seconds"] <= 600, "benchmark exceeds official E2 resources")
        require(report["peak_policy_rss_bytes"] <= 2147483648 and report["maximum_query_cost"] <= 160, "benchmark memory or query violation")
        benchmarks[label] = {key: value for key, value in report.items() if key != "records"}
        if report["passed"]:
            known = {"label": label, "score": "evaluator/hidden/" + filename}
    write_json(HIDDEN / "benchmark_summary.json", benchmarks)
    target = json.loads((HIDDEN / "target.json").read_text())
    target.update(frozen_before_fresh_attempt=True, known_passing_policy=known)
    write_json(HIDDEN / "target.json", target)
    write_json(HIDDEN / "target_diff.json", target_diff(target))
    audit = public_audit()
    write_json(HIDDEN / "public_asset_audit.json", audit)
    write_json(PACKET / "status.json", {
        "concept": "adaptive_cas_experiment_design", "verification_mode": "E", "generation": 2,
        "status": "ready", "ratchet_generations": 1, "fresh_attempt_count": 0,
        "fresh_agents_launched": 0, "attempts_empty": True, "no_fresh_launch": True,
        "fresh_time_limit_seconds": 3600, "hardness_established": False,
        "solvability_demonstrated": known is not None, "known_passing_solution": known,
        "participant_task": "participant/TASK.md", "target_frozen": "evaluator/hidden/target.json",
        "freeze_manifest": "freeze_manifest.json",
        "evaluator_command": "python3 evaluator/evaluate.py --submission SUBMISSION --output SCORE.json",
        "baseline_command": "python3 evaluator/evaluate.py --submission participant/baseline --output SCORE.json",
        "readiness_basis": "Independent physics, complete-table, protocol/isolation, descendant resource accounting, and reference benchmarks validated; no claim that no possible policy passes",
        "solver_access": "Only participant/ and a new empty submission workspace; packet root/evaluator/provenance and all prior artifacts forbidden",
    })
    manifest = {
        "generation": 2, "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "frozen_before_fresh_attempt": True, "fresh_agents_launched": 0,
        "public_allowlist": list(PUBLIC_FILES),
        "files_sha256": {
            str(path.relative_to(PACKET)): sha256(path)
            for path in sorted(PACKET.rglob("*")) if path.is_file() and path.name != "freeze_manifest.json"
        },
        "original_E_inputs_unchanged": True,
        "source_manifest_sha256": sha256(SOURCE / "provenance.json"),
    }
    write_json(PACKET / "freeze_manifest.json", manifest)
    print(json.dumps({"status": "ready", "frozen_files": len(manifest["files_sha256"]),
                      "public_files": len(PUBLIC_FILES), "known_passing_solution": known,
                      "hardness_established": False, "no_fresh_launch": True, "benchmarks": benchmarks}, indent=2), flush=True)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "freeze"))
    arguments = parser.parse_args()
    if arguments.action == "prepare":
        prepare()
    else:
        freeze()


if __name__ == "__main__":
    main()
