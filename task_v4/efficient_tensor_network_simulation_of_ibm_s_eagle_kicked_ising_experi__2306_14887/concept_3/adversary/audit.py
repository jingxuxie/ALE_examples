"""Builder audit: independent dense gates, full circuits, and hostile artifacts."""

import importlib.util
import json
import math
import os
from pathlib import Path
import tempfile

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    imported = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(imported)
    return imported


def dense_product(n_qubits, operators):
    result = np.ones((1, 1), dtype=complex)
    for site in reversed(range(n_qubits)):
        result = np.kron(result, operators.get(site, np.eye(2)))
    return result


def main():
    checker = module("trusted_checker", ROOT / "evaluator" / "evaluate.py")
    public = module("public_simulator", ROOT / "participant" / "workspace" / "simulator.py")
    generator = np.random.default_rng(90814887)
    pauli_x = np.array([[0, 1], [1, 0]])
    pauli_z = np.diag([1, -1])
    state = generator.normal(size=16) + 1j * generator.normal(size=16)
    state /= np.linalg.norm(state)
    max_gate_error = 0.0
    for site in range(4):
        angle = generator.uniform(-3, 3)
        gate = np.cos(angle / 2) * np.eye(2) - 1j * np.sin(angle / 2) * pauli_x
        expected = dense_product(4, {site: gate}) @ state
        actual = checker.apply_one(state.reshape((2,) * 4), gate, site, 4).reshape(-1)
        max_gate_error = max(max_gate_error, float(np.max(np.abs(actual - expected))))
    for first, second in ((0, 1), (1, 2), (2, 3), (3, 0), (0, 2)):
        exponent = generator.uniform(-1, 1)
        generator_matrix = dense_product(4, {first: pauli_z, second: pauli_z})
        expected = (np.cos(exponent) * np.eye(16) + 1j * np.sin(exponent) * generator_matrix) @ state
        actual = checker.apply_zz(state.reshape((2,) * 4), first, second, exponent, 4).reshape(-1)
        max_gate_error = max(max_gate_error, float(np.max(np.abs(actual - expected))))
    scenarios, _ = checker.load_scenarios()
    selected = [scenarios[index] for index in (0, 7, 8, 20, 42, 62)]
    max_circuit_error = 0.0
    max_norm_error = 0.0
    max_parity_error = 0.0
    for trial in range(3):
        angles = generator.uniform(-np.pi, np.pi, (24, 2))
        batched = public.simulate(angles, selected)
        for index, scenario in enumerate(selected):
            trusted = checker.evolve(angles, scenario)
            max_circuit_error = max(max_circuit_error, float(np.max(np.abs(batched[index] - trusted))))
            max_norm_error = max(max_norm_error, abs(float(np.vdot(trusted, trusted).real) - 1))
            max_parity_error = max(max_parity_error, float(np.max(np.abs(trusted - trusted[::-1]))))
    sublattice_flip = sum(1 << site for site in range(0, 12, 2))
    all_edge_phase = np.exp(1j * np.pi / 4 * public.EDGE_SIGNS.sum(axis=0))
    commutator_error = float(np.max(np.abs(all_edge_phase - all_edge_phase[np.arange(4096) ^ sublattice_flip])))
    cat = np.zeros(4096)
    cat[0] = cat[-1] = 1 / np.sqrt(2)
    projected = (cat + cat[np.arange(4096) ^ sublattice_flip]) / 2
    forbidden_full_layer_bound = float(np.vdot(projected, projected).real)
    matching_phase = np.exp(1j * np.pi / 4 * public.EDGE_SIGNS[::2].sum(axis=0))
    matching_commutator = float(np.max(np.abs(matching_phase - matching_phase[np.arange(4096) ^ sublattice_flip])))
    valid = {"schema_version": 1, "angles": [[0.0, 0.0] for layer in range(24)]}
    hostile = {
        "nan": json.dumps(dict(valid, angles=[[float("nan"), 0]] * 24)),
        "infinity": json.dumps(dict(valid, angles=[[float("inf"), 0]] * 24)),
        "bool_angle": json.dumps(dict(valid, angles=[[True, 0]] * 24)),
        "string_angle": json.dumps(dict(valid, angles=[["0.0", 0]] * 24)),
        "huge_integer": json.dumps(dict(valid, angles=[[10 ** 500, 0]] * 24)),
        "wrong_depth": json.dumps(dict(valid, angles=[[0, 0]] * 23)),
        "wrong_width": json.dumps(dict(valid, angles=[[0, 0, 0]] * 24)),
        "out_of_bounds": json.dumps(dict(valid, angles=[[math.pi + 1e-10, 0]] * 24)),
        "boolean_version": json.dumps(dict(valid, schema_version=True)),
        "float_version": json.dumps(dict(valid, schema_version=1.0)),
        "extra_fields": json.dumps(dict(valid, claimed_score=1)),
        "wrong_top_level": "[]",
        "duplicate_key": '{"schema_version":1,"schema_version":1,"angles":[]}',
        "oversize": " " * 65537,
        "malformed_json": "{",
    }
    rejected = []
    with tempfile.TemporaryDirectory(dir=ROOT / "adversary") as temporary:
        directory = Path(temporary)
        artifact = directory / "pulses.json"
        for name, content in hostile.items():
            artifact.write_text(content)
            try:
                checker.read_artifact(directory)
            except (ValueError, OverflowError):
                rejected.append(name)
        artifact.write_text(json.dumps(valid))
        checker.read_artifact(directory)
        target = directory / "target.json"
        artifact.rename(target)
        artifact.symlink_to(target)
        try:
            checker.read_artifact(directory)
        except ValueError:
            rejected.append("symlink")
        artifact.unlink()
        try:
            checker.read_artifact(directory)
        except ValueError:
            rejected.append("missing")
    report = {"dense_gate_tests": 9, "full_circuit_comparisons": 18,
              "max_dense_gate_error": max_gate_error, "max_full_state_error": max_circuit_error,
              "max_norm_error": max_norm_error, "max_global_parity_error": max_parity_error,
              "all_edge_clifford_sublattice_commutator": commutator_error,
              "all_edge_clifford_GHZ_fidelity_upper_bound": forbidden_full_layer_bound,
              "split_matching_sublattice_commutator": matching_commutator,
              "hostile_artifacts_rejected": rejected,
              "passed": max_gate_error < 1e-12 and max_circuit_error < 1e-11
              and max_norm_error < 1e-11 and max_parity_error < 1e-11
              and commutator_error < 1e-12 and abs(forbidden_full_layer_bound - 0.5) < 1e-12
              and matching_commutator > 1 and len(rejected) == len(hostile) + 2}
    (ROOT / "adversary" / "audit_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
