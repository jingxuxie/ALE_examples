"""Public row-update simulator and artifact-only development scorer."""

import argparse
import json
import math
import os
from pathlib import Path
import stat
import time

import numpy as np


MAX_BYTES = 2 * 1024 * 1024
MAX_GATES = 4096
MAX_LAYERS = 4096


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("nonfinite JSON constant: " + value)


def read_solution(directory):
    path = Path(directory) / "solution.json"
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        information = os.fstat(stream.fileno())
        if not stat.S_ISREG(information.st_mode) or information.st_size > MAX_BYTES:
            raise ValueError("solution.json must be a regular file of at most 2 MiB")
        payload = stream.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError("solution.json exceeds 2 MiB")
    return json.loads(payload.decode("utf-8"), object_pairs_hook=unique_object,
                      parse_constant=reject_constant)


def exact_keys(value, expected, context):
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError(context + " has incorrect fields")


def validate_solution(solution, instances):
    exact_keys(solution, ("version", "circuits"), "solution")
    if type(solution["version"]) is not int or solution["version"] != 1:
        raise ValueError("version must be integer 1")
    circuits = solution["circuits"]
    if type(circuits) is not list or len(circuits) != len(instances):
        raise ValueError("one circuit per instance is required")
    known = {instance["id"]: instance for instance in instances}
    indexed = {}
    for circuit in circuits:
        exact_keys(circuit, ("id", "layers"), "circuit")
        identifier = circuit["id"]
        if type(identifier) is not str or identifier not in known or identifier in indexed:
            raise ValueError("unknown or duplicate circuit id")
        instance = known[identifier]
        layers = circuit["layers"]
        if type(layers) is not list or len(layers) > MAX_LAYERS:
            raise ValueError("layers must be a list of at most 4096 layers")
        edges = {frozenset(edge) for edge in instance["edges"]}
        count = 0
        for layer in layers:
            if type(layer) is not list or not layer:
                raise ValueError("layers must be nonempty lists")
            count += len(layer)
            if count > MAX_GATES:
                raise ValueError("more than 4096 gates in a circuit")
            used = set()
            for gate in layer:
                exact_keys(gate, ("u", "v", "theta", "phi"), "gate")
                first, second = gate["u"], gate["v"]
                if any(type(mode) is not int or not 0 <= mode < instance["n_modes"]
                       for mode in (first, second)):
                    raise ValueError("mode indices must be in-range integers")
                if first == second or frozenset((first, second)) not in edges:
                    raise ValueError("gate is not a hardware edge")
                if first in used or second in used:
                    raise ValueError("gates in a layer must have disjoint modes")
                used.update((first, second))
                for name in ("theta", "phi"):
                    value = gate[name]
                    if type(value) not in (int, float) or not -math.pi <= value <= math.pi:
                        raise ValueError("angles must be finite numbers in [-pi,pi]")
        indexed[identifier] = circuit
    return indexed


def projector(instance):
    encoded = instance["target_projector"]
    return np.asarray(encoded["real"], dtype=float) + 1j * np.asarray(encoded["imag"], dtype=float)


def apply_gate(orbitals, gate):
    first, second = gate["u"], gate["v"]
    cosine, sine = math.cos(gate["theta"]), math.sin(gate["theta"])
    phase = complex(math.cos(gate["phi"]), math.sin(gate["phi"]))
    first_row, second_row = orbitals[first].copy(), orbitals[second].copy()
    orbitals[first] = cosine * first_row - phase.conjugate() * sine * second_row
    orbitals[second] = phase * sine * first_row + cosine * second_row


def simulate(instance, circuit):
    orbitals = np.eye(instance["n_modes"], dtype=complex)[:, instance["initial_occupied"]]
    for layer in circuit["layers"]:
        for gate in layer:
            apply_gate(orbitals, gate)
    return orbitals


def circuit_metrics(instance, circuit):
    orbitals = simulate(instance, circuit)
    target = projector(instance)
    error = float(np.linalg.norm(orbitals @ orbitals.conj().T - target, "fro"))
    _, basis = np.linalg.eigh((target + target.conj().T) / 2)
    basis = basis[:, -instance["n_particles"]:]
    singular_values = np.clip(np.linalg.svd(basis.conj().T @ orbitals, compute_uv=False), 0, 1)
    fidelity = float(np.prod(singular_values ** 2))
    infidelity = max(0.0, 1.0 - fidelity)
    gates = sum(map(len, circuit["layers"]))
    depth = len(circuit["layers"])
    accurate = (error <= instance["tolerances"]["projector_frobenius"] and
                infidelity <= instance["tolerances"]["slater_infidelity"])
    within = gates <= instance["budgets"]["max_gates"] and depth <= instance["budgets"]["max_depth"]
    resource = min(1.0, instance["budgets"]["max_gates"] / max(1, gates),
                   instance["budgets"]["max_depth"] / max(1, depth)) if accurate else 0.0
    return {"id": instance["id"], "family": instance["family"], "gates": gates,
            "depth": depth, "projector_error": error, "slater_fidelity": fidelity,
            "slater_infidelity": infidelity, "accurate": bool(accurate),
            "within_budget": bool(within), "certified": bool(accurate and within),
            "resource_score": resource}


def aggregate(metrics):
    families = {}
    for result in metrics:
        families.setdefault(result["family"], []).append(int(result["certified"]))
    family_scores = {name: sum(values) / len(values) for name, values in families.items()}
    count = sum(result["certified"] for result in metrics)
    return {"core_score": count / len(metrics), "worst_family_score": min(family_scores.values()),
            "resource_score": sum(result["resource_score"] for result in metrics) / len(metrics),
            "runtime_score": None, "valid": True, "passed": count == len(metrics),
            "reason": "all instances certified" if count == len(metrics) else
                      f"{count}/{len(metrics)} certified; inspect accuracy and budget flags",
            "family_scores": family_scores, "instances": metrics}


def evaluate(directory, input_path=None):
    started = time.perf_counter()
    source = Path(input_path) if input_path else Path(__file__).resolve().parents[1] / "input/instances.json"
    instances = json.loads(source.read_text())["instances"]
    try:
        indexed = validate_solution(read_solution(directory), instances)
        report = aggregate([circuit_metrics(instance, indexed[instance["id"]]) for instance in instances])
    except (ValueError, OSError, UnicodeError, TypeError, RecursionError, OverflowError) as error:
        report = {"core_score": 0.0, "worst_family_score": 0.0, "resource_score": 0.0,
                  "runtime_score": None, "valid": False, "passed": False,
                  "reason": str(error)[:500], "instances": []}
    report["evaluation_seconds"] = time.perf_counter() - started
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("submission_dir")
    parser.add_argument("--report", type=Path)
    arguments = parser.parse_args()
    report = evaluate(arguments.submission_dir)
    encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.report:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(encoded)
    print(encoded, end="")
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
