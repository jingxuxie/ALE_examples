import hashlib
import json
import multiprocessing
import sys
import time
from pathlib import Path


OUTPUT = Path(__file__).resolve().parent
CONCEPT = OUTPUT.parents[1]
GENERATION_TWO = CONCEPT / "adversary/generation_2"
sys.dont_write_bytecode = True
sys.path.insert(0, str(GENERATION_TWO / "participant/input"))

from embedding import suffix_route
from router import dependencies, relabelings, route, transform
from validation import load_witness, replay, validate


def configurations():
    result = []
    for horizon in (4, 8, 16, 32, 64, 200):
        for weight in (1.1, 1.5, 2.0):
            for tie in ("ascending", "seeded"):
                result.append({"name": f"future-{horizon}-{weight}-{tie}",
                               "horizon": horizon, "decay": weight, "tie": tie,
                               "mode": "weighted"})
    result.append({"name": "suffix-embedding-all-program", "horizon": 0,
                   "decay": 1.0, "tie": "ascending", "mode": "embedding-all-program"})
    return result


def run_case(case):
    witness, setting, family = case
    count, edges, gates, reference = validate(witness)
    name, logical, physical = family
    mapped_gates, mapped_edges, initial = transform(gates, edges, logical, physical)
    started = time.monotonic()
    if setting["mode"] == "embedding-all-program":
        routed = suffix_route(mapped_gates, count, mapped_edges, initial,
                              cutoffs=range(0, len(gates), 4))
    else:
        routed = route(mapped_gates, count, mapped_edges, initial, setting)
    measured = replay(mapped_gates, count, mapped_edges, routed["route"], routed["final_mapping"], initial)
    assert measured["swaps"] == routed["swaps"]
    ratio = measured["swaps"] / reference["swaps"]
    native_ratio = measured["native_2q"] / reference["native_2q"]
    gap = measured["swaps"] - reference["swaps"]
    return {"family": name, "setting": setting, **routed,
            "initial_mapping": initial, "seconds": time.monotonic() - started,
            "swap_ratio": ratio, "native_ratio": native_ratio, "swap_gap": gap,
            "champion_passes": ratio >= 2.5 and native_ratio >= 1.35 and gap >= 16,
            "replay_valid": True}


def main():
    started = time.monotonic()
    source = CONCEPT / "attempts/v_2.frozen/witness.json"
    witness = load_witness(source)
    count, edges, gates, reference = validate(witness)
    (OUTPUT / "authorized_champion.json").write_bytes(source.read_bytes())
    settings = configurations()
    cases = [(witness, setting, family) for setting in settings for family in relabelings(count)]
    with multiprocessing.get_context("fork").Pool(8) as pool:
        results = list(pool.imap_unordered(run_case, cases))
    grouped = []
    for setting in settings:
        rows = sorted((row for row in results if row["setting"] == setting), key=lambda row: row["family"])
        grouped.append({"setting": setting, "families": rows,
                        "worst_swaps": max(row["swaps"] for row in rows),
                        "mean_swaps": sum(row["swaps"] for row in rows) / len(rows)})
    grouped.sort(key=lambda row: (row["worst_swaps"], row["mean_swaps"]))
    winners = []
    for name, _, _ in relabelings(count):
        winners.append(min((row for row in results if row["family"] == name), key=lambda row: row["swaps"]))
    predecessors, _ = dependencies(gates, count)
    depths = []
    for parents in predecessors:
        depths.append(max((depths[parent] + 1 for parent in parents), default=0))
    final_mapping = witness["final_mapping"]
    edge_set = set(edges)
    nonnative = [index for index, (left, right) in enumerate(gates)
                 if tuple(sorted((final_mapping[left], final_mapping[right]))) not in edge_set]
    report = {"new_settings_tested": len(settings), "routes_replayed": len(results),
              "seconds": time.monotonic() - started, "reference": reference,
              "gate_count": len(gates), "DAG_layers": max(depths) + 1,
              "last_gate_nonnative_in_reference_final_mapping": max(nonnative, default=-1),
              "distinct_pairs_by_cut": {str(cut): len({tuple(sorted(gate)) for gate in gates[cut:]})
                                        for cut in range(0, len(gates), 4)},
              "best_by_family": winners, "configurations": grouped,
              "repair_confirmed": all(row["swaps"] <= 23 and not row["champion_passes"] for row in winners),
              "champion_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "source_hashes": {name: hashlib.sha256((GENERATION_TWO / "participant/input" / name).read_bytes()).hexdigest()
                                for name in ("router.py", "embedding.py", "benchmark.py", "validation.py")},
              "frozen_G2_modified": False, "generation_3_built": False}
    (OUTPUT / "probe_results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"repair_confirmed": report["repair_confirmed"], "routes_replayed": len(results),
                      "seconds": report["seconds"], "DAG_layers": report["DAG_layers"],
                      "last_nonnative_gate": report["last_gate_nonnative_in_reference_final_mapping"],
                      "best_by_family": [{"family": row["family"], "swaps": row["swaps"],
                                          "setting": row["setting"]["name"],
                                          "cutoff": row.get("embedding_cutoff")} for row in winners],
                      "best_single": grouped[0]["setting"],
                      "best_single_counts": [row["swaps"] for row in grouped[0]["families"]]}), flush=True)


if __name__ == "__main__":
    main()
