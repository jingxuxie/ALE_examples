"""Independent, artifact-only verifier. Never imports or executes participant code."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import time

import numpy as np


HIDDEN = Path(__file__).resolve().parent / "hidden"
MAX_BYTES = 2097152


class ArtifactError(ValueError):
    pass


def object_without_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ArtifactError("duplicate JSON key")
        result[key] = value
    return result


def bad_constant(value):
    raise ArtifactError("nonfinite JSON constant")


def require(condition, message):
    if not condition:
        raise ArtifactError(message)


def fields(value, keys, context):
    require(type(value) is dict and set(value) == set(keys), context + ": incorrect fields")


def load_artifact(directory, instances):
    descriptor = os.open(Path(directory) / "solution.json", os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        information = os.fstat(stream.fileno())
        require(stat.S_ISREG(information.st_mode), "solution.json is not a regular file")
        require(information.st_size <= MAX_BYTES, "solution.json exceeds 2 MiB")
        payload = stream.read(MAX_BYTES + 1)
    require(len(payload) <= MAX_BYTES, "solution.json exceeds 2 MiB")
    artifact = json.loads(payload.decode("utf-8"), object_pairs_hook=object_without_duplicates,
                          parse_constant=bad_constant)
    fields(artifact, ("version", "circuits"), "solution")
    require(type(artifact["version"]) is int and artifact["version"] == 1, "version must be integer 1")
    circuits = artifact["circuits"]
    require(type(circuits) is list and len(circuits) == len(instances), "one circuit per instance required")
    lookup = {instance["id"]: instance for instance in instances}
    result = {}
    for circuit in circuits:
        fields(circuit, ("id", "layers"), "circuit")
        identifier = circuit["id"]
        require(type(identifier) is str and identifier in lookup and identifier not in result,
                "unknown or duplicate circuit id")
        instance = lookup[identifier]
        layers = circuit["layers"]
        require(type(layers) is list and len(layers) <= 4096, "invalid layers or layer limit exceeded")
        hardware = {tuple(sorted(edge)) for edge in instance["edges"]}
        gate_count = 0
        for layer in layers:
            require(type(layer) is list and len(layer) > 0, "empty or non-list layer")
            gate_count += len(layer)
            require(gate_count <= 4096, "gate parser limit exceeded")
            occupied = set()
            for gate in layer:
                fields(gate, ("u", "v", "theta", "phi"), "gate")
                first, second = gate["u"], gate["v"]
                require(type(first) is int and type(second) is int, "indices must be integers, not booleans")
                require(0 <= first < instance["n_modes"] and 0 <= second < instance["n_modes"],
                        "index out of range")
                require(first != second and tuple(sorted((first, second))) in hardware, "non-hardware gate")
                require(first not in occupied and second not in occupied, "overlapping gates in layer")
                occupied.update((first, second))
                for angle_name in ("theta", "phi"):
                    angle = gate[angle_name]
                    require(type(angle) in (int, float) and -math.pi <= angle <= math.pi,
                            "angle must be a finite number in [-pi,pi]")
        result[identifier] = circuit
    return result


def load_targets():
    payload = (HIDDEN / "targets.json").read_bytes()
    manifest = json.loads((HIDDEN / "freeze.json").read_text())
    if hashlib.sha256(payload).hexdigest() != manifest["target_sha256"]:
        raise RuntimeError("frozen target hash mismatch")
    document = json.loads(payload)
    if document["version"] != 1 or document["task"] != "local_slater_v1":
        raise RuntimeError("invalid frozen target version")
    instances = document["instances"]
    if len(instances) != 4 or len({instance["id"] for instance in instances}) != 4:
        raise RuntimeError("invalid frozen instance set")
    for instance in instances:
        size, particles = instance["n_modes"], instance["n_particles"]
        encoded = instance["target_projector"]
        target = np.asarray(encoded["real"]) + 1j * np.asarray(encoded["imag"])
        if target.shape != (size, size) or not np.isfinite(target).all():
            raise RuntimeError("invalid target matrix")
        integrity = max(np.linalg.norm(target - target.conj().T),
                        np.linalg.norm(target @ target - target),
                        abs(np.trace(target) - particles))
        eigenvalues = np.linalg.eigvalsh(target)
        if integrity > 1e-11 or eigenvalues[-particles] - eigenvalues[-particles - 1] < 0.999999999:
            raise RuntimeError("target is not a well-conditioned occupied projector")
    return instances, manifest["target_sha256"]


def dense_simulation(instance, circuit):
    size = instance["n_modes"]
    evolution = np.eye(size, dtype=np.complex128)
    for layer in circuit["layers"]:
        layer_matrix = np.eye(size, dtype=np.complex128)
        for gate in layer:
            first, second = gate["u"], gate["v"]
            cosine = np.cos(gate["theta"])
            mixing = np.sin(gate["theta"]) * np.exp(1j * gate["phi"])
            layer_matrix[first, first] = layer_matrix[second, second] = cosine
            layer_matrix[first, second] = -mixing.conjugate()
            layer_matrix[second, first] = mixing
        evolution = layer_matrix @ evolution
    orbitals = evolution[:, instance["initial_occupied"]]
    density = orbitals @ orbitals.conj().T
    integrity = max(float(np.linalg.norm(evolution.conj().T @ evolution - np.eye(size), "fro")),
                    float(np.linalg.norm(density @ density - density, "fro")))
    if not np.isfinite(density).all() or integrity > 1e-10:
        raise ArtifactError("numerical unitarity/projector integrity failure")
    return orbitals, density, integrity


def check_instance(instance, circuit):
    orbitals, actual, integrity = dense_simulation(instance, circuit)
    encoded = instance["target_projector"]
    target = np.asarray(encoded["real"]) + 1j * np.asarray(encoded["imag"])
    error = float(np.sqrt(np.sum(np.abs(actual - target) ** 2)))
    _, eigenvectors = np.linalg.eigh((target + target.conj().T) * 0.5)
    overlap = eigenvectors[:, -instance["n_particles"]:].conj().T @ orbitals
    singular_values = np.minimum(1.0, np.maximum(0.0, np.linalg.svd(overlap, compute_uv=False)))
    fidelity = float(np.prod(np.square(singular_values)))
    infidelity = max(0.0, 1.0 - fidelity)
    gates = sum(len(layer) for layer in circuit["layers"])
    depth = len(circuit["layers"])
    accurate = error <= instance["tolerances"]["projector_frobenius"] and infidelity <= instance["tolerances"]["slater_infidelity"]
    within = gates <= instance["budgets"]["max_gates"] and depth <= instance["budgets"]["max_depth"]
    resource = min(1.0, instance["budgets"]["max_gates"] / max(1, gates),
                   instance["budgets"]["max_depth"] / max(1, depth)) if accurate else 0.0
    return {"id": instance["id"], "family": instance["family"], "gates": gates, "depth": depth,
            "projector_error": error, "slater_fidelity": fidelity, "slater_infidelity": infidelity,
            "integrity_error": integrity, "accurate": bool(accurate), "within_budget": bool(within),
            "certified": bool(accurate and within), "resource_score": resource}


def failure(reason, infrastructure=False):
    return {"core_score": 0.0, "worst_family_score": 0.0, "resource_score": 0.0,
            "runtime_score": None, "valid": False, "passed": False,
            "reason": str(reason)[:500], "infrastructure_error": infrastructure, "instances": []}


def evaluate(directory):
    started = time.perf_counter()
    try:
        instances, digest = load_targets()
    except (OSError, ValueError, KeyError, RuntimeError, np.linalg.LinAlgError) as error:
        report = failure(error, infrastructure=True)
        report["evaluation_seconds"] = time.perf_counter() - started
        return report
    try:
        indexed = load_artifact(directory, instances)
        metrics = [check_instance(instance, indexed[instance["id"]]) for instance in instances]
        families = {}
        for metric in metrics:
            families.setdefault(metric["family"], []).append(int(metric["certified"]))
        family_scores = {name: sum(values) / len(values) for name, values in families.items()}
        count = sum(metric["certified"] for metric in metrics)
        report = {"core_score": count / len(metrics), "worst_family_score": min(family_scores.values()),
                  "resource_score": sum(metric["resource_score"] for metric in metrics) / len(metrics),
                  "runtime_score": None, "valid": True, "passed": count == len(metrics),
                  "reason": "all instances certified" if count == len(metrics) else
                            f"{count}/{len(metrics)} certified; inspect accuracy and budget flags",
                  "family_scores": family_scores, "instances": metrics, "infrastructure_error": False}
    except (ValueError, OSError, TypeError, UnicodeError, RecursionError, OverflowError, np.linalg.LinAlgError) as error:
        report = failure(error)
    report["target_sha256"] = digest
    report["evaluation_seconds"] = time.perf_counter() - started
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("submission_dir")
    parser.add_argument("--report", type=Path)
    arguments = parser.parse_args()
    report = evaluate(arguments.submission_dir)
    payload = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.report:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(payload)
    print(payload, end="")
    return 3 if report["infrastructure_error"] else 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
