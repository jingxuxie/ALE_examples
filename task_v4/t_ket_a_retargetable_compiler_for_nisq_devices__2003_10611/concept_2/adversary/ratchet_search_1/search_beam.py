import json
import multiprocessing
import sys
import time
from pathlib import Path


OUTPUT = Path(__file__).resolve().parent
ROOT = OUTPUT.parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "participant" / "input"))

from beam_policy import route_beam
from router import relabelings, transform
from validation import load_witness, replay, validate


def run_case(case):
    witness, configuration, family = case
    count, edges, gates, reference = validate(witness)
    name, logical, physical = family
    mapped_gates, mapped_edges, initial = transform(gates, edges, logical, physical)
    started = time.monotonic()
    routed = route_beam(mapped_gates, count, mapped_edges, initial, **configuration)
    measured = replay(mapped_gates, count, mapped_edges, routed["route"], routed["final_mapping"], initial)
    assert measured["swaps"] == routed["swaps"]
    return {"family": name, "configuration": configuration, "reference": reference,
            **routed, "seconds": time.monotonic() - started,
            "initial_mapping": initial,
            "champion_meets_target": measured["swaps"] >= 2.5 * reference["swaps"]
                and measured["native_2q"] >= 1.35 * reference["native_2q"]
                and measured["swaps"] - reference["swaps"] >= 16}


def main():
    witness = load_witness(OUTPUT / "authorized_champion.json")
    configurations = [
        {"width": 64, "max_swaps": 16, "objective": "unique_pairs", "progress_weight": 0.0},
        {"width": 256, "max_swaps": 16, "objective": "unique_pairs", "progress_weight": 0.0},
        {"width": 64, "max_swaps": 16, "objective": "layer_sum", "progress_weight": 0.0},
        {"width": 256, "max_swaps": 16, "objective": "unique_pairs", "progress_weight": 0.25},
    ]
    started = time.monotonic()
    cases = [(witness, configuration, family) for configuration in configurations for family in relabelings(16)]
    with multiprocessing.get_context("fork").Pool(8) as pool:
        results = list(pool.imap_unordered(run_case, cases))
    grouped = []
    for configuration in configurations:
        rows = sorted((row for row in results if row["configuration"] == configuration),
                      key=lambda row: row["family"])
        grouped.append({"configuration": configuration, "families": rows,
                        "worst_swaps": max(row["swaps"] for row in rows),
                        "all_champion_fail": not any(row["champion_meets_target"] for row in rows)})
    grouped.sort(key=lambda group: group["worst_swaps"])
    report = {"settings_tested": len(configurations), "routes_replayed": len(results),
              "seconds": time.monotonic() - started, "configurations": grouped}
    (OUTPUT / "beam_results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"settings_tested": len(configurations), "routes_replayed": len(results),
                      "seconds": report["seconds"],
                      "summaries": [{"configuration": group["configuration"],
                                     "swaps": [row["swaps"] for row in group["families"]],
                                     "success": [row["beam_succeeded"] for row in group["families"]]}
                                    for group in grouped]}), flush=True)


if __name__ == "__main__":
    main()
