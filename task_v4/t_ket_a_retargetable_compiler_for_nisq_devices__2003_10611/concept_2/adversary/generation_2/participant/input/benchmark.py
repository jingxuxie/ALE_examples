import argparse
import json
from pathlib import Path

from router import relabelings, route, settings, transform
from validation import load_witness, replay, validate


TARGET_SWAP_RATIO = 2.5
TARGET_NATIVE_RATIO = 1.35
TARGET_SWAP_GAP = 16


def invalid_result(reason):
    return {"core_score": 0.0, "worst_family_score": 0.0,
            "resource_score": 0.0, "passed": False, "valid": False, "reason": reason}


def evaluate_witness(witness):
    count, edges, gates, reference = validate(witness)
    families = []
    for name, logical, physical in relabelings(count):
        mapped_gates, mapped_edges, initial = transform(gates, edges, logical, physical)
        mapped_operations = []
        for operation in witness["route"]:
            if operation[0] == "swap":
                mapped_operations.append(["swap", physical[operation[1]], physical[operation[2]]])
            else:
                mapped_operations.append(["gate", operation[1], physical[operation[2]],
                                          physical[operation[3]]])
        final_mapping = [0] * count
        for qubit in range(count):
            final_mapping[logical[qubit]] = physical[witness["final_mapping"][qubit]]
        replay(mapped_gates, count, mapped_edges, mapped_operations, final_mapping, initial)
        results = []
        for setting in settings():
            routed = route(mapped_gates, count, mapped_edges, initial, setting)
            measured = replay(mapped_gates, count, mapped_edges, routed["route"],
                              routed["final_mapping"], initial)
            if measured["swaps"] != routed["swaps"]:
                raise RuntimeError("trusted router cost mismatch")
            results.append({"setting": setting["name"], **measured,
                            "fallback_swaps": routed["fallback_swaps"]})
        best = min(results, key=lambda result: result["swaps"])
        ratio = best["swaps"] / reference["swaps"]
        native_ratio = best["native_2q"] / reference["native_2q"]
        gap = best["swaps"] - reference["swaps"]
        score = max(0.0, min(1.0, (ratio - 1) / (TARGET_SWAP_RATIO - 1),
                             (native_ratio - 1) / (TARGET_NATIVE_RATIO - 1),
                             gap / TARGET_SWAP_GAP))
        families.append({"name": name, "best_setting": best["setting"],
                         "portfolio_swaps": best["swaps"], "swap_ratio": ratio,
                         "native_ratio": native_ratio, "swap_gap": gap,
                         "score": score, "settings": results})
    worst = min(family["score"] for family in families)
    passed = all(family["swap_ratio"] >= TARGET_SWAP_RATIO
                 and family["native_ratio"] >= TARGET_NATIVE_RATIO
                 and family["swap_gap"] >= TARGET_SWAP_GAP for family in families)
    return {"core_score": sum(family["score"] for family in families) / len(families),
            "worst_family_score": worst, "resource_score": worst,
            "passed": passed, "valid": True,
            "reason": "robust portfolio counterexample" if passed else "valid route; target not met",
            "reference": reference, "gate_count": len(gates), "families": families,
            "target": {"swap_ratio": TARGET_SWAP_RATIO, "native_ratio": TARGET_NATIVE_RATIO,
                       "swap_gap": TARGET_SWAP_GAP}}


def evaluate_file(path):
    try:
        return evaluate_witness(load_witness(path))
    except (ValueError, TypeError, KeyError, IndexError, OSError, RecursionError) as error:
        return invalid_result(str(error))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("witness", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(evaluate_file(arguments.witness), sort_keys=True))


if __name__ == "__main__":
    main()
