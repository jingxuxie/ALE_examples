import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

from reference import PAULI_X, PAULI_Y, PAULI_Z, fourier_hoppings, matrix_values, spectral_certificate, topology_certificate


ROOT = Path(__file__).resolve().parents[1]


def reject_constant(value):
    raise ValueError("nonfinite_json_constant")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def validate_witness(witness, config):
    expected = {"schema_version", "mass", "spin_orbit", "orbital_mass", "scalar"}
    if not isinstance(witness, dict) or set(witness) != expected:
        raise ValueError("invalid_witness_keys")
    if type(witness["schema_version"]) is not int or witness["schema_version"] != 1:
        raise ValueError("invalid_schema_version")
    mass = witness["mass"]
    if type(mass) not in (int, float) or not math.isfinite(mass) or not config["mass_bounds"][0] <= mass <= config["mass_bounds"][1]:
        raise ValueError("invalid_mass")
    nonzero = 0
    for name, length in (("spin_orbit", 11), ("orbital_mass", 9), ("scalar", 9)):
        values = witness[name]
        if not isinstance(values, list) or len(values) != length:
            raise ValueError("invalid_coefficient_array")
        for value in values:
            if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > config[name + "_bound"]:
                raise ValueError("invalid_coefficient")
            nonzero += value != 0.0
    if nonzero > config["maximum_nonzero_channels"]:
        raise ValueError("support_budget_exceeded")
    return int(nonzero)


def load_witness(path, config):
    with path.open("rb") as handle:
        payload = handle.read(config["maximum_json_bytes"] + 1)
    if len(payload) > config["maximum_json_bytes"]:
        raise ValueError("witness_too_large")
    witness = json.loads(payload, object_pairs_hook=unique_object, parse_constant=reject_constant)
    validate_witness(witness, config)
    return witness, hashlib.sha256(payload).hexdigest()


def verify_freeze():
    manifest = json.loads((ROOT / "evaluator/hidden/freeze.json").read_text())
    for relative, digest in manifest["sha256"].items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest:
            raise RuntimeError("frozen_contract_changed:" + relative)
    return manifest


def manufacturing_audit(witness, spectral, config, checks):
    generator = np.random.default_rng(checks["manufacturing_seed"])
    mesh = checks["manufacturing_mesh"]
    axis = 2.0 * np.pi * (np.arange(mesh) + 0.371) / mesh - np.pi
    horizontal, vertical = np.meshgrid(axis, axis + 0.173 * 2.0 * np.pi / mesh, indexing="ij")
    results = []
    for trial in range(checks["manufacturing_trials"]):
        perturbed = dict(witness)
        for channel in ("spin_orbit", "orbital_mass", "scalar"):
            errors = generator.choice([-1.0, 1.0], len(witness[channel])) if trial % 2 == 0 else generator.uniform(-1.0, 1.0, len(witness[channel]))
            perturbed[channel] = (np.asarray(witness[channel]) * (1.0 + config["relative_coefficient_radius"] * errors)).tolist()
        mass_error = config["mass_error_radius"] * float(generator.choice([-1.0, 1.0])) if trial % 2 == 0 else float(generator.uniform(-config["mass_error_radius"], config["mass_error_radius"]))
        anisotropy = config["anisotropy_radius"] * float(generator.choice([-1.0, 1.0])) if trial % 2 == 0 else float(generator.uniform(-config["anisotropy_radius"], config["anisotropy_radius"]))
        matrix = matrix_values(fourier_hoppings(perturbed), horizontal, vertical) + mass_error * PAULI_Z
        matrix += anisotropy * (np.sin(horizontal)[..., None, None] * PAULI_X - np.sin(vertical)[..., None, None] * PAULI_Y)
        spectrum = np.linalg.eigvalsh(matrix)
        lower, upper = spectrum[..., 0], spectrum[..., 1]
        width = float(np.ptp(lower))
        direct = float(np.min(upper - lower))
        indirect = float(np.min(upper) - np.max(lower))
        consistent = width <= spectral["certified_bandwidth"] + 1e-8 and direct >= spectral["certified_direct_gap"] - 1e-8 and indirect >= spectral["certified_indirect_gap"] - 1e-8
        if not consistent:
            raise RuntimeError("manufacturing_audit_contradicts_certificate")
        results.append({"width": width, "direct": direct, "indirect": indirect})
    return {"trials": len(results), "all_within_public_box": True, "all_consistent": True, "worst_observed_width": max(result["width"] for result in results), "minimum_observed_direct_gap": min(result["direct"] for result in results), "minimum_observed_indirect_gap": min(result["indirect"] for result in results)}


def evaluate(candidate):
    started = time.monotonic()
    freeze = verify_freeze()
    config = json.loads((ROOT / "participant/input/model.json").read_text())
    target = json.loads((ROOT / "participant/input/targets.json").read_text())
    checks = json.loads((ROOT / "evaluator/hidden/checks.json").read_text())
    witness, digest = load_witness(candidate, config)
    spectral = spectral_certificate(witness, config)
    topology = topology_certificate(witness, config["topology_mesh"])
    second_topology = topology_certificate(witness, config["topology_mesh"], tuple(checks["topology_shift"]), checks["gauge_seed"])
    topological = all(result["certified"] and result.get("chern") == target["chern"] for result in (topology, second_topology))
    score = 0.0
    accepted = False
    audits = None
    if spectral["certified"] and topological:
        ratios = [target["maximum_certified_bandwidth"] / spectral["certified_bandwidth"], spectral["certified_direct_gap"] / target["minimum_certified_direct_gap"], spectral["certified_indirect_gap"] / target["minimum_certified_indirect_gap"]]
        score = float(max(0.0, min(1.0, *ratios)))
        accepted = bool(all(value >= 1.0 for value in ratios))
        if spectral["certified_direct_gap"] > 0.0:
            audits = manufacturing_audit(witness, spectral, config, checks)
    return {"mode": "C", "valid_input": True, "accepted": accepted, "success": accepted, "score": score, "target_frozen": True, "freeze_id": freeze["freeze_id"], "candidate_sha256": digest, "nonzero_channels": validate_witness(witness, config), "spectral": spectral, "topology": topology, "shifted_topology": second_topology, "manufacturing_audit": audits, "elapsed_seconds": time.monotonic() - started}


def main():
    parser = argparse.ArgumentParser(description="Validate a data-only robust Chern-band witness")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--candidate", "--witness", type=Path)
    source.add_argument("--submission-dir", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    candidate = arguments.candidate if arguments.candidate else arguments.submission_dir / "witness.json"
    try:
        report = evaluate(candidate)
    except (ValueError, OverflowError, RecursionError, UnicodeError, OSError) as error:
        report = {"valid_input": False, "accepted": False, "success": False, "score": 0.0, "error": str(error)}
    except RuntimeError as error:
        report = {"valid_input": False, "accepted": False, "success": False, "score": 0.0, "evaluator_error": str(error)}
    payload = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(payload)
    print(payload, end="")


if __name__ == "__main__":
    main()
