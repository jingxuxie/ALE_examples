import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(result)
    return result


def dense_product(operators):
    result = np.ones((1, 1), dtype=np.complex128)
    for site in reversed(range(4)):
        result = np.kron(result, operators.get(site, np.eye(2)))
    return result


def main():
    checker = module("ratchet_checker", ROOT / "evaluator" / "evaluate.py")
    previous = module("previous_checker", ROOT / "generations" / "generation_0" / "evaluator" / "evaluate.py")
    public = module("ratchet_public", ROOT / "participant" / "workspace" / "simulator.py")
    library = ctypes.CDLL(str(HERE.parent / "statevector.so"))
    array = np.ctypeslib.ndpointer(dtype=np.float64, flags="C_CONTIGUOUS")
    library.evaluate.argtypes = [array, array, ctypes.c_int, ctypes.c_int, array, array]
    library.evaluate.restype = None
    scenarios, digest = checker.load_scenarios()
    old_scenarios, old_digest = previous.load_scenarios()
    for old, new in zip(old_scenarios, scenarios[:63]):
        assert all(old[key] == new[key] for key in ("gain_a", "gain_b", "zz_common", "zz_local"))
        assert new["z_drift_radians_per_layer"] == [0.0] * 12
    selected = [scenarios[index] for index in (0, 7, 38, 63, 66, 91, 176, 222)]
    rows = np.ascontiguousarray([[row["gain_a"], row["gain_b"], row["zz_common"],
                                 *row["zz_local"], *row["z_drift_radians_per_layer"]] for row in selected])
    generator = np.random.default_rng(880127)
    circuit_error = 0.0
    compiled_error = 0.0
    norm_error = 0.0
    zero_drift_error = 0.0
    for trial in range(3):
        angles = generator.uniform(-np.pi, np.pi, (24, 2))
        states = public.simulate(angles, selected)
        scores = np.zeros(len(rows))
        gradients = np.zeros((len(rows), 48))
        library.evaluate(np.ascontiguousarray(angles.reshape(-1)), rows, len(rows), 0, scores, gradients)
        for index, scenario in enumerate(selected):
            state = checker.evolve(angles, scenario)
            circuit_error = max(circuit_error, float(np.max(np.abs(state - states[index]))))
            norm_error = max(norm_error, abs(float(np.vdot(state, state).real) - 1))
            fidelity = float(abs((state[0] + state[-1]) / np.sqrt(2)) ** 2)
            compiled_error = max(compiled_error, abs(fidelity - scores[index]))
            if not any(scenario["z_drift_radians_per_layer"]):
                zero_drift_error = max(zero_drift_error, float(np.max(np.abs(state - previous.evolve(angles, scenario)))))
    vector = generator.normal(size=16) + 1j * generator.normal(size=16)
    vector /= np.linalg.norm(vector)
    pauli_x = np.array([[0, 1], [1, 0]])
    pauli_z = np.diag([1, -1])
    gate_error = 0.0
    for site in range(4):
        angle = generator.uniform(-np.pi, np.pi)
        gates = [np.cos(angle / 2) * np.eye(2) - 1j * np.sin(angle / 2) * pauli_x,
                 np.diag(np.exp(-0.5j * angle * np.array([1, -1])))]
        for gate in gates:
            trusted = checker.apply_one(vector.reshape((2,) * 4), gate, site, 4).reshape(-1)
            expected = dense_product({site: gate}) @ vector
            gate_error = max(gate_error, float(np.max(np.abs(trusted - expected))))
    for first, second in ((0, 1), (1, 2), (2, 3), (3, 0)):
        exponent = generator.uniform(-1, 1)
        expected = (np.cos(exponent) * np.eye(16) + 1j * np.sin(exponent) * dense_product({first: pauli_z, second: pauli_z})) @ vector
        trusted = checker.apply_zz(vector.reshape((2,) * 4), first, second, exponent, 4).reshape(-1)
        gate_error = max(gate_error, float(np.max(np.abs(trusted - expected))))
    fresh = np.asarray(json.loads((ROOT / "champions" / "generation_1" / "pulses.json").read_text())["angles"])
    drift_state = checker.evolve(fresh, scenarios[143])
    drift_parity = float(np.vdot(drift_state, drift_state[::-1]).real)
    assert drift_parity < 0.99
    valid = {"schema_version": 1, "angles": [[0.0, 0.0]] * 24}
    invalid = {
        "nan": json.dumps(dict(valid, angles=[[float("nan"), 0]] * 24)),
        "inf": json.dumps(dict(valid, angles=[[float("inf"), 0]] * 24)),
        "bool": json.dumps(dict(valid, angles=[[True, 0]] * 24)),
        "string": json.dumps(dict(valid, angles=[["0", 0]] * 24)),
        "null": json.dumps(dict(valid, angles=[[None, 0]] * 24)),
        "huge_integer": json.dumps(dict(valid, angles=[[10 ** 500, 0]] * 24)),
        "bound": json.dumps(dict(valid, angles=[[float(np.pi + 1e-8), 0]] * 24)),
        "depth": json.dumps(dict(valid, angles=[[0, 0]] * 23)),
        "width": json.dumps(dict(valid, angles=[[0, 0, 0]] * 24)),
        "bool_version": json.dumps(dict(valid, schema_version=True)),
        "float_version": json.dumps(dict(valid, schema_version=1.0)),
        "extra": json.dumps(dict(valid, claimed_score=1)),
        "duplicate": '{"schema_version":1,"schema_version":1,"angles":[]}',
        "top_level": "[]", "oversize": " " * 65537, "malformed": "{"
    }
    rejected = []
    with tempfile.TemporaryDirectory(dir=HERE) as temporary:
        directory = Path(temporary)
        artifact = directory / "pulses.json"
        for name, content in invalid.items():
            artifact.write_text(content)
            try:
                checker.read_artifact(directory)
            except (ValueError, OverflowError):
                rejected.append(name)
        for name in ("nan", "bool", "string"):
            artifact.write_text(invalid[name])
            output = directory / (name + "_result.json")
            process = subprocess.run([sys.executable, str(ROOT / "evaluator" / "evaluate.py"),
                                      "--submission", str(directory), "--output", str(output)],
                                     capture_output=True, text=True, timeout=30)
            result = json.loads(output.read_text())
            assert process.returncode == 2 and not result["valid"]
            assert all(result[key] == 0 for key in ("score", "core_score", "worst_family_score", "resource_score"))
            assert result["runtime"] >= 0 and result["reason"]
        artifact.rename(directory / "target.json")
        artifact.symlink_to(directory / "target.json")
        try:
            checker.read_artifact(directory)
        except ValueError:
            rejected.append("symlink")
        artifact.unlink()
        try:
            checker.read_artifact(directory)
        except ValueError:
            rejected.append("missing")
        staged = directory / "participant"
        shutil.copytree(ROOT / "participant", staged, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        process = subprocess.run([sys.executable, "baseline/run_baseline.py", "--mode", "random",
                                  "--trials", "1", "--output", str(directory / "smoke")],
                                 cwd=staged, capture_output=True, text=True, timeout=120)
        assert process.returncode == 0, process.stderr
    expected_baseline = hashlib.sha256((ROOT / "generations" / "generation_0" / "participant" / "baseline" / "pulses.json").read_bytes()).hexdigest()
    assert hashlib.sha256((ROOT / "participant" / "baseline" / "pulses.json").read_bytes()).hexdigest() == expected_baseline
    private_hashes = {hashlib.sha256(path.read_bytes()).hexdigest() for path in (ROOT / "champions" / "generation_1").rglob('*') if path.is_file()}
    for path in HERE.parent.glob("*candidate.json"):
        private_hashes.add(hashlib.sha256(path.read_bytes()).hexdigest())
    leaks = [str(path.relative_to(ROOT)) for path in (ROOT / "participant").rglob('*')
             if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() in private_hashes]
    assert not leaks
    report = {"passed": circuit_error < 1e-11 and compiled_error < 1e-11 and norm_error < 1e-11
              and zero_drift_error < 1e-11 and gate_error < 1e-12 and len(rejected) == 18,
              "full_state_comparisons": 24, "dense_gate_checks": 12,
              "max_public_trusted_state_error": circuit_error,
              "max_compiled_trusted_fidelity_error": compiled_error,
              "max_zero_drift_generation_0_state_error": zero_drift_error,
              "max_norm_error": norm_error, "max_dense_gate_error": gate_error,
              "nonzero_drift_global_x_expectation": drift_parity,
              "parity_assertion_scope": "zero_drift_only", "old_scenarios_preserved": 63,
              "hostile_artifacts_rejected": rejected, "invalid_cli_schema_checked": 3,
              "staged_public_baseline_runner_passed": True, "original_weak_baseline_unchanged": True,
              "private_artifact_leaks": leaks, "scenario_sha256": digest,
              "generation_0_scenario_sha256": old_digest}
    (HERE / "audit_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)
    assert report["passed"]


if __name__ == "__main__":
    main()
