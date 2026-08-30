import argparse
import importlib.util
import json
import multiprocessing
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.optimize import minimize


sys.dont_write_bytecode = True
OUTPUT = Path(__file__).resolve().parent
ROOT = OUTPUT.parents[1]


def load_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


SEARCH = load_module("seed_search", ROOT / "adversary/robust_search.py")
SCREEN = SEARCH.SCREEN
EVALUATOR = load_module("trusted_evaluator", ROOT / "evaluator/evaluate.py")
SCALE = SEARCH.SCALE


def save(name, data):
    temporary = OUTPUT / (name + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    temporary.replace(OUTPUT / name)


def margins(result):
    scenarios = result["scenarios"]
    return {"calibration_max_margin": .005 - max(family["max_abs_error"] for scenario in scenarios
                                                 for family in scenario["calibration"].values()),
            "calibration_rms_margin": .002 - max(family["rms_error"] for scenario in scenarios
                                                 for family in scenario["calibration"].values()),
            "final_leakage_margin": .01 - max(scenario["final_leakage"] for scenario in scenarios),
            "prediction_gap_margin": result["worst_family_score"] - .065}


def feasible(result):
    values = margins(result)
    return result["valid"] and min(values[key] for key in values if key != "prediction_gap_margin") >= -1e-10


def optimize_parameters(parameters, word, worker, deadline):
    encoded = SCREEN.encode(sum(SCREEN.FAMILIES.values(), []) + [word])
    last_candidate = None
    last_data = None

    def evaluate(candidate):
        nonlocal last_candidate, last_data
        if time.monotonic() >= deadline:
            raise TimeoutError("bounded search deadline")
        if last_candidate is None or not np.array_equal(candidate, last_candidate):
            last_candidate = candidate.copy()
            last_data = SEARCH.data(candidate * SCALE, encoded)
        return last_data

    def objective(candidate):
        results = evaluate(candidate)
        return -10 * min(abs(residual[-1]) for residual, leakage in results)

    def constraints(candidate):
        values = []
        for residual, leakage in evaluate(candidate):
            values.extend([(.004999 - residual[:-1]) / .005, (.004999 + residual[:-1]) / .005,
                           [(.009995 - leakage[-1]) / .01]])
            offset = 0
            for family in SCREEN.FAMILIES.values():
                rms = np.sqrt(np.mean(residual[offset:offset + len(family)] ** 2))
                values.append([(.0019996 - rms) / .002])
                offset += len(family)
        values.append((.039999 - np.linalg.norm((candidate * SCALE).reshape(3, 5)[:, 1:], axis=1)) / .04)
        return np.concatenate(values)

    result = minimize(objective, np.asarray(parameters).ravel() / SCALE, method="SLSQP",
                      bounds=[(-np.pi, np.pi), (-4., 4.), (-4., 4.), (-4., 4.), (-4., 4.)] * 3,
                      constraints={"type": "ineq", "fun": constraints},
                      options={"maxiter": 190 if worker % 2 else 130, "ftol": 5e-9, "eps": 2e-6})
    parameters = result.x * SCALE
    last = None
    for iteration in range(24):
        witness = {"version": 1, "gate_parameters": parameters.reshape(3, 5).tolist(), "circuit": word}
        try:
            measured = SCREEN.measure(witness)
        except ValueError:
            parameters.reshape(3, 5)[:, 1:] *= .98
            continue
        last = (parameters.copy(), measured, bool(result.success), int(result.nfev))
        if feasible(measured):
            return last
        parameters.reshape(3, 5)[:, 1:] *= .99
    if last is None:
        raise ValueError("no physical parameter-search result")
    return last


def mutate_word(word, generator, worker, cycle):
    symbols = np.array(list(word))
    if worker == 1:
        start = generator.integers(0, 56)
        count = int(generator.integers(2, 9))
        symbols[start:start + count] = symbols[start:start + count][::-1]
    elif worker == 2:
        first, second = generator.choice(64, 2, replace=False)
        symbols[first], symbols[second] = symbols[second], symbols[first]
    elif worker == 3:
        location = int(generator.integers(0, 64))
        count = int(generator.integers(1, 5))
        symbols = np.roll(symbols, count)
        symbols[location] = generator.choice(list("IXY"))
    return "".join(symbols)


def worker_main(worker, deadline, stop):
    try:
        cores = sorted(os.sched_getaffinity(0))
        os.sched_setaffinity(0, {cores[-1 - worker % min(len(cores), 4)]})
    except (AttributeError, OSError):
        pass
    generator = np.random.default_rng(182893 + 7919 * worker)
    counts = {"probability_batch_calls": 0, "circuit_scenario_evaluations": 0,
              "continuous_batch_calls": 0, "discrete_batch_calls": 0, "other_batch_calls": 0,
              "independent_evaluator_calls": 0, "completed_parameter_searches": 0}
    phase = "other"
    original = SCREEN.probabilities

    def counted(parameters, encoded):
        counts["probability_batch_calls"] += 1
        counts["circuit_scenario_evaluations"] += len(encoded)
        counts[phase + "_batch_calls"] += 1
        return original(parameters, encoded)

    SCREEN.probabilities = counted
    seed = json.loads((ROOT / "adversary/private_best_witness.json").read_text())
    best_witness = seed
    best = EVALUATOR.score_witness(seed)
    counts["independent_evaluator_calls"] += 1
    parameters = np.array(seed["gate_parameters"]).ravel()
    word = seed["circuit"]
    history = []
    save("worker_" + str(worker) + "_best_witness.json", best_witness)
    save("worker_" + str(worker) + "_best_evaluation.json", best)
    started = time.monotonic()
    cycle = 0
    outcome = "budget_exhausted"
    try:
        while time.monotonic() < deadline and not stop.is_set():
            if cycle and worker and cycle % 3 == 0:
                parameters = np.array(best_witness["gate_parameters"]).ravel()
                parameters.reshape(3, 5)[:, 0] += generator.normal(0, .035 + .015 * worker, 3)
                parameters.reshape(3, 5)[:, 0] = np.clip(parameters.reshape(3, 5)[:, 0], -np.pi, np.pi)
                parameters.reshape(3, 5)[:, 1:] += generator.normal(0, .0005 * worker, (3, 4))
                word = mutate_word(best_witness["circuit"], generator, worker, cycle)
            elif cycle:
                parameters = np.array(best_witness["gate_parameters"]).ravel()
                word = best_witness["circuit"]
            if cycle or worker:
                phase = "discrete"
                word = SEARCH.circuit_search(parameters, word, generator,
                                             rounds=180 + worker * 40, population=1024 if worker == 0 else 2048)
            phase = "continuous"
            parameters, measured, success, evaluations = optimize_parameters(parameters, word, worker, deadline)
            counts["completed_parameter_searches"] += 1
            phase = "other"
            witness = {"version": 1, "gate_parameters": parameters.reshape(3, 5).tolist(), "circuit": word}
            independent = EVALUATOR.score_witness(witness)
            counts["independent_evaluator_calls"] += 1
            record = {"cycle": cycle, "solver_success": success, "optimizer_function_evaluations": evaluations,
                      "core_score": independent["core_score"], "worst_family_score": independent["worst_family_score"],
                      "passed": independent["passed"], "feasible_except_gap": feasible(independent),
                      "margins": margins(independent), "seconds": time.monotonic() - started,
                      "counts": counts.copy()}
            history.append(record)
            save("worker_" + str(worker) + "_history.json", history)
            print(json.dumps({"worker": worker, **record}), flush=True)
            if feasible(independent) and independent["worst_family_score"] > best["worst_family_score"]:
                best = independent
                best_witness = witness
                save("worker_" + str(worker) + "_best_witness.json", witness)
                save("worker_" + str(worker) + "_best_evaluation.json", independent)
            if independent["passed"]:
                save("worker_" + str(worker) + "_passing_witness.json", witness)
                save("worker_" + str(worker) + "_passing_evaluation.json", independent)
                outcome = "independent_passing_witness"
                stop.set()
                break
            cycle += 1
    except TimeoutError:
        outcome = "budget_exhausted"
    except Exception as error:
        outcome = type(error).__name__ + ": " + str(error)
    finally:
        save("worker_" + str(worker) + "_final.json",
             {"outcome": outcome, "counts": counts, "seconds": time.monotonic() - started,
              "core_score": best["core_score"], "worst_family_score": best["worst_family_score"],
              "passed": best["passed"], "margins": margins(best)})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=1080)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    started = time.monotonic()
    deadline = started + args.seconds
    stop = multiprocessing.Event()
    processes = [multiprocessing.Process(target=worker_main, args=(worker, deadline, stop)) for worker in range(args.workers)]
    save("run_manifest.json", {"started_at_utc": datetime.now(timezone.utc).isoformat(), "budget_seconds": args.seconds,
                               "workers": args.workers, "starting_worst_score": .05072907638997459,
                               "starting_witness": "adversary/private_best_witness.json",
                               "frozen_target": .065, "fresh_attempts_inspected": False,
                               "new_artifacts_restricted_to": "adversary/extended_search/"})
    for process in processes:
        process.start()
    while any(process.is_alive() for process in processes):
        if time.monotonic() > deadline + 10:
            for process in processes:
                if process.is_alive():
                    process.terminate()
            break
        time.sleep(1)
    for process in processes:
        process.join(timeout=3)
    evaluations = []
    for worker in range(args.workers):
        path = OUTPUT / ("worker_" + str(worker) + "_best_witness.json")
        if path.exists():
            result = EVALUATOR.evaluate(path)
            evaluations.append((result["worst_family_score"] if feasible(result) else -1, worker, result))
    score, worker, result = max(evaluations)
    witness = json.loads((OUTPUT / ("worker_" + str(worker) + "_best_witness.json")).read_text())
    save("best_witness.json", witness)
    save("best_evaluation.json", result)
    final_counts = []
    for worker in range(args.workers):
        path = OUTPUT / ("worker_" + str(worker) + "_final.json")
        if path.exists():
            final_counts.append(json.loads(path.read_text())["counts"])
    counts = {name: sum(record[name] for record in final_counts) for name in final_counts[0]} if final_counts else {}
    save("summary.json", {"runtime_seconds": time.monotonic() - started, "core_score": result["core_score"],
                          "worst_family_score": result["worst_family_score"], "passed": result["passed"],
                          "margins": margins(result), "counts": counts,
                          "workers_with_complete_final_counts": len(final_counts), "solvability": "demonstrated" if result["passed"] else "unknown"})
    print(json.dumps({"FINAL": result["worst_family_score"], "passed": result["passed"], "counts": counts}), flush=True)


if __name__ == "__main__":
    main()
