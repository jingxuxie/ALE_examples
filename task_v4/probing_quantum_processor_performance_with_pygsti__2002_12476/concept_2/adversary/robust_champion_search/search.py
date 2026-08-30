import argparse
import copy
import functools
import hashlib
import importlib.util
import itertools
import json
import multiprocessing
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.optimize import minimize


sys.dont_write_bytecode = True
OUTPUT = Path(__file__).resolve().parent
ROOT = OUTPUT.parents[1]
ARCHIVE = ROOT / "generations/generation_0"
SELECTED = ROOT / "adversary/generation_1/selected_specification.json"


def module(name, path):
    loader = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(result)
    return result


PUBLIC = module("archived_screen", ARCHIVE / "participant/workspace/screen.py")
PRIVATE = module("archived_evaluator", ARCHIVE / "evaluator/evaluate.py")
FAMILIES = PUBLIC.FAMILIES
CALIBRATION_WORDS = sum(FAMILIES.values(), [])
SCALE = np.tile([1., .01, .01, .01, .01], 3)


def save(name, value):
    temporary = OUTPUT / (name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(OUTPUT / name)


def selected_specification(path):
    specification = json.loads(Path(path).read_text())
    if "specification" in specification:
        specification = specification["specification"]
    if "scenarios" not in specification:
        raise ValueError("selected specification has no scenario list")
    for key in ["heldout_min_abs_error", "heldout_max_final_leakage", "calibration_max_abs_error",
                "calibration_max_family_rms_error", "coupling_norm_max", "phase_absolute_max"]:
        if key in specification and specification[key] != PUBLIC.SPEC[key]:
            raise ValueError("nominal bound or target differs from the archived task: " + key)
    return specification


def offsets(scenario):
    if "phase_offsets" in scenario:
        value = scenario["phase_offsets"]
    elif "phase_shifts" in scenario:
        value = scenario["phase_shifts"]
    elif "phase_shift" in scenario:
        value = scenario["phase_shift"]
    else:
        raise ValueError("scenario does not specify its phase perturbation")
    if isinstance(value, dict):
        value = [value[symbol] for symbol in "IXY"]
    result = np.asarray(value, dtype=float)
    if result.ndim == 0:
        result = np.full(3, float(result))
    if result.shape != (3,) or not np.isfinite(result).all():
        raise ValueError("phase perturbation must have three finite components")
    return result


class Simulator:
    def __init__(self, specification):
        self.specification = specification
        self.scenarios = specification["scenarios"]
        self.scales = sorted(set(float(scenario["coupling_scale"]) for scenario in self.scenarios))
        self.scale_indices = np.array([self.scales.index(float(scenario["coupling_scale"])) for scenario in self.scenarios])
        self.phase_offsets = np.array([offsets(scenario) for scenario in self.scenarios])
        self.batch_calls = 0
        self.circuit_scenario_evaluations = 0

    def simulate(self, parameters, encoded):
        self.batch_calls += 1
        self.circuit_scenario_evaluations += len(encoded) * len(self.scenarios)
        unitaries_by_scale = []
        transfers = []
        for strength in self.scales:
            transformed = np.asarray(parameters).reshape(3, 5).copy()
            transformed[:, 1:] *= strength
            unitaries, transfer = PUBLIC.operators(transformed)
            unitaries_by_scale.append(unitaries)
            transfers.append(transfer)
        unitaries = np.array(unitaries_by_scale)[self.scale_indices]
        unitaries[:, :3, :, 2] *= np.exp(-1j * self.phase_offsets)[:, :, None]
        transfers = np.array(transfers)
        states = np.zeros((len(self.scenarios), len(encoded), 3), dtype=complex)
        states[:, :, 0] = 1
        bloch = np.tile([1., 0., 0., 1.], (len(self.scales), len(encoded), 1))
        for column in encoded.T:
            states = (unitaries[:, column] @ states[..., None])[..., 0]
            bloch = (transfers[:, column] @ bloch[..., None])[..., 0]
        truth = .005 + .99 * abs(states[:, :, 0]) ** 2
        prediction = .005 + .99 * (bloch[:, :, 0] + bloch[:, :, 3]) / 2
        prediction = prediction[self.scale_indices]
        leakage = abs(states[:, :, 2]) ** 2
        return truth - prediction, leakage


def independent(witness, specification):
    PRIVATE.check_input(witness)
    words = CALIBRATION_WORDS + [witness["circuit"]]
    records = []
    violations = []
    for scenario in specification["scenarios"]:
        parameters = np.asarray(witness["gate_parameters"]).copy()
        parameters[:, 0] += offsets(scenario)
        parameters[:, 1:] *= scenario["coupling_scale"]
        truth, prediction, leakage = PRIVATE.simulate(parameters, words)
        errors = abs(truth - prediction)
        families = {}
        offset = 0
        for name, family in FAMILIES.items():
            selected = errors[offset:offset + len(family)]
            offset += len(family)
            maximum = float(np.max(selected))
            rms = float(np.sqrt(np.mean(selected ** 2)))
            families[name] = {"max_abs_error": maximum, "rms_error": rms}
            if maximum > .005 + 1e-10 or rms > .002 + 1e-10:
                violations.append(scenario["name"] + ":calibration:" + name)
        if leakage[-1] > .01 + 1e-10:
            violations.append(scenario["name"] + ":final_leakage")
        if errors[-1] < .065 - 1e-10:
            violations.append(scenario["name"] + ":prediction_gap")
        records.append({"name": scenario["name"], "heldout_abs_error": float(errors[-1]),
                        "final_leakage": float(leakage[-1]), "calibration": families})
    nominal_truth, nominal_prediction, nominal_leakage = PRIVATE.simulate(witness["gate_parameters"], [witness["circuit"]])
    result = {"valid": True, "passed": not violations, "core_score": float(abs(nominal_truth[0] - nominal_prediction[0])),
              "worst_family_score": min(record["heldout_abs_error"] for record in records),
              "calibration_accepted": not any("calibration" in violation for violation in violations),
              "scenarios": records, "violations": violations}
    result["margins"] = margins(result)
    return result


def margins(result):
    scenarios = result["scenarios"]
    return {"calibration_max": .005 - max(family["max_abs_error"] for scenario in scenarios for family in scenario["calibration"].values()),
            "calibration_rms": .002 - max(family["rms_error"] for scenario in scenarios for family in scenario["calibration"].values()),
            "final_leakage": .01 - max(scenario["final_leakage"] for scenario in scenarios),
            "prediction_gap": result["worst_family_score"] - .065}


def optimize(parameters, word, simulator, deadline, maxiter=140):
    encoded = PUBLIC.encode(CALIBRATION_WORDS + [word])

    @functools.lru_cache(maxsize=64)
    def data(candidate):
        if time.monotonic() > deadline:
            raise TimeoutError("search budget exhausted")
        return simulator.simulate(np.array(candidate) * SCALE, encoded)

    def objective(candidate):
        residual, leakage = data(tuple(candidate))
        return -10 * min(abs(residual[:, -1]))

    def constraints(candidate):
        residual, leakage = data(tuple(candidate))
        values = [(.004999 - residual[:, :-1]).ravel() / .005,
                  (.004999 + residual[:, :-1]).ravel() / .005, (.00999 - leakage[:, -1]) / .01]
        offset = 0
        for family in FAMILIES.values():
            rms = np.sqrt(np.mean(residual[:, offset:offset + len(family)] ** 2, axis=1))
            values.append((.0019995 - rms) / .002)
            offset += len(family)
        values.append((.039999 - np.linalg.norm((candidate * SCALE).reshape(3, 5)[:, 1:], axis=1)) / .04)
        return np.concatenate(values)

    result = minimize(objective, np.asarray(parameters).ravel() / SCALE, method="SLSQP",
                      bounds=[(-np.pi, np.pi), (-4., 4.), (-4., 4.), (-4., 4.), (-4., 4.)] * 3,
                      constraints={"type": "ineq", "fun": constraints},
                      options={"ftol": 1e-8, "maxiter": maxiter, "eps": 3e-6})
    candidate = result.x * SCALE
    witness = {"version": 1, "gate_parameters": candidate.reshape(3, 5).tolist(), "circuit": word}
    return witness, {"success": bool(result.success), "nfev": int(result.nfev), "iterations": int(result.nit)}


def circuit_search(parameters, word, simulator, generator, deadline, rounds=100):
    population = 384
    encoded = generator.integers(0, 3, size=(population, 64))
    encoded[:population // 2] = PUBLIC.encode([word])[0]
    best_word = word
    best_score = -np.inf
    for generation in range(rounds):
        if time.monotonic() > deadline:
            raise TimeoutError("search budget exhausted")
        residual, leakage = simulator.simulate(parameters, encoded)
        scores = np.min(abs(residual), axis=0) - 5 * np.maximum(np.max(leakage, axis=0) - .0099, 0)
        for gate in range(3):
            scores -= np.maximum(4 - np.sum(encoded == gate, axis=1), 0)
        order = np.argsort(-scores)
        if scores[order[0]] > best_score:
            best_score = float(scores[order[0]])
            best_word = "".join("IXY"[label] for label in encoded[order[0]])
        sorted_encoded = encoded[order]
        unique, indices = np.unique(sorted_encoded, axis=0, return_index=True)
        elite = sorted_encoded[np.sort(indices)[:64]]
        encoded = elite[generator.integers(0, len(elite), population)].copy()
        for index in range(population):
            first, second = sorted(generator.integers(0, 64, 2))
            move = generator.integers(0, 4)
            if move == 0:
                encoded[index, first] = generator.integers(0, 3)
            elif move == 1:
                encoded[index, first], encoded[index, second] = encoded[index, second], encoded[index, first]
            elif move == 2:
                encoded[index, first:second + 1] = np.roll(encoded[index, first:second + 1], 1)
            else:
                encoded[index, first:second + 1] = encoded[index, first:second + 1][::-1]
        encoded[:len(elite)] = elite
    return best_word


def worker(worker, specification, deadline, stop):
    try:
        cores = sorted(os.sched_getaffinity(0))
        os.sched_setaffinity(0, {cores[-1 - worker % min(4, len(cores))]})
    except (AttributeError, OSError):
        pass
    simulator = Simulator(specification)
    generator = np.random.default_rng(664120 + 2311 * worker)
    champion = json.loads((ROOT / "champions/generation_1/witness.json").read_text())
    current = champion
    best = independent(champion, specification)
    best_witness = champion
    independent_calls = 1
    history = []
    cycle = 0
    started = time.monotonic()
    outcome = "budget_exhausted"
    try:
        while time.monotonic() < deadline and not stop.is_set():
            parameters = np.asarray(current["gate_parameters"]).copy()
            word = current["circuit"]
            if worker and cycle == 0:
                parameters[:, 1:] *= .8 + .07 * worker
                parameters[:, 0] += generator.normal(0, .002 * worker, 3)
            if cycle and worker:
                word = circuit_search(parameters, word, simulator, generator, deadline, rounds=100 + 30 * worker)
            witness, solver = optimize(parameters, word, simulator, deadline)
            measured = independent(witness, specification)
            independent_calls += 1
            record = {"cycle": cycle, "solver": solver, "core_score": measured["core_score"],
                      "worst_family_score": measured["worst_family_score"], "passed": measured["passed"],
                      "margins": measured["margins"], "seconds": time.monotonic() - started,
                      "batch_calls": simulator.batch_calls, "circuit_scenario_evaluations": simulator.circuit_scenario_evaluations,
                      "independent_evaluator_calls": independent_calls}
            history.append(record)
            save("worker_" + str(worker) + "_history.json", history)
            print(json.dumps({"worker": worker, **record}), flush=True)
            current = witness
            eligible = min(value for key, value in measured["margins"].items() if key != "prediction_gap") >= -1e-10
            previous_eligible = min(value for key, value in best["margins"].items() if key != "prediction_gap") >= -1e-10
            if eligible and (not previous_eligible or measured["worst_family_score"] > best["worst_family_score"]):
                best, best_witness = measured, witness
                save("worker_" + str(worker) + "_best_witness.json", witness)
                save("worker_" + str(worker) + "_best_evaluation.json", measured)
            if measured["passed"]:
                outcome = "passing_independent_reproduction"
                stop.set()
                break
            cycle += 1
    except TimeoutError:
        pass
    except Exception as error:
        outcome = type(error).__name__ + ": " + str(error)
    finally:
        save("worker_" + str(worker) + "_final.json", {"outcome": outcome, "seconds": time.monotonic() - started,
                                                       "batch_calls": simulator.batch_calls,
                                                       "circuit_scenario_evaluations": simulator.circuit_scenario_evaluations,
                                                       "independent_evaluator_calls": independent_calls,
                                                       "completed_optimizations": len(history)})


def main():
    global OUTPUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, default=SELECTED)
    parser.add_argument("--seconds", type=int, default=1020)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    OUTPUT = args.output_dir.resolve()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    specification = selected_specification(args.spec)
    for scenario in specification["scenarios"]:
        offsets(scenario)
    save("used_specification.json", specification)
    source_hash = hashlib.sha256(args.spec.read_bytes()).hexdigest()
    champion = json.loads((ROOT / "champions/generation_1/witness.json").read_text())
    simulator = Simulator(specification)
    residual, leakage = simulator.simulate(champion["gate_parameters"], PUBLIC.encode(CALIBRATION_WORDS + [champion["circuit"]]))
    reference = independent(champion, specification)
    difference = max(abs(abs(residual[index, -1]) - record["heldout_abs_error"]) for index, record in enumerate(reference["scenarios"]))
    for index, scenario in enumerate(specification["scenarios"]):
        transformed = np.asarray(champion["gate_parameters"]).copy()
        transformed[:, 0] += offsets(scenario)
        transformed[:, 1:] *= scenario["coupling_scale"]
        truth, prediction, reference_leakage = PRIVATE.simulate(transformed, CALIBRATION_WORDS + [champion["circuit"]])
        difference = max(difference, float(np.max(abs(residual[index] - (truth - prediction)))),
                         float(np.max(abs(leakage[index] - reference_leakage))))
    if difference > 3e-12:
        raise ArithmeticError("batched simulator cross-check failed")
    save("simulator_audit.json", {"passed": True, "maximum_disagreement": difference, "scenario_count": len(specification["scenarios"]),
                                  "selected_specification_sha256": source_hash})
    save("champion_evaluation.json", reference)
    print(json.dumps({"champion_worst": reference["worst_family_score"], "champion_margins": reference["margins"],
                      "simulator_disagreement": difference}), flush=True)
    if args.audit_only:
        return
    started = time.monotonic()
    deadline = started + args.seconds
    save("run_manifest.json", {"started_at_utc": datetime.now(timezone.utc).isoformat(), "budget_seconds": args.seconds,
                               "scenario_count": len(specification["scenarios"]), "source_specification": str(args.spec),
                               "selected_specification_sha256": source_hash, "workers": args.workers,
                               "fresh_outputs_inspected": False, "seed": "champions/generation_1/witness.json"})
    stop = multiprocessing.Event()
    processes = [multiprocessing.Process(target=worker, args=(index, specification, deadline, stop)) for index in range(args.workers)]
    for process in processes:
        process.start()
    while any(process.is_alive() for process in processes):
        if time.monotonic() > deadline + 15:
            for process in processes:
                if process.is_alive():
                    process.terminate()
            break
        time.sleep(1)
    for process in processes:
        process.join(timeout=3)
    if hashlib.sha256(args.spec.read_bytes()).hexdigest() != source_hash:
        save("specification_changed.json", {"reason": "Selected specification changed during search; revalidate before making an achievability claim."})
    print("search_complete", flush=True)


if __name__ == "__main__":
    main()
