import argparse
import ctypes
import hashlib
import json
import math
import multiprocessing
import os
import random
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "adversary" / "private_candidates"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "participant" / "input"))

from router import hardware, relabelings, route, settings, transform
from validation import InvalidWitness, replay, validate


def dump(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n")
    temporary.replace(path)


def source_hashes():
    paths = [ROOT / "participant" / "input" / name
             for name in ("router.py", "benchmark.py", "validation.py")]
    paths.append(ROOT / "evaluator" / "evaluate.py")
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths}


class FastPortfolio:
    def __init__(self):
        self.library = ctypes.CDLL(str(ROOT / "adversary" / "private_search_router.so"))
        pointer = ctypes.POINTER(ctypes.c_int)
        self.library.count_swaps.argtypes = [ctypes.c_int, pointer, ctypes.c_int,
                                             pointer, pointer, ctypes.c_int,
                                             ctypes.c_double, ctypes.c_int, pointer]
        self.library.count_swaps.restype = ctypes.c_int
        self.configurations = settings()
        self.prepared = {}
        self.route_runs = 0
        for graph in ("ring16", "ladder16", "grid16"):
            count, edges = hardware(graph)
            families = []
            for name, logical, physical in relabelings(count):
                _, mapped_edges, initial = transform([], edges, logical, physical)
                edge_array = self.array([node for edge in mapped_edges for node in edge])
                initial_array = self.array(initial)
                ranked = []
                for setting in self.configurations:
                    assert setting["mode"] in ("weighted", "lexicographic")
                    assert setting["horizon"] <= 32
                    ordered = mapped_edges[:]
                    if setting["tie"] == "descending":
                        ordered.reverse()
                    elif setting["tie"] == "seeded":
                        random.Random(1729).shuffle(ordered)
                    else:
                        assert setting["tie"] == "ascending"
                    ranks = {edge: index for index, edge in enumerate(ordered)}
                    ranked.append(self.array([ranks[edge] for edge in mapped_edges]))
                families.append((name, logical, edge_array, initial_array, ranked, mapped_edges))
            self.prepared[graph] = families

    @staticmethod
    def array(values):
        return (ctypes.c_int * len(values))(*values)

    def count(self, gate_array, gate_count, family, setting_index):
        _, _, edges, initial, ranked, mapped_edges = family
        setting = self.configurations[setting_index]
        self.route_runs += 1
        return self.library.count_swaps(gate_count, gate_array, len(mapped_edges), edges,
                                         initial, setting["horizon"], setting["decay"],
                                         int(setting["mode"] == "lexicographic"),
                                         ranked[setting_index])

    def score(self, witness, cutoff=0.0, order_seed=0):
        gate_count = len(witness["gates"])
        swaps = sum(operation[0] == "swap" for operation in witness["route"])
        required = math.ceil(max(2.5 * swaps, swaps + 16,
                                 (1.35 * (gate_count + 3 * swaps) - gate_count) / 3) - 1e-10)
        minimum = float("inf")
        family_minima = []
        all_counts = []
        family_order = list(range(len(self.prepared[witness["hardware"]])))
        family_order = family_order[order_seed % len(family_order):] + family_order[:order_seed % len(family_order)]
        setting_order = list(range(len(self.configurations)))
        preferred = [0, 1, 4, 5, 8, 9, len(setting_order) - 2, len(setting_order) - 1]
        setting_order = list(dict.fromkeys(preferred + setting_order))
        for family_index in family_order:
            family = self.prepared[witness["hardware"]][family_index]
            logical = family[1]
            gate_array = self.array([logical[qubit] for gate in witness["gates"] for qubit in gate])
            best = float("inf")
            for setting_index in setting_order:
                routed = self.count(gate_array, gate_count, family, setting_index)
                best = min(best, routed)
                minimum = min(minimum, routed)
                all_counts.append(routed)
                if minimum / required + 1e-12 < cutoff:
                    return None
            family_minima.append(best)
        primary = minimum / required
        secondary = sum(family_minima) / len(family_minima) / required
        tertiary = sum(all_counts) / len(all_counts) / required
        return (primary, secondary, tertiary), family_minima, swaps, required


def decode(graph, genome, repair=True):
    count, edges = hardware(graph)
    occupants = list(range(count))
    position = list(range(count))
    previous = [-1] * count
    coverage = [0] * count
    repeated = Counter()
    operations, gates, repaired = [], [], []
    gate_count = sum(token >= 0 for token in genome)
    cap = min(40, (4 * gate_count + count - 1) // count)
    for token in genome:
        if token < 0:
            edge_index = (-token - 1) % len(edges)
            left, right = edges[edge_index]
            first, second = occupants[left], occupants[right]
            occupants[left], occupants[right] = second, first
            position[first], position[second] = right, left
            operations.append(["swap", left, right])
            repaired.append(-edge_index - 1)
            continue
        chosen = None
        for offset in range(len(edges) if repair else 1):
            edge_index = (token + offset) % len(edges)
            left, right = edges[edge_index]
            first, second = occupants[left], occupants[right]
            if previous[first] == previous[second] and previous[first] != -1:
                continue
            if repeated[tuple(sorted((first, second)))] >= 8:
                continue
            if coverage[first] >= cap or coverage[second] >= cap:
                continue
            chosen = edge_index
            break
        if chosen is None:
            return None
        left, right = edges[chosen]
        if len(gates) % 2:
            left, right = right, left
        first, second = occupants[left], occupants[right]
        index = len(gates)
        gates.append([first, second])
        operations.append(["gate", index, left, right])
        previous[first] = previous[second] = index
        coverage[first] += 1
        coverage[second] += 1
        repeated[tuple(sorted((first, second)))] += 1
        repaired.append(chosen)
    witness = {"version": 1, "hardware": graph, "gates": gates,
               "route": operations, "final_mapping": position}
    try:
        validate(witness)
    except (InvalidWitness, ValueError):
        return None
    return witness, repaired


def initial_genome(generator, graph, gate_count, swap_count):
    _, edges = hardware(graph)
    genome = [generator.randrange(len(edges)) for _ in range(gate_count)]
    for _ in range(swap_count):
        slot = generator.randrange(len(genome))
        genome.insert(slot, -generator.randrange(len(edges)) - 1)
    return genome


def mutate(generator, graph, genome):
    _, edges = hardware(graph)
    mutated = genome[:]
    changes = generator.choices((1, 2, 3, 5, 8), weights=(50, 25, 15, 7, 3))[0]
    for _ in range(changes):
        index = generator.randrange(len(mutated))
        draw = generator.random()
        if draw < 0.45:
            replacement = generator.randrange(len(edges))
            mutated[index] = replacement if mutated[index] >= 0 else -replacement - 1
        elif draw < 0.73:
            destination = max(0, min(len(mutated) - 1, index + generator.randint(-12, 12)))
            token = mutated.pop(index)
            mutated.insert(destination, token)
        elif draw < 0.9:
            second = generator.randrange(len(mutated))
            mutated[index], mutated[second] = mutated[second], mutated[index]
        elif draw < 0.94 and sum(token < 0 for token in mutated) > 8:
            swaps = [slot for slot, token in enumerate(mutated) if token < 0]
            del mutated[generator.choice(swaps)]
        elif draw < 0.97 and sum(token < 0 for token in mutated) < 24:
            mutated.insert(index, -generator.randrange(len(edges)) - 1)
        elif draw < 0.985 and sum(token >= 0 for token in mutated) > 48:
            gates = [slot for slot, token in enumerate(mutated) if token >= 0]
            del mutated[generator.choice(gates)]
        elif sum(token >= 0 for token in mutated) < 160:
            mutated.insert(index, generator.randrange(len(edges)))
    return mutated


def parity_test():
    fast = FastPortfolio()
    tested = 0
    mismatches = []
    started = time.monotonic()
    for graph in ("ring16", "ladder16", "grid16"):
        count, edges = hardware(graph)
        for seed in (19, 31):
            generator = random.Random(seed)
            gates = [generator.sample(range(count), 2) for _ in range(64)]
            for family_index in (0, 1, 5):
                name, logical, physical = relabelings(count)[family_index]
                mapped_gates, mapped_edges, initial = transform(gates, edges, logical, physical)
                gate_array = fast.array([qubit for gate in mapped_gates for qubit in gate])
                for setting_index, setting in enumerate(settings()):
                    trusted = route(mapped_gates, count, mapped_edges, initial, setting)
                    replay(mapped_gates, count, mapped_edges, trusted["route"], trusted["final_mapping"], initial)
                    accelerated = fast.count(gate_array, len(gates), fast.prepared[graph][family_index], setting_index)
                    tested += 1
                    if accelerated != trusted["swaps"]:
                        mismatches.append({"graph": graph, "seed": seed, "family": name,
                                           "setting": setting, "trusted": trusted["swaps"],
                                           "accelerated": accelerated})
    result = {"tested": tested, "mismatches": mismatches,
              "passed": not mismatches, "seconds": time.monotonic() - started,
              "source_hashes": source_hashes(), "settings": settings()}
    dump(ROOT / "adversary" / "private_search_parity.json", result)
    print(json.dumps({"parity_tested": tested, "mismatches": len(mismatches),
                      "seconds": result["seconds"]}), flush=True)
    if mismatches:
        raise RuntimeError("accelerated router disagrees with trusted router")


def worker(arguments):
    worker_id, seconds, seed = arguments
    started = time.monotonic()
    deadline = started + seconds
    generator = random.Random(seed + 100003 * worker_id)
    graph = ("ring16", "ladder16", "grid16")[worker_id % 3]
    initial_gates = (64, 80, 96, 112)[(worker_id // 3) % 4]
    initial_swaps = (10, 12, 14)[(worker_id // 6) % 3]
    fast = FastPortfolio()
    statistics = {"worker": worker_id, "seed": seed + 100003 * worker_id,
                  "graph": graph, "generated": 0, "valid": 0,
                  "screened_out": 0, "full_scored": 0, "accepted": 0,
                  "improvements": 0, "restarts": 0}
    best = None
    current = None
    elites = []
    last_improvement = started
    last_checkpoint = started
    while time.monotonic() < deadline:
        if current is None:
            genome = initial_genome(generator, graph, initial_gates, initial_swaps)
        else:
            if generator.random() < 0.10 and elites:
                parent = generator.choice(elites)
            else:
                parent = current
            genome = mutate(generator, graph, parent[1])
        statistics["generated"] += 1
        decoded = decode(graph, genome)
        if decoded is None:
            continue
        witness, genome = decoded
        statistics["valid"] += 1
        if current is None:
            cutoff = 0
        else:
            temperature = 0.018 + 0.045 * (1 - (time.monotonic() - started) / seconds)
            cutoff = parent[0][0] + temperature * math.log(max(1e-9, generator.random()))
        scored = fast.score(witness, cutoff, statistics["valid"])
        if scored is None:
            statistics["screened_out"] += 1
        else:
            metrics, family_counts, swaps, required = scored
            statistics["full_scored"] += 1
            entry = (metrics, genome, witness)
            if current is None or metrics >= current[0] or metrics[0] >= cutoff:
                current = entry
                statistics["accepted"] += 1
            if best is None or metrics > best[0]:
                best = entry
                statistics["improvements"] += 1
                last_improvement = time.monotonic()
                directory = PRIVATE / f"island_{worker_id:02d}"
                dump(directory / "witness.json", witness)
                dump(directory / "genome.json", genome)
                dump(directory / "search_summary.json", {**statistics,
                     "proxy_metrics": metrics, "proxy_family_counts": family_counts,
                     "reference_swaps": swaps, "required_portfolio_swaps": required,
                     "route_runs": fast.route_runs, "seconds": time.monotonic() - started,
                     "note": "Private accelerated screening only; exact checker decides validity and pass."})
            if not elites or metrics >= elites[-1][0]:
                elites.append(entry)
                elites.sort(key=lambda item: item[0], reverse=True)
                elites = elites[:16]
        if best is not None and time.monotonic() - last_improvement > 60:
            statistics["restarts"] += 1
            current = best if generator.random() < 0.6 else None
            last_improvement = time.monotonic()
        if time.monotonic() - last_checkpoint > 30:
            dump(ROOT / "adversary" / f"private_search_worker_{worker_id:02d}.json",
                 {**statistics, "route_runs": fast.route_runs,
                  "best_proxy": None if best is None else best[0],
                  "seconds": time.monotonic() - started})
            last_checkpoint = time.monotonic()
    result = {**statistics, "route_runs": fast.route_runs,
              "best_proxy": None if best is None else best[0],
              "seconds": time.monotonic() - started}
    dump(ROOT / "adversary" / f"private_search_worker_{worker_id:02d}.json", result)
    return result


def finalize():
    expected_target = {"swap_ratio": 2.5, "native_ratio": 1.35, "swap_gap": 16}
    initial_record = json.loads((ROOT / "adversary" / "private_search_run.json").read_text())
    summaries = [json.loads(path.read_text()) for path in sorted(
        (ROOT / "adversary").glob("private_search_worker_*.json"))]
    results = []
    for directory in sorted(PRIVATE.glob("island_*")):
        if not (directory / "witness.json").exists():
            continue
        process = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "evaluator" / "evaluate.py"),
                                  "--solution-dir", str(directory)], capture_output=True,
                                 text=True, timeout=180, cwd=ROOT)
        if process.returncode != 0:
            raise RuntimeError(process.stderr)
        result = json.loads(process.stdout)
        if result.get("valid"):
            assert result["target"] == expected_target
            assert all(len({setting["setting"] for setting in family["settings"]}) == len(family["settings"])
                       for family in result["families"])
        dump(directory / "exact_result.json", result)
        results.append({"directory": str(directory.relative_to(ROOT)), "result": result})
    def exact_rank(entry):
        result = entry["result"]
        margin = min((min(family["swap_ratio"] / 2.5, family["native_ratio"] / 1.35,
                          family["swap_gap"] / 16) for family in result.get("families", [])), default=0)
        return result["passed"], result["worst_family_score"], margin, result["core_score"]

    results.sort(key=exact_rank, reverse=True)
    counts = [len(family["settings"]) for entry in results for family in entry["result"].get("families", [])]
    best = results[0] if results else None
    if best is not None:
        best_directory = PRIVATE / "best"
        dump(best_directory / "witness.json", json.loads(
            (ROOT / best["directory"] / "witness.json").read_text()))
        dump(best_directory / "exact_result.json", best["result"])
        best = {**best, "candidate_artifact": str((best_directory / "witness.json").relative_to(ROOT)),
                "sha256": hashlib.sha256((best_directory / "witness.json").read_bytes()).hexdigest()}
    final_hashes = source_hashes()
    final = {"source_hashes_final": final_hashes, "source_hashes_initial": initial_record["source_hashes"],
             "frozen_sources_unchanged": final_hashes == initial_record["source_hashes"], "workers": summaries,
             "number_generated": sum(entry["generated"] for entry in summaries),
             "number_validated": sum(entry["valid"] for entry in summaries),
             "number_full_proxy_scored": sum(entry["full_scored"] for entry in summaries),
             "number_early_screened": sum(entry["screened_out"] for entry in summaries),
             "number_proxy_route_runs": sum(entry["route_runs"] for entry in summaries),
             "number_exact_candidates": len(results), "requested_portfolio_settings": 36,
             "counting_note": "Counts are candidate trials, not distinct circuits; repeated mutations may recur.",
             "actual_portfolio_settings": sorted(set(counts)),
             "exact_routes_replayed_in_finalization": sum(counts),
             "portfolio_count_caveat": None if counts and all(count == 36 for count in counts)
                 else "The supplied exact checker exposes 18 settings, not the requested 36; no 36-setting pass is claimed.",
             "requested_36_configuration_validation_complete": bool(counts) and all(count == 36 for count in counts),
             "best": best, "all_exact_results": results,
             "truly_passes_supplied_exact_checker": bool(best and best["result"]["valid"] and best["result"]["passed"]),
             "requested_36_setting_pass_claim": bool(best and best["result"]["valid"] and best["result"]["passed"]
                 and counts and all(count == 36 for count in counts)),
             "targets_unchanged": {"swap_ratio": 2.5, "native_ratio": 1.35, "swap_gap": 16},
             "fresh_launches": 0, "inspected_fresh_outputs": False}
    dump(ROOT / "adversary" / "private_search_result.json", final)
    dump(ROOT / "evaluator" / "hidden" / "private_search_result.json", final)
    print(json.dumps({"finalized": True, "tested": final["number_validated"],
                      "settings": final["actual_portfolio_settings"],
                      "best_artifact": None if best is None else best["directory"] + "/witness.json",
                      "exact_passed": None if best is None else best["result"]["passed"],
                      "exact_worst_score": None if best is None else best["result"]["worst_family_score"]}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=900)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--seed", type=int, default=28082026)
    parser.add_argument("--parity-only", action="store_true")
    parser.add_argument("--finalize-only", action="store_true")
    arguments = parser.parse_args()
    PRIVATE.mkdir(parents=True, exist_ok=True)
    if arguments.finalize_only:
        finalize()
        return
    parity_test()
    if arguments.parity_only:
        return
    dump(ROOT / "adversary" / "private_search_run.json",
         {"started_unix": time.time(), "seconds": arguments.seconds,
          "workers": arguments.workers, "source_hashes": source_hashes(),
          "settings": settings(), "requested_settings": 36})
    context = multiprocessing.get_context("fork")
    with context.Pool(arguments.workers) as pool:
        for result in pool.imap_unordered(worker, [(worker_id, arguments.seconds, arguments.seed)
                                                  for worker_id in range(arguments.workers)]):
            print(json.dumps(result), flush=True)
    finalize()


if __name__ == "__main__":
    main()
