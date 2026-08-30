import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone

sys.dont_write_bytecode = True

from metrics import HERE, ROOT, write_json


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze():
    destination = HERE / "final_design.json"
    if destination.exists():
        raise RuntimeError("final design is already frozen")
    destination.write_bytes((HERE / "design.json").read_bytes())
    write_json(HERE / "final_private_training_score.json",
               json.loads((HERE / "score.json").read_text()))
    write_json(HERE / "fitting_stopped.json", {
        "utc": datetime.now(timezone.utc).isoformat(),
        "candidate_sha256": digest(destination),
        "training_source_sha256": digest(HERE / "training_source.npz"),
        "own_training_sha256": digest(HERE / "own_training.npz"),
        "training_points": 240,
        "main_600_used_for_fitting": False,
        "no_further_fitting_after_official_evaluation": True,
    })


def report():
    stopped = json.loads((HERE / "fitting_stopped.json").read_text())
    if digest(HERE / "final_design.json") != stopped["candidate_sha256"]:
        raise RuntimeError("frozen candidate changed")
    official = json.loads((HERE / "official_score.json").read_text())
    training = json.loads((HERE / "final_private_training_score.json").read_text())
    saved_hashes = json.loads((HERE / "protected_hashes.json").read_text())
    protected_checks = {
        name: digest(ROOT / name) == saved
        for name, saved in saved_hashes.items()
        if name.startswith("champions/") or name.startswith("adversary/portfolio/")
    }
    diagnostics = json.loads((HERE / "champion_diagnostics.json").read_text())
    final_audit = HERE / "final_audit_summary.json"
    official_brief = {key: value for key, value in official.items()
                      if key != "worst_lost_circuits_per_model"}
    output = {
        "private_generation_time_only": True,
        "feasibility": "demonstrated_by_private_design" if official["passed"] else "unknown",
        "passing_proof_found": bool(official["passed"]),
        "not_an_infeasibility_proof": not official["passed"],
        "targets": {"core_at_least": .25, "every_family_at_least": .20,
                    "intact_mean_ratio_at_most": 1.20},
        "official_evaluator": official_brief,
        "private_training_score": training,
        "target_violation_factors": {
            "overall": .25 / max(official["core_score"], 1e-300),
            "worst_family": .20 / max(official["worst_family_score"], 1e-300),
            "intact_guard": official.get("intact_mean_ratio", 1e300) / 1.20,
        },
        "fitting_stopped": stopped,
        "active_attempts_inspected": False,
        "protected_old_private_artifacts_and_champion_unchanged": protected_checks,
        "public_and_evaluator_changes_authorized_by_main": True,
        "champion_broad": diagnostics["broad"],
        "champion_independent_confirmation": diagnostics["confirmation"],
        "numerical_checks": json.loads((HERE / "numerical_checks.json").read_text()),
        "root_cause_evidence": {
            "primary": "Loss of 461/471/476 removes all first-order Y_z sensitivity at zero coherent error.",
            "secondary": "Loss of 139/320/353 exposes X_z; smaller rate-information clusters remain.",
            "private_pilot": "After coherent repair, I/X depolarization loss competes with intact efficiency and cardinality.",
            "caution": "Local Fisher singularity does not prove failure of every nonlinear finite-shot inference method.",
        },
        "generalization_caution": "Large empirical triple-loss tails make small-ensemble means unstable; no population guarantee is claimed.",
    }
    if final_audit.exists():
        output["final_candidate_private_broad_validation"] = json.loads(final_audit.read_text())
    write_json(HERE / "final_report.json", output)
    print(json.dumps({"feasibility": output["feasibility"],
                      "official": official_brief,
                      "protected_artifacts_unchanged": all(protected_checks.values())}, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["freeze", "report"])
    args = parser.parse_args()
    {"freeze": freeze, "report": report}[args.stage]()


if __name__ == "__main__":
    main()
