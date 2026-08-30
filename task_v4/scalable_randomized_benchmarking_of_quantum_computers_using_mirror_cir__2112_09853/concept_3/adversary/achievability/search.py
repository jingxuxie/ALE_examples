import argparse
import copy
import hashlib
import heapq
import json
import math
import multiprocessing
import os
import random
import resource
import secrets
import subprocess
import sys
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "evaluator/hidden"))
from core import LOCAL_WORDS, circuit_weights, score_metrics, summarize, validate_submission
from design import matching


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def clone(layers):
    return [{"local": layer["local"][:], "cx": [gate[:] for gate in layer["cx"]]} for layer in layers]


def inverse_representative(layers):
    inverse_words = {"I": "I", "H": "H", "S": "S", "HS": "SH", "SH": "HS", "HSH": "HSH"}
    n = len(layers[0]["local"])
    result = []
    for position, source in enumerate(reversed(layers)):
        local = ["I"] * n if position == 0 else [inverse_words[word] for word in layers[len(layers) - position]["local"]]
        result.append({"local": local, "cx": [gate[:] for gate in source["cx"]]})
    return result


def metrics(family, layers, mean_multiplier):
    weights = circuit_weights(family["n"], layers)
    hard_loss = 0.0
    soft_loss = 0.0
    violations = 0
    ratios = []
    minima = []
    means = []
    failed_inputs = []
    for direction_index, strata in enumerate(weights):
        for kind, values in zip(("single", "double"), strata):
            target = family["targets"]["min_" + kind]
            mean_milli = family["targets"]["mean_" + kind + "_milli"]
            minimum = int(values.min())
            total = int(values.sum())
            deficit = np.maximum(0, target - values.astype(float))
            hard_loss += float((deficit * deficit).sum())
            violations += int(np.count_nonzero(deficit))
            mean_gap = max(0, mean_milli * len(values) - 1000 * total) / (1000 * len(values))
            hard_loss += mean_multiplier * mean_gap
            violations += int(mean_gap > 0)
            soft_loss += float(np.exp(-1.1 * (values.astype(float) - target)).sum())
            ratios.extend((minimum / target, 1000 * total / (mean_milli * len(values))))
            minima.append(minimum)
            means.append(total / len(values))
            failed_inputs.append(int(np.count_nonzero(deficit)))
    return {"loss": hard_loss + 0.003 * soft_loss, "hard_loss": hard_loss,
            "core_score": min(1.0, min(ratios)), "passed": violations == 0,
            "violations": violations, "minima": minima, "means": means,
            "failed_input_counts": failed_inputs}


def archive_key(measured):
    return measured["core_score"], -measured["violations"], -measured["hard_loss"], -measured["loss"]


def neighbors(layers, family, rng):
    locations = [(round_index, qubit) for round_index in range(1, len(layers)) for qubit in range(family["n"])]
    rng.shuffle(locations)
    for round_index, qubit in locations:
        alternatives = [word for word in LOCAL_WORDS if word != layers[round_index]["local"][qubit]]
        rng.shuffle(alternatives)
        for word in alternatives:
            candidate = clone(layers)
            candidate[round_index]["local"][qubit] = word
            yield candidate
    for round_index, layer in enumerate(layers):
        for gate_index, gate in enumerate(layer["cx"]):
            candidate = clone(layers)
            candidate[round_index]["cx"][gate_index].reverse()
            yield candidate
            occupied = {qubit for index, existing in enumerate(layer["cx"]) if index != gate_index for qubit in existing}
            for first, second in family["edges"]:
                if first in occupied or second in occupied or set((first, second)) == set(gate):
                    continue
                for oriented in ([first, second], [second, first]):
                    candidate = clone(layers)
                    candidate[round_index]["cx"][gate_index] = oriented
                    yield candidate


def mutation(layers, family, rng):
    candidate = clone(layers)
    round_index = rng.randrange(len(candidate))
    layer = candidate[round_index]
    choice = rng.random()
    if choice < 0.58:
        round_index = rng.randrange(1, len(candidate))
        for _ in range(1 if choice < 0.48 else 2):
            qubit = rng.randrange(family["n"])
            alternatives = [word for word in LOCAL_WORDS if word != candidate[round_index]["local"][qubit]]
            candidate[round_index]["local"][qubit] = rng.choice(alternatives)
    elif choice < 0.74:
        if layer["cx"]:
            rng.choice(layer["cx"]).reverse()
    elif choice < 0.90:
        if layer["cx"]:
            gate_index = rng.randrange(len(layer["cx"]))
            occupied = {qubit for index, gate in enumerate(layer["cx"]) if index != gate_index for qubit in gate}
            choices = [edge for edge in family["edges"] if not occupied.intersection(edge)]
            if choices:
                edge = rng.choice(choices)[:]
                if rng.randrange(2):
                    edge.reverse()
                layer["cx"][gate_index] = edge
    elif choice < 0.96:
        elsewhere = sum(len(entry["cx"]) for index, entry in enumerate(candidate) if index != round_index)
        layer["cx"] = matching(family, rng, family["max_cx"] - elsewhere)
    else:
        second = rng.randrange(len(candidate))
        candidate[round_index], candidate[second] = candidate[second], candidate[round_index]
    return candidate


def worker(worker_id, family, seeds, warmstarts, deadline, stop, run_directory):
    rng = random.Random(seeds[worker_id])
    run_directory = Path(run_directory)
    started = time.perf_counter()
    mean_multiplier = (80.0, 30.0, 100.0, 50.0)[worker_id]
    initial = clone(warmstarts[worker_id % len(warmstarts)])
    best = initial
    best_metrics = metrics(family, initial, mean_multiplier)
    best_key = archive_key(best_metrics)
    iterations = 0
    improvements = []
    last_saved = started
    current = initial
    current_metrics = best_metrics
    lowest = initial
    lowest_metrics = best_metrics

    def consider(candidate):
        nonlocal best, best_metrics, best_key, iterations, last_saved, lowest, lowest_metrics
        measured = metrics(family, candidate, mean_multiplier)
        iterations += 1
        if measured["loss"] < lowest_metrics["loss"]:
            lowest = candidate
            lowest_metrics = measured
        key = archive_key(measured)
        if key > best_key:
            best = candidate
            best_metrics = measured
            best_key = key
            improvements.append({"iteration": iterations, "runtime_seconds": time.perf_counter() - started, **measured})
        if measured["passed"]:
            best = candidate
            best_metrics = measured
            save(run_directory / f"worker_{worker_id}_passing_grid.json", {"family": family["id"], "layers": candidate})
            stop.set()
        if time.perf_counter() - last_saved > 20:
            progress = {"worker": worker_id, "iterations": iterations,
                        "runtime_seconds": time.perf_counter() - started, "best": best_metrics,
                        "lowest_loss": lowest_metrics["loss"]}
            save(run_directory / f"worker_{worker_id}_progress.json", progress)
            save(run_directory / f"worker_{worker_id}_best.json", {"family": family["id"], "layers": best})
            print(json.dumps(progress), flush=True)
            last_saved = time.perf_counter()
        return measured

    if worker_id == 0:
        beam = [initial]
        beam_depth = 0
        while beam and time.monotonic() < deadline and not stop.is_set() and beam_depth < 5:
            retained = []
            serial = 0
            for parent in beam:
                for candidate in neighbors(parent, family, rng):
                    if stop.is_set() or time.monotonic() >= deadline:
                        break
                    measured = consider(candidate)
                    serial += 1
                    entry = (-measured["loss"], serial, candidate)
                    if len(retained) < 20:
                        heapq.heappush(retained, entry)
                    elif entry[0] > retained[0][0]:
                        heapq.heapreplace(retained, entry)
            retained.sort(reverse=True)
            beam = [entry[2] for entry in retained]
            beam_depth += 1
        current = lowest
        current_metrics = lowest_metrics

    restart_period = (25000, 50000, 80000, 40000)[worker_id]
    start_temperature = (0.15, 1.2, 2.5, 0.6)[worker_id]
    while time.monotonic() < deadline and not stop.is_set():
        candidate = mutation(current, family, rng)
        if rng.random() < 0.015:
            for _ in range(rng.randint(1, 5)):
                candidate = mutation(candidate, family, rng)
        measured = consider(candidate)
        progress = (iterations % restart_period) / restart_period
        temperature = start_temperature * math.exp(-4.5 * progress)
        if measured["loss"] <= current_metrics["loss"] or rng.random() < math.exp(min(0, (current_metrics["loss"] - measured["loss"]) / temperature)):
            current = candidate
            current_metrics = measured
        if iterations % restart_period == 0:
            current = clone(best if rng.random() < 0.5 else lowest)
            for _ in range(rng.randint(2, 8)):
                current = mutation(current, family, rng)
            current_metrics = metrics(family, current, mean_multiplier)
    usage = resource.getrusage(resource.RUSAGE_SELF)
    result = {"worker": worker_id, "seed": str(seeds[worker_id]), "iterations": iterations,
              "runtime_seconds": time.perf_counter() - started,
              "cpu_seconds": usage.ru_utime + usage.ru_stime, "best": best_metrics,
              "mean_multiplier": mean_multiplier, "improvements": improvements,
              "stop_reason": "passing candidate discovered" if stop.is_set() else "time budget reached"}
    save(run_directory / f"worker_{worker_id}_result.json", result)
    save(run_directory / f"worker_{worker_id}_best.json", {"family": family["id"], "layers": best})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=1200)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--replay")
    args = parser.parse_args()
    if not 1 <= args.workers <= 4 or not 1 <= args.seconds <= 1500:
        parser.error("workers must be 1..4 and seconds 1..1500")
    started = time.monotonic()
    run_directory = WORK / ("run_" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "_" + str(os.getpid()))
    run_directory.mkdir()
    frozen_paths = [ROOT / "participant/input/spec.json", ROOT / "evaluator/hidden/frozen_spec.json",
                    ROOT / "evaluator/evaluate.py", ROOT / "evaluator/hidden/core.py"]
    frozen_hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in frozen_paths}
    spec = json.loads((ROOT / "evaluator/hidden/frozen_spec.json").read_text())
    family = next(family for family in spec["families"] if family["id"] == "grid20")
    if args.replay:
        original_config = json.loads(Path(args.replay).read_text())
        snapshot = json.loads((Path(args.replay).parent / "input_snapshot.json").read_text())
        seeds = [int(seed) for seed in original_config["seeds"]]
    else:
        template = json.loads((ROOT / "champions/best.json").read_text())
        alternative = json.loads((ROOT / "evaluator/hidden/grid_tight_result.json").read_text())["artifact"]
        snapshot = {"template": template, "alternative": alternative,
                    "read_sources": ["champions/best.json", "evaluator/hidden/grid_tight_result.json"]}
        seeds = [secrets.randbits(128) for _ in range(args.workers)]
    template = snapshot["template"]
    primary = next(circuit for circuit in template["circuits"] if circuit["family"] == "grid20")["layers"]
    alternative = snapshot["alternative"]["layers"]
    warmstarts = [primary, primary, inverse_representative(primary), alternative]
    direct = circuit_weights(family["n"], primary)
    inverted = circuit_weights(family["n"], warmstarts[2])
    for original, transformed in zip(direct, reversed(inverted)):
        for first, second in zip(original, transformed):
            if sorted(first.tolist()) != sorted(second.tolist()):
                raise RuntimeError("inverse representative does not preserve the swapped distributions")
    save(run_directory / "input_snapshot.json", snapshot)
    config = {"seconds": args.seconds, "workers": args.workers, "seeds": list(map(str, seeds)),
              "seed_sha256": [hashlib.sha256(str(seed).encode()).hexdigest() for seed in seeds],
              "family": family, "frozen_file_sha256": frozen_hashes,
              "search_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "methods": ["bounded beam neighborhood then annealing", "annealing from primary",
                          "annealing from inverse primary", "annealing from alternative"],
              "replay": args.replay, "numpy_version": np.__version__, "python_version": sys.version,
              "fresh_artifacts_read": False}
    save(run_directory / "config.json", config)
    print("RUN_DIRECTORY", run_directory, flush=True)
    context = multiprocessing.get_context("fork")
    stop = context.Event()
    processes = [context.Process(target=worker, args=(worker_id, family, seeds, warmstarts,
                 started + args.seconds, stop, str(run_directory))) for worker_id in range(args.workers)]
    for process in processes:
        process.start()
    for process in processes:
        process.join()
    if any(process.exitcode != 0 for process in processes):
        raise RuntimeError("private search worker failed")
    results = [json.loads((run_directory / f"worker_{worker_id}_result.json").read_text()) for worker_id in range(args.workers)]
    selected = max(results, key=lambda result: archive_key(result["best"]))
    grid = json.loads((run_directory / f"worker_{selected['worker']}_best.json").read_text())
    artifact = copy.deepcopy(template)
    artifact["circuits"] = [grid if circuit["family"] == "grid20" else circuit for circuit in artifact["circuits"]]
    validate_submission(artifact, spec)
    artifact_path = ROOT / "champions/private_achievability.json"
    report_path = ROOT / "champions/private_achievability_report.json"
    save(artifact_path, artifact)
    evaluation_started = time.perf_counter()
    completed = subprocess.run([sys.executable, "-B", str(ROOT / "evaluator/evaluate.py"), "--submission",
                                str(artifact_path), "--output", str(report_path)],
                               check=True, capture_output=True, text=True)
    official = json.loads(completed.stdout)
    unchanged = all(hashlib.sha256(path.read_bytes()).hexdigest() == frozen_hashes[str(path.relative_to(ROOT))] for path in frozen_paths)
    if not unchanged:
        raise RuntimeError("a frozen file changed externally during this search")
    summary = {"runtime_seconds": time.monotonic() - started, "official_evaluation_seconds": time.perf_counter() - evaluation_started,
               "core_score": official["core_score"], "valid": official["valid"], "passed": official["passed"],
               "selected_worker": selected["worker"], "workers": results, "frozen_files_unchanged": unchanged,
               "artifact": str(artifact_path.relative_to(ROOT)), "report": str(report_path.relative_to(ROOT)),
               "config": str((run_directory / "config.json").relative_to(ROOT))}
    save(run_directory / "summary.json", summary)
    save(WORK / "latest_summary.json", summary)
    print("FINAL", json.dumps({key: value for key, value in summary.items() if key != "workers"}), flush=True)


if __name__ == "__main__":
    main()
