import copy
import datetime
import hashlib
import json
from pathlib import Path
import secrets
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))

import numpy as np

import evaluate
from build_cohort import accepts, features


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    cases = read(HERE / "cases_96.json")["episodes"]
    by_id = {case["id"]: case for case in cases}
    screen = read(HERE / "screen_96" / "report.json")
    records = {result["case_id"]: result for result in screen["episodes"]}
    replays = {}
    for directory in (HERE / "recheck_56", HERE / "additional_recheck_56"):
        for path in directory.glob("*replay*.json"):
            result = read(path)
            source = result["case_id"].split("-replay-")[0]
            replays.setdefault(source, []).append(result)
    twice_replayed = [identity for identity in screen["failures"] if len(replays.get(identity, [])) == 2
              and all(result["protocol_valid"] and not result["metrics"]["joint_success"] for result in replays[identity])]
    recovered = [identity for identity in screen["failures"] if any(result["metrics"]["joint_success"] for result in replays.get(identity, []))]
    reeval = HERE / "proposed_reevaluation_56" / "report.json"
    reeval_records = {result["case_id"]: result for result in read(reeval)["episodes"]} if reeval.exists() else {}
    recovered = sorted(set(recovered) | {identity for identity in screen["failures"]
                                         if identity in reeval_records and reeval_records[identity]["metrics"]["joint_success"]})
    stable = [identity for identity in twice_replayed if identity not in recovered]
    selected = []
    for family in evaluate.model.SPEC["families"]:
        failures = [identity for identity in twice_replayed if by_id[identity]["family"] == family]
        controls = sorted([case["id"] for case in cases if case["family"] == family and records[case["id"]]["metrics"]["joint_success"]],
                          key=lambda identity: (-records[identity]["wall_seconds"], identity))
        selected.extend(failures[:4] + controls[:4 - len(failures[:4])])
    chosen = [copy.deepcopy(by_id[identity]) for identity in selected]
    selected_path = HERE / "proposed_cases_12.json"
    if selected_path.exists():
        selected = [case["id"] for case in read(selected_path)["episodes"]]
    else:
        save(selected_path, {"episodes": chosen, "query_budget": 56,
                            "selection": "four per original prior family; include all twice-reproduced failures then longest-runtime originally successful controls; exclude replay-recovered failures",
                            "adversarial_heldout": True, "iid_evaluation_claim": False,
                            "frozen_before_any_new_fresh_session": True, "quality_targets_unchanged": True})
    selected_report = {"summary": evaluate.aggregate([records[identity] for identity in selected], official=False),
                       "score_origin": "actual isolated screen episodes, postselected without rescoring predictions; separate full re-evaluation is recorded if present",
                       "episodes": [records[identity] for identity in selected]}
    save(HERE / "proposed_screen_score.json", selected_report)
    calibration_path = HERE / "proposed_public_calibration.json"
    if not calibration_path.exists():
        master = secrets.randbits(128)
        generator = np.random.default_rng(master)
        calibration = []
        for family in evaluate.model.SPEC["families"]:
            for mode in ("weak_dipoles", "strong_cluster"):
                for trial in range(200000):
                    seed = int(generator.integers(0, 2 ** 63))
                    scene = evaluate.model.draw_scene(seed, family)
                    if accepts(scene, family, mode):
                        break
                else:
                    raise RuntimeError("public calibration rejection exhausted")
                actions = evaluate.model.uniform_actions()
                values = evaluate.model.simulate(scene, actions)
                calibration.append({"id": "public-frontier-" + family + "-" + mode, "family": family, "mode": mode,
                                    "seed": seed, "scene": scene, "features": features(scene),
                                    "example_actions": actions, "example_observations": [round(float(value), 12) for value in values]})
        save(calibration_path, {"master_seed": master, "episodes": calibration,
                                "selection": "independent rejection draws for each family and weak-dipole/strong-cluster regime; no champion-outcome filtering",
                                "proposed_only": True})
    validity = {result["id"]: result for result in read(HERE / "validity_scored_96.json")["episodes"]}
    clusters = []
    for identity in screen["failures"]:
        case = by_id[identity]
        result = records[identity]
        truth = case["scene"]
        estimate = result["estimate"]
        true_map = {item["site"]: item["strength"] for item in truth["impurities"]}
        estimated_map = {item["site"]: item["strength"] for item in estimate["impurities"]}
        mismatch = not result["metrics"]["vortex_exact"]
        cluster = "vortex-position/support coupled local basin" if mismatch else "signed-support multiple-scattering local basin"
        if identity in recovered:
            cluster = "search-throughput/resource-sensitive recovery; not a stable counterexample"
        clusters.append({"case_id": identity, "family": case["family"], "observed_cluster": cluster,
                         "failed_both_initial_replays": identity in twice_replayed,
                         "stable_across_all_rechecks": identity in stable,
                         "missed_sites": sorted(set(true_map) - set(estimated_map)), "spurious_sites": sorted(set(estimated_map) - set(true_map)),
                         "matched_site_sign_errors": [site for site in true_map.keys() & estimated_map.keys() if true_map[site] * estimated_map[site] < 0],
                         "true_vortices": truth["vortices"], "estimated_vortices": estimate["vortices"],
                         "features": case["features"], "original_metrics": result["metrics"], "validity": validity[identity],
                         "full_proposal_reevaluation": reeval_records.get(identity),
                         "replays": [{"success": item["metrics"]["joint_success"], "wall_seconds": item["wall_seconds"],
                                      "cpu_lower_bound": item.get("observed_cpu_seconds_lower_bound"), "stderr": item["stderr"]}
                                     for item in replays.get(identity, [])],
                         "causality_caveat": "Geometry/features and fitted residuals characterize the failure; no single-feature causal ablation is claimed."})
    frontiers = {}
    for budget in (40, 32):
        path = HERE / ("frontier_" + str(budget)) / "report.json"
        if path.exists():
            report = read(path)
            groups = {}
            for cohort in sorted({result["cohort"] for result in report["episodes"]}):
                group = [result for result in report["episodes"] if result["cohort"] == cohort]
                groups[cohort] = evaluate.aggregate(group, official=False)
            frontiers[str(budget)] = {"summary": report["summary"], "cohorts": groups, "failures": report["failures"],
                                     "adapter": "only initial fixed query slice changes from 44 to max(4,query_budget-12); same policy, model, optimizer and quality target otherwise"}
    protected = read(HERE / "protected_hashes.json")
    changed = [name for name, digest in protected.items() if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
    source_hashes = {}
    for filename in ("solve.py", "inference.py", "physics.py"):
        original = ROOT / "champions" / "generation_1" / filename
        staged = HERE / "submission" / filename
        if original.read_bytes() != staged.read_bytes():
            raise RuntimeError("staged champion changed")
        source_hashes[filename] = hashlib.sha256(staged.read_bytes()).hexdigest()
    if changed:
        raise RuntimeError("protected files changed")
    robust = reeval.exists() and read(reeval)["summary"]["target_met_on_this_sample"] and not stable
    crosscheck = HERE / "proposed_frontier_32" / "report.json"
    packet = {"schema": "ldos-ratchet-goal-packet-v1", "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "status": "robust_solved_no_ratchet_recommended" if robust else "proposal_requires_main_approval", "fresh_launched": False, "production_assets_changed": False,
              "screen_cases": 96, "screen_summary": screen["summary"], "screen_groups": screen["groups"],
              "same_prior_stable_counterexamples": stable, "replay_recovered_cases": recovered,
              "proposed_cases": "proposed_cases_12.json", "proposed_public_calibration": "proposed_public_calibration.json",
              "proposal_score_from_screen": selected_report["summary"],
              "proposal_reevaluation": read(reeval)["summary"] if reeval.exists() else None,
              "proposal_32_query_crosscheck": read(crosscheck)["summary"] if crosscheck.exists() else None,
              "quality_target": evaluate.TARGET, "proposed_primary_budget": None if robust else 56,
              "rejected_candidate_budget": 56 if robust else None, "root_cause_clusters": clusters,
              "frontiers": frontiers, "protected_changes": changed, "champion_sha256": source_hashes,
              "recommendation": ("Keep generation 1 marked solved. Reject this provisional ratchet: all 12 curated scenes were subsequently solved by the identical champion under the identical 56-query resource contract. Initial repeated failures are throughput-sensitive, not stable inverse-scattering counterexamples. Do not launch a fresh session on this proposal."
                                 if robust else "Main approval and further reproducibility checks are required; do not present postselected accuracy as IID generalization."),
              "solvability": "The unchanged champion demonstrates full-target achievability on the complete provisional 12-case suite. No label-oracle or truth-initialized solve is counted." if robust else "Full-target achievability of a new generation is not established by local Jacobians.",
              "resource_caveats": ["Original evaluator cpu_seconds undercounts nested bwrap descendants on this host; wall times remain valid.",
                                     "Replay and frontier runs add kernel process-tree CPU lower bounds; hard inherited resource limits and champion internal CPU guard remain unchanged.",
                                     "Some replays hit the champion's 110s wall guard before its 83s CPU guard under contention; this is reported, not hidden."]}
    save(HERE / "GOAL_PACKET.json", packet)
    print(json.dumps({"status": packet["status"], "stable_failures": stable, "recovered": recovered,
                      "initial_postselected_core": selected_report["summary"]["core_score"],
                      "final_reevaluation_core": packet["proposal_reevaluation"]["core_score"] if packet["proposal_reevaluation"] else None,
                      "frontiers_completed": list(frontiers)}, indent=2))


if __name__ == "__main__":
    main()
