import argparse
import concurrent.futures
import json
import multiprocessing
import random
import sys
import time


sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit import OUTPUT, frozen_hashes, write_json
from router import hardware, relabelings, transform
from validation import load_witness, replay, validate
from window_embedding import window_route


def probe(payload):
    kind, family, gates, count, edges, initial, reference, prefix_portfolio = payload
    started = time.monotonic()
    routed = window_route(gates, count, edges, initial, prefix_portfolio)
    measured = replay(gates, count, edges, routed["route"], routed["final_mapping"], initial)
    assert measured["swaps"] == routed["swaps"]
    record = {"kind": kind, "family": family, "valid_route": True,
              "seconds": time.monotonic() - started, "route": routed,
              "measured": measured, "gate_count": len(gates), "initial_mapping": initial}
    if reference is not None:
        ratio = measured["swaps"] / reference["swaps"]
        native_ratio = measured["native_2q"] / reference["native_2q"]
        gap = measured["swaps"] - reference["swaps"]
        record.update({"swap_ratio": ratio, "native_ratio": native_ratio, "swap_gap": gap,
                       "champion_meets_targets_against_repair": ratio >= 2.5 and native_ratio >= 1.35 and gap >= 16,
                       "reference": reference})
    directory = "repair_routes_portfolio" if prefix_portfolio else "repair_routes"
    write_json(OUTPUT / directory / f"{family}.json", record)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix-portfolio", action="store_true")
    arguments = parser.parse_args()
    started = time.monotonic()
    before = frozen_hashes()
    witness = load_witness(OUTPUT / "authorized_champion.json")
    count, edges, gates, reference = validate(witness)
    jobs = []
    for name, logical, physical in relabelings(count):
        mapped_gates, mapped_edges, initial = transform(gates, edges, logical, physical)
        jobs.append(("champion", name, mapped_gates, count, mapped_edges, initial, reference,
                     arguments.prefix_portfolio))
    for graph in ("ring16", "ladder16", "grid16"):
        control_count, control_edges = hardware(graph)
        for seed in (1709, 2027):
            generator = random.Random(seed)
            initial = list(range(control_count))
            generator.shuffle(initial)
            control_gates = [generator.sample(range(control_count), 2) for _ in range(12)]
            jobs.append(("control", f"control-{graph}-{seed}", control_gates,
                         control_count, control_edges, initial, None, arguments.prefix_portfolio))
    records = []
    context = multiprocessing.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(max_workers=6, mp_context=context) as pool:
        futures = [pool.submit(probe, payload) for payload in jobs]
        for future in concurrent.futures.as_completed(futures):
            record = future.result()
            records.append(record)
            print(json.dumps({"family": record["family"], "swaps": record["measured"]["swaps"],
                              "window": record["route"].get("window"), "seconds": record["seconds"]}), flush=True)
    after = frozen_hashes()
    assert before == after
    champion = sorted((record for record in records if record["kind"] == "champion"), key=lambda item: item["family"])
    controls = [record for record in records if record["kind"] == "control"]
    summary = {"repair": "bounded suffix-core embedding with paid terminal tail",
               "prefix_policy": "frozen G3 portfolio" if arguments.prefix_portfolio else "weighted horizon16 factor0.9 ascending",
               "completed_policy_calls": len(records), "champion_families": len(champion),
               "independent_controls": len(controls), "all_routes_valid": all(record["valid_route"] for record in records),
               "repair_defeats_champion_all_public_families": all(not record["champion_meets_targets_against_repair"] for record in champion),
               "minimum_repair_swaps": min(record["measured"]["swaps"] for record in champion),
               "maximum_repair_swaps": max(record["measured"]["swaps"] for record in champion),
               "assembled_routes_replayed": sum(record["route"]["search_statistics"]["assembled_routes_replayed"] for record in records),
               "prefix_setting_routes_replayed": sum(record["route"]["search_statistics"]["prefix_setting_routes_replayed"] for record in records),
               "baseline_routes_replayed": len(records), "final_routes_replayed": len(records),
               "seconds": time.monotonic() - started, "frozen_artifacts_unchanged": before == after,
               "official_G3_score_changed": False, "no_further_generation": True,
               "champion": champion, "controls": controls}
    filename = "repair_summary_portfolio.json" if arguments.prefix_portfolio else "repair_summary.json"
    write_json(OUTPUT / filename, summary)
    print(json.dumps({key: value for key, value in summary.items() if key not in ("champion", "controls")}), flush=True)


if __name__ == "__main__":
    main()
