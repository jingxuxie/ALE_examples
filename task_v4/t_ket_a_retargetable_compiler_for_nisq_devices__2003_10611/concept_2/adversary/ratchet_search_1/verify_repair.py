import hashlib
import importlib.util
import json
import multiprocessing
import random
import sys
import time
from pathlib import Path


OUTPUT = Path(__file__).resolve().parent
ROOT = OUTPUT.parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "participant" / "input"))

from beam_policy import route_beam
from router import relabelings, route, settings, transform
from validation import InvalidWitness, load_witness, replay, validate


REPAIR = {"width": 64, "max_swaps": None, "objective": "unique_pairs",
          "progress_weight": 0.0, "max_expansions": 200000}


def run_case(case):
    label, witness, family = case
    count, edges, gates, reference = validate(witness)
    name, logical, physical = family
    mapped_gates, mapped_edges, initial = transform(gates, edges, logical, physical)
    started = time.monotonic()
    routed = route_beam(mapped_gates, count, mapped_edges, initial, **REPAIR)
    measured = replay(mapped_gates, count, mapped_edges, routed["route"], routed["final_mapping"], initial)
    assert measured["swaps"] == routed["swaps"]
    assert measured["swaps"] <= routed["incumbent_swaps"]
    ratio = measured["swaps"] / reference["swaps"]
    native_ratio = measured["native_2q"] / reference["native_2q"]
    gap = measured["swaps"] - reference["swaps"]
    return {"label": label, "family": name, "hardware": witness["hardware"],
            "gates": len(gates), "reference": reference, **routed,
            "initial_mapping": initial, "seconds": time.monotonic() - started,
            "swap_ratio": ratio, "native_ratio": native_ratio, "swap_gap": gap,
            "old_witness_still_passes": ratio >= 2.5 and native_ratio >= 1.35 and gap >= 16,
            "valid_replay": True}


def make_controls():
    specification = importlib.util.spec_from_file_location("trusted_baseline_generator", ROOT / "participant/baseline/generate.py")
    generator_module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(generator_module)
    controls = []
    for graph_index, graph in enumerate(("ring16", "ladder16", "grid16")):
        for gate_count in (64, 96):
            for variant in range(2):
                for seed in range(5000 + 1000 * graph_index + 100 * variant,
                                  5100 + 1000 * graph_index + 100 * variant):
                    witness = generator_module.inverse_candidate(seed, graph, gate_count, 12)
                    try:
                        validate(witness)
                    except (InvalidWitness, ValueError):
                        continue
                    label = f"control-{graph}-{gate_count}-{variant}"
                    controls.append((label, witness, relabelings(16)[variant]))
                    break
                else:
                    raise RuntimeError("control generation failed")
    return controls


def main():
    started = time.monotonic()
    champion = load_witness(OUTPUT / "authorized_champion.json")
    cases = [("champion", champion, family) for family in relabelings(16)]
    for seed in range(35001, 35017):
        generator = random.Random(seed)
        logical, physical = list(range(16)), list(range(16))
        generator.shuffle(logical)
        generator.shuffle(physical)
        cases.append(("champion-extra", champion, (f"joint-{seed}", logical, physical)))
    controls = make_controls()
    (OUTPUT / "independent_controls.json").write_text(json.dumps(
        [{"label": label, "witness": witness, "family": family} for label, witness, family in controls], indent=2) + "\n")
    cases.extend(controls)
    with multiprocessing.get_context("fork").Pool(8) as pool:
        results = list(pool.imap_unordered(run_case, cases))
    official = sorted((row for row in results if row["label"] == "champion"), key=lambda row: row["family"])
    extra = [row for row in results if row["label"] == "champion-extra"]
    control_results = [row for row in results if row["label"].startswith("control-")]
    report = {"repair_configuration": REPAIR, "official_families": official,
              "additional_relabelings": extra, "independent_controls": control_results,
              "routes_replayed": len(results), "seconds": time.monotonic() - started,
              "all_valid_replays": all(row["valid_replay"] for row in results),
              "champion_rejected_in_every_official_family": not any(row["old_witness_still_passes"] for row in official),
              "champion_rejected_in_every_extra_family": not any(row["old_witness_still_passes"] for row in extra),
              "helper_sha256": hashlib.sha256((OUTPUT / "beam_policy.py").read_bytes()).hexdigest(),
              "trusted_source_sha256": hashlib.sha256((ROOT / "participant/input/router.py").read_bytes()).hexdigest(),
              "target_unchanged": {"swap_ratio": 2.5, "native_ratio": 1.35, "swap_gap": 16},
              "original_settings": len(settings()), "proposed_settings_with_one_component": len(settings()) + 1,
              "policy_reads_champion_reference_route": False,
              "frozen_sources_modified": False, "new_generation_built": False, "fresh_agents_launched": 0}
    (OUTPUT / "verified_repair.json").write_text(json.dumps(report, indent=2) + "\n")
    (OUTPUT / "repaired_champion_routes.json").write_text(json.dumps(official, indent=2) + "\n")
    print(json.dumps({"official_counts": [row["swaps"] for row in official],
                      "official_ratios": [row["swap_ratio"] for row in official],
                      "extra_counts": [row["swaps"] for row in extra],
                      "control_counts": [{"label": row["label"], "reference": row["reference"]["swaps"],
                                          "repair": row["swaps"], "incumbent": row["incumbent_swaps"],
                                          "beam_succeeded": row["beam_succeeded"]} for row in control_results],
                      "all_replays_valid": report["all_valid_replays"], "seconds": report["seconds"],
                      "slowest_seconds": max(row["seconds"] for row in results)}), flush=True)


if __name__ == "__main__":
    main()
