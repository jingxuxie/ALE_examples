import argparse
import hashlib
import json
import multiprocessing
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "participant" / "input"))

from benchmark import evaluate_witness
from router import dependencies, relabelings, route, settings, transform
from validation import load_witness, replay, validate


def dump(path, content):
    path.write_text(json.dumps(content, indent=2) + "\n")


def run_case(case):
    witness, setting, family = case
    count, edges, gates, reference = validate(witness)
    name, logical, physical = family
    mapped_gates, mapped_edges, initial = transform(gates, edges, logical, physical)
    started = time.monotonic()
    if setting.get("implementation") == "general":
        from general_policy import route_general

        routed = route_general(mapped_gates, count, mapped_edges, initial, setting)
    else:
        routed = route(mapped_gates, count, mapped_edges, initial, setting)
    measured = replay(mapped_gates, count, mapped_edges, routed["route"], routed["final_mapping"], initial)
    assert measured["swaps"] == routed["swaps"]
    ratio = measured["swaps"] / reference["swaps"]
    native_ratio = measured["native_2q"] / reference["native_2q"]
    gap = measured["swaps"] - reference["swaps"]
    return {"family": name, "setting": setting, **measured,
            "fallback_swaps": routed["fallback_swaps"], "swap_ratio": ratio,
            "native_ratio": native_ratio, "swap_gap": gap,
            "champion_meets_target": ratio >= 2.5 and native_ratio >= 1.35 and gap >= 16,
            "seconds": time.monotonic() - started,
            "route": routed["route"], "final_mapping": routed["final_mapping"],
            "initial_mapping": initial}


def long_settings():
    result = []
    for horizon in (32, 64, 128, 200):
        for decay in (0.25, 0.5, 0.7, 0.85, 0.9, 0.95, 0.98, 1.0):
            for tie in ("ascending", "descending", "seeded"):
                result.append({"name": f"long-{horizon}-{decay}-{tie}", "horizon": horizon,
                               "decay": decay, "tie": tie, "mode": "weighted"})
        for tie in ("ascending", "descending", "seeded"):
            result.append({"name": f"long-lex-{horizon}-{tie}", "horizon": horizon,
                           "decay": 1.0, "tie": tie, "mode": "lexicographic"})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--general", action="store_true")
    parser.add_argument("--wide-parameters", action="store_true")
    arguments = parser.parse_args()
    started = time.monotonic()
    witness = load_witness(ROOT / "attempts" / "v_1.frozen" / "witness.json")
    count, edges, gates, reference = validate(witness)
    dump(OUTPUT / "authorized_champion.json", witness)
    if arguments.wide_parameters:
        configurations = []
        for horizon in (1, 2, 4, 8, 16, 32, 64, 128, 200):
            for decay in (0.0, 0.01, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.6, 0.8,
                          0.99, 0.995, 1.01, 1.05, 1.1, 1.2, 1.5, 2.0):
                for tie in ("ascending", "descending", "seeded"):
                    configurations.append({"name": f"wide-{horizon}-{decay}-{tie}",
                        "horizon": horizon, "decay": decay, "tie": tie, "mode": "weighted"})
        label = "wide_parameters"
    elif arguments.general:
        from general_policy import general_settings

        configurations = general_settings()
        label = "general"
    else:
        configurations = long_settings()
        label = "long_lookahead"
        dump(OUTPUT / "original_exact_score.json", evaluate_witness(witness))
    cases = [(witness, setting, family) for setting in configurations for family in relabelings(count)]
    context = multiprocessing.get_context("fork")
    with context.Pool(arguments.workers) as pool:
        results = list(pool.imap_unordered(run_case, cases))
    grouped = []
    for configuration in configurations:
        rows = sorted((row for row in results if row["setting"]["name"] == configuration["name"]),
                      key=lambda row: row["family"])
        grouped.append({"setting": configuration, "worst_swaps": max(row["swaps"] for row in rows),
                        "mean_swaps": sum(row["swaps"] for row in rows) / len(rows),
                        "best_swaps": min(row["swaps"] for row in rows),
                        "champion_fails_all_six": not any(row["champion_meets_target"] for row in rows),
                        "families": rows})
    grouped.sort(key=lambda entry: (entry["worst_swaps"], entry["mean_swaps"], entry["best_swaps"]))
    portfolio = []
    for family, _, _ in relabelings(count):
        rows = [row for row in results if row["family"] == family]
        portfolio.append(min(rows, key=lambda row: row["swaps"]))
    predecessors, _ = dependencies(gates, count)
    depths = []
    for parents in predecessors:
        depths.append(max((depths[parent] + 1 for parent in parents), default=0))
    report = {"search": label, "settings_tested": len(configurations), "routes_replayed": len(results),
              "seconds": time.monotonic() - started, "reference": reference,
              "gate_count": len(gates), "initial_DAG_layers": max(depths) + 1,
              "best_single_configuration": grouped[0], "best_portfolio_by_family": portfolio,
              "all_configurations": grouped,
              "champion_sha256": hashlib.sha256((ROOT / "attempts/v_1.frozen/witness.json").read_bytes()).hexdigest(),
              "trusted_source_sha256": hashlib.sha256((ROOT / "participant/input/router.py").read_bytes()).hexdigest()}
    dump(OUTPUT / f"{label}_results.json", report)
    dump(OUTPUT / f"{label}_best_replayed_routes.json", grouped[0])
    print(json.dumps({"search": label, "settings_tested": len(configurations),
                      "routes_replayed": len(results), "seconds": report["seconds"],
                      "dag_layers": report["initial_DAG_layers"],
                      "best_single_setting": grouped[0]["setting"],
                      "best_single_counts": [row["swaps"] for row in grouped[0]["families"]],
                      "portfolio_counts": [row["swaps"] for row in portfolio]}), flush=True)


if __name__ == "__main__":
    main()
