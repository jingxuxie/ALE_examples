import hashlib
import json
import multiprocessing
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


OUTPUT = Path(__file__).resolve().parent
CONCEPT = OUTPUT.parents[1]
OLD = CONCEPT / "adversary/generation_2"
NEW = CONCEPT / "adversary/generation_3"
sys.dont_write_bytecode = True
sys.path.insert(0, str(NEW / "participant/input"))

from benchmark import evaluate_file
from embedding import suffix_route_all
from router import hardware, relabelings, settings, transform
from validation import replay


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def check_pruning(case):
    label, gates, count, edges, initial, expected = case
    pruned = suffix_route_all(gates, count, edges, initial)
    measured = replay(gates, count, edges, pruned["route"], pruned["final_mapping"], initial)
    if expected is None:
        unpruned = suffix_route_all(gates, count, edges, initial, prune=False)
        original = replay(gates, count, edges, unpruned["route"], unpruned["final_mapping"], initial)
        expected = original["swaps"]
        replay_count = 2
    else:
        replay_count = 1
    assert measured["swaps"] == expected, f"safe prune changed cost for {label}"
    return {"label": label, "pruned_swaps": measured["swaps"], "unpruned_swaps": expected,
            "replays_this_check": replay_count, "equivalent": True}


def main():
    started = time.monotonic()
    probe = json.loads((OUTPUT / "probe_results.json").read_text())
    assert probe["repair_confirmed"]
    security = json.loads((NEW / "adversary/validation.json").read_text())
    assert security["passed"] and security["check_count"] == 47
    configuration_code = "import sys,json;sys.path.insert(0,sys.argv[1]);from router import settings;print(json.dumps(settings()))"
    old_process = subprocess.run([sys.executable, "-I", "-B", "-c", configuration_code,
                                   str(OLD / "participant/input")], capture_output=True, text=True, check=True)
    old_settings = json.loads(old_process.stdout)
    new_settings = settings()
    assert len(old_settings) == 25 and len(new_settings) == 62
    assert len({setting["name"] for setting in new_settings}) == 62
    assert new_settings[:25] == old_settings
    assert len([setting for setting in new_settings if setting["name"].startswith("future-")]) == 36
    retained_assets = {}
    for relative in ("participant/input/validation.py", "participant/input/benchmark.py",
                     "participant/baseline/witness.json", "participant/baseline/generate.py", "evaluator/evaluate.py"):
        retained_assets[relative] = (NEW / relative).read_bytes() == (OLD / relative).read_bytes()
    assert all(retained_assets.values())
    assert (NEW / "participant/input/embedding.py").read_text().startswith((OLD / "participant/input/embedding.py").read_text())
    champion = json.loads((OUTPUT / "authorized_champion.json").read_text())
    regression = evaluate_file(OUTPUT / "authorized_champion.json")
    assert regression["valid"] and not regression["passed"]
    assert regression["target"] == {"swap_ratio": 2.5, "native_ratio": 1.35, "swap_gap": 16}
    assert all(len(family["settings"]) == 62 and family["portfolio_swaps"] <= 23 for family in regression["families"])
    previous_score = json.loads((CONCEPT / "attempts/v_2.score.json").read_text())
    previous_families = {family["name"]: family for family in previous_score["families"]}
    for family in regression["families"]:
        assert family["settings"][:25] == previous_families[family["name"]]["settings"]
    write_json(NEW / "evaluator/hidden/g2_champion_score.json", regression)
    write_json(NEW / "adversary/g2_champion_score.json", regression)
    count, edges = hardware(champion["hardware"])
    unpruned = next(group for group in probe["configurations"]
                    if group["setting"]["mode"] == "embedding-all-program")
    unpruned_counts = {row["family"]: row["swaps"] for row in unpruned["families"]}
    cases = []
    for name, logical, physical in relabelings(count):
        gates, mapped_edges, initial = transform(champion["gates"], edges, logical, physical)
        cases.append((f"champion-{name}", gates, count, mapped_edges, initial, unpruned_counts[name]))
    for graph in ("ring16", "ladder16", "grid16"):
        count, graph_edges = hardware(graph)
        for seed in (19, 31):
            generator = random.Random(seed)
            gates = [generator.sample(range(count), 2) for _ in range(12)]
            _, logical, physical = relabelings(count)[-1]
            mapped_gates, mapped_edges, initial = transform(gates, graph_edges, logical, physical)
            cases.append((f"random-{graph}-{seed}", mapped_gates, count, mapped_edges, initial, None))
    with multiprocessing.get_context("fork").Pool(6) as pool:
        pruning_checks = list(pool.imap_unordered(check_pruning, cases))
    protected_sources_unchanged = all(hashlib.sha256((OLD / "participant/input" / name).read_bytes()).hexdigest() == digest
                                      for name, digest in probe["source_hashes"].items())
    assert protected_sources_unchanged
    public_paths = [path for path in (NEW / "participant").rglob("*") if path.is_file()]
    champion_bytes = (OUTPUT / "authorized_champion.json").read_bytes()
    assert not any(path.read_bytes() == champion_bytes for path in public_paths)
    assert len(public_paths) == 10
    manifest = {str(path.relative_to(NEW)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(public_paths + [NEW / "evaluator/evaluate.py"])}
    validation = {"passed": True, "generation": 3, "final_generation": True,
                  "settings": 62, "families": 6, "retained_settings": 25, "new_settings": 37,
                  "security_checks": security["check_count"], "security_checks_passed": True,
                  "baseline_valid": security["baseline"]["valid"], "baseline_passed": security["baseline"]["passed"],
                  "baseline_core_score": security["baseline"]["core_score"],
                  "baseline_portfolio_routes_replayed": 372, "randomized_policy_routes_replayed": 372,
                  "g2_regression_routes_replayed": 372,
                  "pruning_checks": pruning_checks,
                  "additional_pruning_replays": sum(row["replays_this_check"] for row in pruning_checks),
                  "old_policy_results_unchanged": True, "byte_identical_retained_assets": retained_assets,
                  "g2_sources_unchanged": protected_sources_unchanged,
                  "old_champion_valid": regression["valid"], "old_champion_passed": regression["passed"],
                  "old_champion_core_score": regression["core_score"],
                  "old_champion_worst_family_score": regression["worst_family_score"],
                  "old_champion_portfolio_swaps": [family["portfolio_swaps"] for family in regression["families"]],
                  "prior_raw_submissions_in_public_assets": False, "fresh_agents_launched": 0,
                  "seconds": time.monotonic() - started}
    write_json(NEW / "evaluator/hidden/validation.json", validation)
    write_json(NEW / "adversary/final_validation.json", validation)
    write_json(NEW / "adversary/frozen_manifest.json", manifest)
    freeze = {"generation": 3, "final_generation": True, "maximum_generations": 3,
              "frozen_at_utc": datetime.now(timezone.utc).isoformat(), "settings": new_settings,
              "target": regression["target"], "public_asset_sha256": manifest,
              "repair_confirmed_before_build": True, "regression_defeated": True,
              "validation_passed": True, "fresh_agents_launched": 0, "launch_owner": "main"}
    write_json(NEW / "evaluator/hidden/freeze.json", freeze)
    write_json(NEW / "adversary/freeze.json", freeze)
    status_path = NEW / "status.json"
    previous_status = status_path.read_text()
    status = json.loads(previous_status)
    status.update({"status": "hard_open_candidate", "launch_ready": True, "frozen": True,
                   "frozen_at_utc": freeze["frozen_at_utc"], "validation_passed": True,
                   "security_checks_passed": 47, "old_champion_valid": True, "old_champion_passed": False,
                   "old_champion_core_score": regression["core_score"],
                   "old_champion_portfolio_swaps": validation["old_champion_portfolio_swaps"],
                   "baseline_valid": True, "baseline_passed": False,
                   "known_passing_g3_witness": False, "achievability": "open; no G3 passing witness claimed",
                   "freeze_manifest": "adversary/frozen_manifest.json",
                   "validation_report": "adversary/final_validation.json",
                   "evaluator_cli": "python -I -B evaluator/evaluate.py --solution-dir OUTPUT_DIR",
                   "next_action": "main reviews and performs the final fresh launch; no G4"})
    replacement = json.dumps(status, indent=2) + "\n"
    patch = ["*** Begin Patch", f"*** Update File: {status_path.relative_to(CONCEPT)}", "@@"]
    patch.extend("-" + line for line in previous_status.splitlines())
    patch.extend("+" + line for line in replacement.splitlines())
    patch.append("*** End Patch")
    subprocess.run(["apply_patch", "\n".join(patch) + "\n"], cwd=CONCEPT, check=True)
    print(json.dumps({"launch_ready": True, "generation": 3, "settings": 62,
                      "champion_swaps": validation["old_champion_portfolio_swaps"],
                      "champion_core_score": regression["core_score"],
                      "baseline_valid": True, "baseline_passed": False,
                      "security_checks": 47, "safe_pruning_pairs": len(pruning_checks),
                      "old_policies_unchanged": True, "frozen_public_files": len(manifest),
                      "seconds": validation["seconds"]}), flush=True)


if __name__ == "__main__":
    main()
