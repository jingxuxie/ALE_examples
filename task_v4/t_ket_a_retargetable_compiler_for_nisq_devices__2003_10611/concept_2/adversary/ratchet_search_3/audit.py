import argparse
import concurrent.futures
import hashlib
import json
import multiprocessing
import random
import sys
import time
from pathlib import Path


sys.dont_write_bytecode = True
OUTPUT = Path(__file__).resolve().parent
CONCEPT = OUTPUT.parents[1]
GENERATION = CONCEPT / "adversary/generation_3"
sys.path.insert(0, str(GENERATION / "participant/input"))

import benchmark
from router import relabelings, settings
from validation import load_witness, validate


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def frozen_hashes():
    paths = set()
    for directory in ("participant", "evaluator"):
        paths.update(path for path in (GENERATION / directory).rglob("*") if path.is_file())
    paths.update(GENERATION / name for name in ("adversary/freeze.json", "adversary/frozen_manifest.json"))
    return {str(path.relative_to(GENERATION)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)}


def additional_families(count):
    result = []
    for kind, seeds in (("logical", [1009 + 37 * index for index in range(11)]),
                        ("physical", [2003 + 41 * index for index in range(11)]),
                        ("joint", [3001 + 43 * index for index in range(10)])):
        for seed in seeds:
            generator = random.Random(seed)
            logical, physical = list(range(count)), list(range(count))
            if kind in ("logical", "joint"):
                generator.shuffle(logical)
            if kind in ("physical", "joint"):
                generator.shuffle(physical)
            result.append((f"additional-{kind}-{seed}", logical, physical))
    assert len(result) == 32
    assert len({(tuple(logical), tuple(physical)) for _, logical, physical in result}) == 32
    public = {(tuple(logical), tuple(physical)) for _, logical, physical in relabelings(count)}
    assert not public.intersection((tuple(logical), tuple(physical)) for _, logical, physical in result)
    return result


def evaluate_family(payload):
    family, witness = payload
    started = time.monotonic()
    benchmark.relabelings = lambda count: [family]
    result = benchmark.evaluate_witness(witness)
    assert len(result["families"]) == 1
    assert len(result["families"][0]["settings"]) == 62
    record = {"family": family[0], "logical": family[1], "physical": family[2],
              "seconds": time.monotonic() - started, "portfolio_routes_replayed": 62,
              "reference_routes_replayed": 1, "result": result}
    write_json(OUTPUT / "additional_families" / f"{family[0]}.json", record)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    arguments = parser.parse_args()
    started = time.monotonic()
    source = CONCEPT / "attempts/v_3.frozen/witness.json"
    witness = load_witness(source)
    count, edges, gates, reference = validate(witness)
    write_json(OUTPUT / "authorized_champion.json", witness)
    families = additional_families(count)
    before = frozen_hashes()
    manifest = json.loads((GENERATION / "adversary/frozen_manifest.json").read_text())
    assert all(before[name] == expected for name, expected in manifest.items())
    write_json(OUTPUT / "audit_parameters.json", {
        "started_unix": time.time(), "scope": "private audit; G3 score unchanged",
        "champion_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "families": families, "settings": settings(), "frozen_hashes_before": before,
        "targets": {"swap_ratio": 2.5, "native_ratio": 1.35, "swap_gap": 16},
        "window_repair": {"tail_trims": list(range(1, 9)), "cutoff_step": 4,
                          "prefix_tail_horizon": 16, "prefix_tail_decay": 0.9,
                          "prefix_tail_tie": "ascending", "embedding_budget": 12000,
                          "token_budget": 2500},
    })
    records = []
    context = multiprocessing.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(max_workers=arguments.workers, mp_context=context) as pool:
        futures = [pool.submit(evaluate_family, (family, witness)) for family in families]
        for future in concurrent.futures.as_completed(futures):
            record = future.result()
            records.append(record)
            measured = record["result"]["families"][0]
            print(json.dumps({"completed": len(records), "family": record["family"],
                              "portfolio_swaps": measured["portfolio_swaps"],
                              "passed": record["result"]["passed"], "seconds": record["seconds"]}), flush=True)
    after = frozen_hashes()
    assert before == after
    records.sort(key=lambda record: record["family"])
    measured = [record["result"]["families"][0] for record in records]
    summary = {"audit": "fixed G3 policies on 32 additional deterministic relabelings",
               "valid": all(record["result"]["valid"] for record in records),
               "targets_survive_all_additional_families": all(record["result"]["passed"] for record in records),
               "families_requested": 32, "families_completed": len(records),
               "families_passed": sum(record["result"]["passed"] for record in records),
               "portfolio_routes_replayed": sum(record["portfolio_routes_replayed"] for record in records),
               "reference_routes_replayed": sum(record["reference_routes_replayed"] for record in records),
               "gate_count": len(gates), "reference": reference,
               "minimum_portfolio_swaps": min(family["portfolio_swaps"] for family in measured),
               "maximum_portfolio_swaps": max(family["portfolio_swaps"] for family in measured),
               "minimum_swap_ratio": min(family["swap_ratio"] for family in measured),
               "minimum_native_ratio": min(family["native_ratio"] for family in measured),
               "minimum_swap_gap": min(family["swap_gap"] for family in measured),
               "worst_family_score": min(family["score"] for family in measured),
               "core_score": sum(family["score"] for family in measured) / len(measured),
               "seconds": time.monotonic() - started, "frozen_artifacts_unchanged": before == after,
               "families": records, "official_G3_score_changed": False, "fresh_agents_launched": 0}
    write_json(OUTPUT / "robustness_summary.json", summary)
    print(json.dumps({key: value for key, value in summary.items() if key != "families"}), flush=True)


if __name__ == "__main__":
    main()
