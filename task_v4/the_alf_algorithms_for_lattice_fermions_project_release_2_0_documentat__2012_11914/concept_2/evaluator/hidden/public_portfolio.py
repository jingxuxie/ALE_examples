import argparse
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import resource
import time

for variable in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "attempts/privileged_public"


class Deadline(Exception):
    pass


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def strang(order):
    result = []
    for repeat in range(4):
        for index, label in enumerate(list(order) + list(order[-2::-1])):
            weight = 0.25 if index == 4 else 0.125
            if result and result[-1][0] == label:
                result[-1][1] += weight
            else:
                result.append([label, weight])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=240.0)
    arguments = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU, (330, 330))
    resource.setrlimit(resource.RLIMIT_AS, (1073741824, 1073741824))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    started = time.monotonic()
    deadline = started + min(arguments.seconds, 300.0)
    OUT.mkdir(parents=True, exist_ok=True)
    rules_path = ROOT / "participant/input/spec.json"
    training_path = ROOT / "participant/input/training_instances.json"
    rules = json.loads(rules_path.read_text())
    instances = json.loads(training_path.read_text())["instances"]
    labels = rules["components"]
    family_names = [family["name"] for family in rules["sampling"]["families"]]
    batches, steps, families = [], [], []
    for instance in instances:
        dimension = math.prod(instance["shape"])
        components = np.zeros((5, 24, 24), dtype=complex)
        components[4, :dimension, :dimension] = np.diag(instance["site_potential"])
        for label, source, target, amplitude, phase in instance["bonds"]:
            component = labels.index(label)
            value = -amplitude * np.exp(1j * phase)
            components[component, source, target] += value
            components[component, target, source] += value.conjugate()
        for step in rules["sampling"]["dtau"]:
            batches.append(components)
            steps.append(step)
            families.append(family_names.index(instance["family"]))
    batch = np.array(batches)
    steps = np.array(steps)
    families = np.array(families)
    identity = np.broadcast_to(np.eye(24, dtype=complex), (len(batch), 24, 24))
    eigenvalues, eigenvectors = np.linalg.eigh(batch)
    adjoints = eigenvectors.conj().swapaxes(-1, -2)
    total_values, total_vectors = np.linalg.eigh(batch.sum(axis=1))
    total_adjoints = total_vectors.conj().swapaxes(-1, -2)
    exact = []
    exact_green = []
    for repeats in rules["sampling"]["repetitions"]:
        exponentials = np.exp(-repeats * steps[:, None] * total_values)
        exact.append((total_vectors * exponentials[:, None, :]) @ total_adjoints)
        exact_green.append((total_vectors * (1.0 / (1.0 + exponentials))[:, None, :]) @ total_adjoints)

    def propagate(schedule):
        product = identity.copy()
        cache = {}
        for label, weight in schedule:
            key = (label, float(weight))
            if key not in cache:
                component = labels.index(label)
                exponentials = np.exp(-weight * steps[:, None] * eigenvalues[:, component])
                cache[key] = (eigenvectors[:, component] * exponentials[:, None, :]) @ adjoints[:, component]
            product = product @ cache[key]
        return product

    def errors(schedule):
        single = propagate(schedule)
        result = []
        for index, repeats in enumerate(rules["sampling"]["repetitions"]):
            repeated = np.linalg.matrix_power(single, repeats)
            green = np.linalg.inv(identity + repeated)
            result.append(np.stack((np.linalg.norm(repeated - exact[index], axis=(-2, -1)), np.linalg.norm(green - exact_green[index], axis=(-2, -1))), axis=-1))
        return np.stack(result, axis=1)

    reference = strang(labels)
    denominators = errors(reference)
    assert denominators.min() > 1e-10
    multiplicity = np.array([2.0] * 16 + [1.0])
    floor = rules["constraints"]["minimum_coefficient"]
    targets = rules["scoring"]["targets"]
    generator = np.random.default_rng(285206)
    best = {"loss": float("inf")}
    history = []
    evaluations = 0
    last_progress = started

    def groups(word):
        return [np.array([index for index, label in enumerate(word) if label == component]) for component in labels]

    def encode(word, weights):
        parameters = []
        for positions in groups(word):
            logs = np.log(np.maximum(np.asarray(weights)[positions] - floor, 1e-10))
            parameters.extend(logs[:-1] - logs[-1])
        return np.array(parameters)

    def decode(word, parameters):
        weights = np.empty(17)
        offset = 0
        for positions in groups(word):
            count = len(positions) - 1
            values = np.append(parameters[offset:offset + count], 0.0)
            values = np.exp(values - values.max())
            weights[positions] = floor + (1 - floor * multiplicity[positions].sum()) * values / np.dot(values, multiplicity[positions])
            offset += count
        half = [[label, float(weight)] for label, weight in zip(word, weights)]
        return half + half[-2::-1]

    def objective(word, parameters, origin):
        nonlocal best, evaluations, last_progress
        if time.monotonic() >= deadline:
            raise Deadline()
        schedule = decode(word, parameters)
        ratios = errors(schedule) / denominators
        family_rms = np.array([np.sqrt(np.mean(ratios[families == index] ** 2)) for index in range(4)])
        core = float(np.exp(-np.mean(np.log(family_rms))))
        worst = float(1.0 / family_rms.max())
        maximum = float(ratios.max())
        gates = np.concatenate(([targets["core_score_min"] / core], targets["worst_family_score_min"] * family_rms, [maximum / targets["max_point_ratio_max"]]))
        loss = float(logsumexp(24 * np.log(gates)) / 24)
        evaluations += 1
        if loss < best["loss"]:
            best = {"loss": loss, "core_score": core, "worst_family_score": worst, "max_point_ratio": maximum, "family_scores": dict(zip(family_names, (1 / family_rms).tolist())), "origin": origin, "evaluation": evaluations, "training_passes": bool(np.max(gates) <= 1.0), "half_word": list(word), "parameters": parameters.tolist()}
            history.append({key: value for key, value in best.items() if key not in ("parameters", "half_word")})
            payload = {"schema_version": 1, "stages": [{"component": label, "coefficient": weight} for label, weight in schedule]}
            write_json(OUT / "submission.json", payload)
            write_json(OUT / "best_training.json", best)
        if time.monotonic() - last_progress > 20:
            print(json.dumps({"elapsed": time.monotonic() - started, "evaluations": evaluations, "best_core": best["core_score"], "best_worst": best["worst_family_score"], "best_max_ratio": best["max_point_ratio"]}), flush=True)
            last_progress = time.monotonic()
        return loss

    completed_orders = 0
    optimized_words = 0
    stop = "portfolio_completed"
    try:
        candidates = []
        for order in itertools.permutations(labels):
            schedule = strang(order)
            word = [label for label, weight in schedule[:17]]
            parameters = encode(word, [weight for label, weight in schedule[:17]])
            loss = objective(word, parameters, "equal_strang_order_scan")
            candidates.append((loss, word, parameters))
            completed_orders += 1
        candidates.sort(key=lambda entry: entry[0])
        for candidate_index, (loss, word, parameters) in enumerate(candidates[:4]):
            minimize(lambda values: objective(word, values, "optimized_order_" + str(candidate_index)), parameters, method="L-BFGS-B", bounds=[(-9, 9)] * len(parameters), options={"maxiter": 85, "maxfun": 1400, "eps": 1e-5, "ftol": 1e-10})
            optimized_words += 1
        for mutation in range(16):
            word = list(best["half_word"])
            previous = decode(word, np.asarray(best["parameters"]))
            for retry in range(50):
                changed = list(word)
                if generator.random() < 0.5:
                    first, second = generator.choice(17, size=2, replace=False)
                    changed[first], changed[second] = changed[second], changed[first]
                else:
                    changed[int(generator.integers(17))] = str(generator.choice(labels))
                if set(changed) == set(labels) and all(left != right for left, right in zip(changed, changed[1:])) and changed != word:
                    word = changed
                    break
            else:
                continue
            parameters = encode(word, [weight for label, weight in previous[:17]])
            minimize(lambda values: objective(word, values, "word_mutation_" + str(mutation)), parameters, method="L-BFGS-B", bounds=[(-9, 9)] * len(parameters), options={"maxiter": 25, "maxfun": 450, "eps": 1e-5, "ftol": 1e-9})
            optimized_words += 1
    except Deadline:
        stop = "wall_deadline_reached"
    usage = resource.getrusage(resource.RUSAGE_SELF)
    summary = {"purpose": "privileged achievability probe, not fresh-agent hardness evidence", "search_data": "public training only", "training_sha256": hashlib.sha256(training_path.read_bytes()).hexdigest(), "public_contract_sha256": hashlib.sha256(rules_path.read_bytes()).hexdigest(), "seed": 285206, "threads": 1, "wall_budget_seconds": min(arguments.seconds, 300.0), "cpu_cap_seconds": 330, "elapsed_wall_seconds": time.monotonic() - started, "cpu_seconds": usage.ru_utime + usage.ru_stime, "stop": stop, "evaluations": evaluations, "scanned_orders": completed_orders, "optimized_words": optimized_words, "best": best, "history": history, "participant_modified": False, "thresholds_modified": False, "hidden_instances_read_during_search": False}
    write_json(OUT / "search_summary.json", summary)
    print(json.dumps({key: value for key, value in summary.items() if key != "history"}, indent=2), flush=True)


if __name__ == "__main__":
    main()
