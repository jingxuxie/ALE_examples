import argparse
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "participant" / "input"))

from router import relabelings, route, settings, transform
from validation import load_witness, replay, validate


def trajectory(witness):
    occupants = list(range(16))
    moves = [0] * 16
    swaps = []
    completed = 0
    for operation in witness["route"]:
        if operation[0] == "swap":
            left, right = operation[1:]
            first, second = occupants[left], occupants[right]
            occupants[left], occupants[right] = second, first
            moves[first] += 1
            moves[second] += 1
            swaps.append({"after_gates": completed, "physical_edge": [left, right],
                          "logical_operands": [first, second]})
        else:
            completed += 1
    return {"logical_moves": moves, "swap_locations": swaps}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--extra-families", type=int, default=32)
    arguments = parser.parse_args()
    started = time.monotonic()
    witness = load_witness(arguments.candidate)
    count, edges, gates, reference = validate(witness)
    coverage = Counter(qubit for gate in gates for qubit in gate)
    pairs = Counter(tuple(sorted(gate)) for gate in gates)
    partners = [set() for _ in range(count)]
    for left, right in gates:
        partners[left].add(right)
        partners[right].add(left)
    settings_by_name = {setting["name"]: setting for setting in settings()}
    official_result_path = arguments.candidate.parent / "exact_result.json"
    if not official_result_path.exists():
        official_result_path = arguments.candidate.parent / "result.json"
    official = json.loads(official_result_path.read_text())
    families_by_name = {family["name"]: family for family in official["families"]}
    winners = []
    for name, logical, physical in relabelings(count):
        mapped_gates, mapped_edges, initial = transform(gates, edges, logical, physical)
        official_family = families_by_name[name]
        setting = settings_by_name[official_family["best_setting"]]
        routed = route(mapped_gates, count, mapped_edges, initial, setting)
        measured = replay(mapped_gates, count, mapped_edges, routed["route"], routed["final_mapping"], initial)
        assert measured["swaps"] == official_family["portfolio_swaps"]
        winners.append({"family": name, "setting": setting["name"], **measured,
                        "fallback_swaps": routed["fallback_swaps"]})
    extra = []
    for index in range(arguments.extra_families):
        generator = random.Random(910000 + index)
        logical, physical = list(range(count)), list(range(count))
        generator.shuffle(logical)
        generator.shuffle(physical)
        mapped_gates, mapped_edges, initial = transform(gates, edges, logical, physical)
        results = []
        for setting in settings():
            routed = route(mapped_gates, count, mapped_edges, initial, setting)
            measured = replay(mapped_gates, count, mapped_edges, routed["route"], routed["final_mapping"], initial)
            results.append({"setting": setting["name"], **measured,
                            "fallback_swaps": routed["fallback_swaps"]})
        best = min(results, key=lambda result: result["swaps"])
        ratio = best["swaps"] / reference["swaps"]
        native_ratio = best["native_2q"] / reference["native_2q"]
        gap = best["swaps"] - reference["swaps"]
        extra.append({"seed": 910000 + index, "best": best, "settings_tested": len(results),
                      "swap_ratio": ratio, "native_ratio": native_ratio, "swap_gap": gap,
                      "meets_frozen_numeric_targets": ratio >= 2.5 and native_ratio >= 1.35 and gap >= 16})
    diagnostics = {"candidate_artifact": str(arguments.candidate.relative_to(ROOT))
                   if arguments.candidate.is_absolute() else str(arguments.candidate),
                   "hardware": witness["hardware"], "gates": len(gates),
                   "reference": reference, "reference_structure": trajectory(witness),
                   "wire_gate_counts": dict(coverage), "wire_partner_counts": list(map(len, partners)),
                   "distinct_interaction_pairs": len(pairs), "max_pair_repetition": max(pairs.values()),
                   "official_winners": winners, "supplementary_relabelings": extra,
                   "supplementary_all_meet_targets": all(family["meets_frozen_numeric_targets"] for family in extra),
                   "seconds": time.monotonic() - started,
                   "interpretation": "Winning-route fallback counts distinguish ordinary heuristic regret from progress-safeguard overhead. The reference is a feasible upper bound, not an optimality certificate. Extra relabelings are diagnostic only and do not change the frozen checker."}
    destination = arguments.candidate.parent / "diagnostics.json"
    destination.write_text(json.dumps(diagnostics, indent=2) + "\n")
    print(json.dumps({"diagnostics": str(destination),
                      "official_winner_fallbacks": [winner["fallback_swaps"] for winner in winners],
                      "extra_families": len(extra),
                      "extra_all_meet_targets": diagnostics["supplementary_all_meet_targets"],
                      "extra_worst_swap_ratio": min((family["swap_ratio"] for family in extra), default=None),
                      "extra_worst_native_ratio": min((family["native_ratio"] for family in extra), default=None)}), flush=True)


if __name__ == "__main__":
    main()
