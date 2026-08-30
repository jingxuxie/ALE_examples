import hashlib
import itertools
import json
import math
import os
import stat
from functools import lru_cache
from pathlib import Path

import numpy as np


LOCAL_WORDS = ("I", "H", "S", "HS", "SH", "HSH")
MAX_ARTIFACT_BYTES = 2_000_000


class InvalidSubmission(ValueError):
    pass


def reject_constant(value):
    raise InvalidSubmission("nonfinite JSON number: " + value)


def finite_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise InvalidSubmission("nonfinite JSON number")
    return result


def bounded_integer(value):
    if len(value) > 32:
        raise InvalidSubmission("JSON integer is too long")
    return int(value)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidSubmission("duplicate JSON key: " + key)
        result[key] = value
    return result


def load_json(path, limit=MAX_ARTIFACT_BYTES):
    path = Path(path)
    initial = path.lstat()
    if not stat.S_ISREG(initial.st_mode) or initial.st_nlink != 1:
        raise InvalidSubmission("artifact must be a regular, single-link file; symlinks and hardlinks are forbidden")
    if initial.st_size > limit:
        raise InvalidSubmission("artifact exceeds byte limit")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                or (initial.st_dev, initial.st_ino) != (opened.st_dev, opened.st_ino)):
            raise InvalidSubmission("artifact file changed or is not a regular single-link file")
        if opened.st_size > limit:
            raise InvalidSubmission("artifact exceeds byte limit")
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise InvalidSubmission("artifact exceeds byte limit")
    try:
        result = json.loads(data.decode("utf-8"), object_pairs_hook=unique_object,
                            parse_constant=reject_constant, parse_float=finite_float,
                            parse_int=bounded_integer)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise InvalidSubmission("invalid JSON: " + str(error)) from error
    return result, hashlib.sha256(data).hexdigest()


def exact_keys(value, keys, location):
    if type(value) is not dict or set(value) != set(keys):
        raise InvalidSubmission(location + ": expected keys " + ", ".join(keys))


def validate_submission(artifact, spec):
    exact_keys(artifact, ("schema_version", "circuits"), "artifact")
    if type(artifact["schema_version"]) is not int or artifact["schema_version"] != 1:
        raise InvalidSubmission("schema_version must be integer 1")
    circuits = artifact["circuits"]
    families = {family["id"]: family for family in spec["families"]}
    if type(circuits) is not list or len(circuits) != len(families):
        raise InvalidSubmission("exactly one circuit per hardware family is required")
    indexed = {}
    for circuit in circuits:
        exact_keys(circuit, ("family", "layers"), "circuit")
        family_id = circuit["family"]
        if type(family_id) is not str or family_id not in families:
            raise InvalidSubmission("unknown hardware family")
        if family_id in indexed:
            raise InvalidSubmission("duplicate hardware family")
        family = families[family_id]
        layers = circuit["layers"]
        if type(layers) is not list or len(layers) > family["max_rounds"]:
            raise InvalidSubmission(family_id + ": round limit exceeded or invalid layers")
        edges = {tuple(sorted(edge)) for edge in family["edges"]}
        cnot_count = 0
        for layer_index, layer in enumerate(layers):
            location = f"{family_id} round {layer_index}"
            exact_keys(layer, ("local", "cx"), location)
            local = layer["local"]
            if type(local) is not list or len(local) != family["n"]:
                raise InvalidSubmission(location + ": local must have n entries")
            if any(type(word) is not str or word not in LOCAL_WORDS for word in local):
                raise InvalidSubmission(location + ": unsupported local Clifford")
            cnots = layer["cx"]
            if type(cnots) is not list or len(cnots) > family["n"] // 2:
                raise InvalidSubmission(location + ": invalid CNOT matching")
            occupied = set()
            for gate in cnots:
                if type(gate) is not list or len(gate) != 2:
                    raise InvalidSubmission(location + ": CNOT must be [control, target]")
                if any(type(qubit) is not int or not 0 <= qubit < family["n"] for qubit in gate):
                    raise InvalidSubmission(location + ": CNOT qubit out of range or not integer")
                control, target = gate
                if control == target or tuple(sorted(gate)) not in edges:
                    raise InvalidSubmission(location + ": CNOT is not a native edge")
                if control in occupied or target in occupied:
                    raise InvalidSubmission(location + ": CNOTs must form a matching")
                occupied.update(gate)
            cnot_count += len(cnots)
        if cnot_count > family["max_cx"]:
            raise InvalidSubmission(family_id + ": two-qubit budget exceeded")
        indexed[family_id] = circuit
    return indexed


@lru_cache(maxsize=None)
def pauli_indices(n):
    left = []
    right = []
    labels = [(qubit, axis) for qubit in range(n) for axis in ("X", "Y", "Z")]
    for first, second in itertools.combinations(range(n), 2):
        for first_axis in range(3):
            for second_axis in range(3):
                left.append(3 * first + first_axis)
                right.append(3 * second + second_axis)
    return np.array(left), np.array(right), labels


def output_rows(n, layers, drop=None):
    rows = [1 << index for index in range(2 * n)]
    for layer_index, layer in enumerate(layers):
        for qubit, word in enumerate(layer["local"]):
            for gate in word:
                if gate == "H":
                    rows[qubit], rows[n + qubit] = rows[n + qubit], rows[qubit]
                elif gate == "S":
                    rows[n + qubit] ^= rows[qubit]
        for gate_index, (control, target) in enumerate(layer["cx"]):
            if drop == (layer_index, gate_index):
                continue
            rows[target] ^= rows[control]
            rows[n + control] ^= rows[n + target]
    return rows


def generator_images(n, rows):
    packed = np.array(rows, dtype=np.uint64)
    shifts = np.arange(2 * n, dtype=np.uint64)
    matrix = (packed[:, None] >> shifts[None, :]) & np.uint64(1)
    forward = np.sum(matrix << shifts[:, None], axis=0, dtype=np.uint64)
    swapped = np.concatenate((packed[n:], packed[:n]))
    inverse = ((swapped & np.uint64((1 << n) - 1)) << np.uint64(n)) | (swapped >> np.uint64(n))
    return forward, inverse


@lru_cache(maxsize=1)
def byte_popcounts():
    return np.array([value.bit_count() for value in range(256)], dtype=np.uint8)


def weights_from_images(n, images):
    singles = np.stack((images[:n], images[:n] ^ images[n:], images[n:]), axis=1).reshape(-1)
    left, right, _ = pauli_indices(n)
    doubles = singles[left] ^ singles[right]
    packed = np.concatenate((singles, doubles))
    support = ((packed | (packed >> np.uint64(n))) & np.uint64((1 << n) - 1)).astype(np.uint32)
    weights = byte_popcounts()[support.view(np.uint8).reshape(-1, 4)].sum(axis=1)
    return weights[:3 * n], weights[3 * n:]


def circuit_weights(n, layers, drop=None):
    return tuple(weights_from_images(n, images) for images in generator_images(n, output_rows(n, layers, drop)))


def input_witness(n, stratum, index):
    left, right, labels = pauli_indices(n)
    positions = [index] if stratum == "single" else [int(left[index]), int(right[index])]
    return [{"qubit": labels[position][0], "pauli": labels[position][1]} for position in positions]


def summarize(n, direction_weights):
    result = {}
    for direction, strata in zip(("forward", "inverse"), direction_weights):
        result[direction] = {}
        for stratum, weights in zip(("single", "double"), strata):
            worst = int(np.argmin(weights))
            result[direction][stratum] = {
                "count": len(weights), "minimum": int(weights[worst]),
                "weight_sum": int(weights.sum()), "mean": float(weights.mean()),
                "histogram": np.bincount(weights.astype(int), minlength=n + 1).tolist(),
                "worst_input": input_witness(n, stratum, worst),
            }
    return result


def score_metrics(metrics, targets):
    ratios = []
    failed = []
    for direction in ("forward", "inverse"):
        for stratum in ("single", "double"):
            observed = metrics[direction][stratum]
            minimum = targets["min_" + stratum]
            mean_milli = targets["mean_" + stratum + "_milli"]
            ratios.extend((observed["minimum"] / minimum,
                           1000 * observed["weight_sum"] / (mean_milli * observed["count"])))
            if observed["minimum"] < minimum:
                failed.append(f"{direction}.{stratum}.minimum")
            if 1000 * observed["weight_sum"] < mean_milli * observed["count"]:
                failed.append(f"{direction}.{stratum}.mean")
    return min(1.0, min(ratios)), failed


def deletion_diagnostics(n, layers):
    worst = {direction: {"single": n, "double": n} for direction in ("forward", "inverse")}
    worst_case = None
    global_minimum = n + 1
    scenarios = 0
    for layer_index, layer in enumerate(layers):
        for gate_index in range(len(layer["cx"])):
            scenarios += 1
            weights = circuit_weights(n, layers, (layer_index, gate_index))
            for direction, strata in zip(("forward", "inverse"), weights):
                for stratum, values in zip(("single", "double"), strata):
                    minimum = int(values.min())
                    worst[direction][stratum] = min(worst[direction][stratum], minimum)
                    if minimum < global_minimum:
                        global_minimum = minimum
                        worst_case = {"round": layer_index, "cx_index": gate_index,
                                      "direction": direction, "stratum": stratum,
                                      "input": input_witness(n, stratum, int(values.argmin()))}
    return {"scenarios": scenarios, "minimum": global_minimum if scenarios else None,
            "stratum_minima": worst if scenarios else None, "worst_case": worst_case,
            "affects_pass": False}
