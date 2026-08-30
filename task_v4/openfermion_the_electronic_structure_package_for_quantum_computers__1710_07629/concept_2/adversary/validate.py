"""Private independent numerical and malformed-artifact regression suite."""

import copy
import importlib.util
import itertools
import json
import math
import os
from pathlib import Path
import sys
import tempfile

import numpy as np
from scipy.linalg import expm


ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "participant/workspace"))
import simulator


def module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(loaded)
    return loaded


official = module("official_verifier", ROOT / "evaluator/evaluate.py")
baseline = module("generic_compiler", ROOT / "participant/baseline/compile.py")


def hopping(mask, destination, source):
    if not mask & (1 << source):
        return None
    sign = (-1) ** (mask & ((1 << source) - 1)).bit_count()
    cleared = mask ^ (1 << source)
    if cleared & (1 << destination):
        return None
    sign *= (-1) ** (cleared & ((1 << destination) - 1)).bit_count()
    return cleared | (1 << destination), sign


def fock_evolve(size, particles, occupied, gates):
    configurations = list(itertools.combinations(range(size), particles))
    masks = [sum(1 << mode for mode in configuration) for configuration in configurations]
    positions = {mask: index for index, mask in enumerate(masks)}
    state = np.zeros(len(masks), dtype=complex)
    state[positions[sum(1 << mode for mode in occupied)]] = 1
    for gate in gates:
        generator = np.zeros((len(masks), len(masks)), dtype=complex)
        first, second = gate["u"], gate["v"]
        for column, mask in enumerate(masks):
            for destination, source, coefficient in (
                (second, first, np.exp(1j * gate["phi"])),
                (first, second, -np.exp(-1j * gate["phi"]))
            ):
                outcome = hopping(mask, destination, source)
                if outcome is not None:
                    updated, sign = outcome
                    generator[positions[updated], column] += coefficient * sign
        state = expm(gate["theta"] * generator) @ state
    covariance = np.zeros((size, size), dtype=complex)
    for row in range(size):
        for column in range(size):
            for position, mask in enumerate(masks):
                outcome = hopping(mask, column, row)
                if outcome is not None:
                    updated, sign = outcome
                    covariance[row, column] += state[positions[updated]].conjugate() * state[position] * sign
    return state, covariance, configurations


def numerical_crosschecks():
    rng = np.random.default_rng(192837)
    instance = {"n_modes": 6, "n_particles": 3, "initial_occupied": [0, 2, 5]}
    states, frames = [], []
    results = {}
    for sample in range(2):
        gates = []
        for _ in range(15):
            first, second = [int(mode) for mode in rng.choice(6, 2, replace=False)]
            gates.append({"u": first, "v": second, "theta": float(rng.uniform(-1.3, 1.3)),
                          "phi": float(rng.uniform(-math.pi, math.pi))})
        frame = simulator.simulate(instance, {"layers": [[gate] for gate in gates]})
        state, covariance, configurations = fock_evolve(6, 3, instance["initial_occupied"], gates)
        determinants = np.asarray([np.linalg.det(frame[list(configuration), :]) for configuration in configurations])
        amplitude_error = float(np.linalg.norm(state - determinants))
        covariance_error = float(np.linalg.norm(covariance - frame @ frame.conj().T))
        assert amplitude_error < 2e-13 and covariance_error < 2e-13
        results[f"fock_amplitude_error_{sample}"] = amplitude_error
        results[f"fock_covariance_error_{sample}"] = covariance_error
        states.append(state)
        frames.append(frame)
    overlap_error = abs(abs(np.vdot(states[0], states[1])) ** 2 - abs(np.linalg.det(frames[0].conj().T @ frames[1])) ** 2)
    assert overlap_error < 2e-13
    results["fock_slater_fidelity_error"] = float(overlap_error)
    gauge, _ = np.linalg.qr(rng.normal(size=(3, 3)) + 1j * rng.normal(size=(3, 3)))
    gauge_frame = frames[0] @ gauge
    gauge_error = float(np.linalg.norm(gauge_frame @ gauge_frame.conj().T - frames[0] @ frames[0].conj().T))
    assert gauge_error < 2e-13
    results["occupied_gauge_projector_error"] = gauge_error
    size = 7
    hardware = {"n_modes": size, "edges": [[mode, mode + 1] for mode in range(size - 1)]}
    routing_error = 0.0
    for first in range(size):
        for second in range(size):
            if first == second:
                continue
            gate = {"u": first, "v": second, "theta": 0.73, "phi": -0.84}
            expected = np.eye(size, dtype=complex)
            simulator.apply_gate(expected, gate)
            actual = np.eye(size, dtype=complex)
            for native in baseline.route(gate, hardware):
                simulator.apply_gate(actual, native)
            routing_error = max(routing_error, float(np.linalg.norm(actual - expected)))
    assert routing_error < 2e-13
    results["all_ordered_pair_routing_error"] = routing_error
    return results


def main():
    witness = json.loads((ROOT / "evaluator/hidden/witness/solution.json").read_text())
    instances = json.loads((ROOT / "participant/input/instances.json").read_text())["instances"]
    assert (ROOT / "participant/input/instances.json").read_bytes() == (ROOT / "evaluator/hidden/targets.json").read_bytes()
    results = []
    numerical = numerical_crosschecks()
    with tempfile.TemporaryDirectory(prefix="checks_", dir=ROOT / "adversary") as temporary:
        directory = Path(temporary)
        path = directory / "solution.json"

        def check(name, value, valid, passed=False, core=None, raw=False):
            if path.exists() or path.is_symlink():
                path.unlink()
            path.write_bytes(value if raw else json.dumps(value, allow_nan=True).encode())
            authoritative = official.evaluate(directory)
            public = simulator.evaluate(directory)
            for report in (authoritative, public):
                assert report["valid"] == valid, (name, report)
                assert report["passed"] == passed, (name, report)
                if core is not None:
                    assert report["core_score"] == core, (name, report)
            assert authoritative["core_score"] == public["core_score"]
            if valid:
                for private_metric, public_metric in zip(authoritative["instances"], public["instances"]):
                    assert abs(private_metric["projector_error"] - public_metric["projector_error"]) < 2e-12
                    assert abs(private_metric["slater_fidelity"] - public_metric["slater_fidelity"]) < 2e-12
            results.append({"name": name, "ok": True, "valid": authoritative["valid"],
                            "passed": authoritative["passed"], "core_score": authoritative["core_score"]})
            return authoritative

        check("private_witness", witness, True, True, 1.0)
        candidate = copy.deepcopy(witness)
        for circuit in candidate["circuits"]:
            circuit["layers"] = []
        check("identity_wrong_state", candidate, True, False, 0.0)
        candidate = copy.deepcopy(witness)
        candidate["circuits"][0]["layers"] = []
        partial = check("partial_credit_and_worst_family", candidate, True, False, 0.75)
        assert partial["worst_family_score"] == 0.5
        candidate = copy.deepcopy(witness)
        for circuit in candidate["circuits"]:
            for layer in circuit["layers"]:
                layer.reverse()
                for gate in layer:
                    gate["u"], gate["v"] = gate["v"], gate["u"]
                    gate["theta"], gate["phi"] = -gate["theta"], -gate["phi"]
        check("equivalent_ordered_edges_and_layer_order", candidate, True, True, 1.0)
        candidate = copy.deepcopy(witness)
        for circuit in candidate["circuits"]:
            for layer in circuit["layers"]:
                for gate in layer:
                    gate["phi"] = -gate["phi"]
        check("complex_conjugate_wrong_target", candidate, True, False, 0.0)
        candidate = copy.deepcopy(witness)
        candidate["circuits"][0]["layers"][0][0]["theta"] += 3e-7
        near = check("fidelity_roundoff_does_not_override_projector", candidate, True, False, 0.75)
        assert near["instances"][0]["slater_infidelity"] < 1e-8
        assert near["instances"][0]["projector_error"] > 1e-8
        for delta, expected_core, expected_pass in ((2e-9, 1.0, True), (2e-8, 0.75, False)):
            candidate = copy.deepcopy(witness)
            candidate["circuits"][0]["layers"][0][0]["theta"] += delta
            check("projector_threshold_" + str(delta), candidate, True, expected_pass, expected_core)
        candidate = copy.deepcopy(witness)
        circuit = candidate["circuits"][0]
        circuit["layers"] = [[gate] for layer in circuit["layers"] for gate in layer]
        report = check("exact_but_depth_over_budget", candidate, True, False, 0.75)
        assert report["instances"][0]["accurate"] and report["instances"][0]["gates"] < instances[0]["budgets"]["max_gates"]
        candidate = copy.deepcopy(witness)
        circuit = candidate["circuits"][0]
        for _ in range(4):
            first, second = instances[0]["edges"][0]
            circuit["layers"].append([{"u": first, "v": second, "theta": 0.0, "phi": 0.0}])
        report = check("identity_gates_still_count", candidate, True, False, 0.75)
        assert report["instances"][0]["accurate"] and report["instances"][0]["gates"] == 34
        mutations = [
            ("boolean_index", lambda item: item["circuits"][0]["layers"][0][0].update(u=True)),
            ("float_index", lambda item: item["circuits"][0]["layers"][0][0].update(u=1.0)),
            ("negative_index", lambda item: item["circuits"][0]["layers"][0][0].update(u=-1)),
            ("huge_index", lambda item: item["circuits"][0]["layers"][0][0].update(u=10 ** 100)),
            ("boolean_angle", lambda item: item["circuits"][0]["layers"][0][0].update(phi=False)),
            ("nan_angle", lambda item: item["circuits"][0]["layers"][0][0].update(phi=float("nan"))),
            ("infinite_angle", lambda item: item["circuits"][0]["layers"][0][0].update(theta=float("inf"))),
            ("huge_finite_angle", lambda item: item["circuits"][0]["layers"][0][0].update(theta=10 ** 100)),
            ("out_of_range_angle", lambda item: item["circuits"][0]["layers"][0][0].update(theta=3.2)),
            ("extra_score", lambda item: item.update(core_score=1)),
            ("boolean_version", lambda item: item.update(version=True)),
            ("missing_circuit", lambda item: item["circuits"].pop()),
            ("unknown_id", lambda item: item["circuits"][0].update(id="../hidden/witness")),
            ("duplicate_id", lambda item: item["circuits"][1].update(id=item["circuits"][0]["id"])),
            ("empty_layer", lambda item: item["circuits"][0]["layers"].append([])),
            ("layer_overlap", lambda item: item["circuits"][0]["layers"][0].append(item["circuits"][0]["layers"][0][0])),
            ("extra_gate_field", lambda item: item["circuits"][0]["layers"][0][0].update(matrix=[])),
            ("null_layers", lambda item: item["circuits"][0].update(layers=None)),
        ]
        for name, mutation in mutations:
            candidate = copy.deepcopy(witness)
            mutation(candidate)
            check(name, candidate, False, False, 0.0)
        edges = {frozenset(edge) for edge in instances[0]["edges"]}
        missing = next(pair for pair in itertools.combinations(range(instances[0]["n_modes"]), 2) if frozenset(pair) not in edges)
        candidate = copy.deepcopy(witness)
        candidate["circuits"][0]["layers"][0][0].update(u=missing[0], v=missing[1])
        check("nonedge", candidate, False)
        candidate = copy.deepcopy(witness)
        candidate["circuits"][0]["layers"] = [[candidate["circuits"][0]["layers"][0][0]]] * 4097
        check("parser_layer_cap", candidate, False)
        for name, payload in (
            ("duplicate_json_keys", b'{"version":1,"version":1,"circuits":[]}'),
            ("nonfinite_exponent", json.dumps(witness).replace('"theta":', '"theta":1e999,"unused":', 1).encode()),
            ("oversized_file", b" " * (2097152 + 1)),
            ("truncated_json", b'{"version":'),
            ("invalid_utf8", b'\xff'),
            ("deep_nesting", b'[' * 1500 + b']' * 1500),
        ):
            check(name, payload, False, raw=True)
        path.unlink()
        path.symlink_to(ROOT / "evaluator/hidden/witness/solution.json")
        assert not official.evaluate(directory)["valid"] and not simulator.evaluate(directory)["valid"]
        results.append({"name": "symlink_rejected", "ok": True})
        path.unlink()
        os.mkfifo(path)
        assert not official.evaluate(directory)["valid"] and not simulator.evaluate(directory)["valid"]
        results.append({"name": "fifo_rejected_without_blocking", "ok": True})
        path.unlink()
        assert not official.evaluate(directory)["valid"]
        results.append({"name": "missing_artifact_rejected", "ok": True})
        marker = directory / "executed"
        (directory / "solver.py").write_text("raise RuntimeError('must not execute submission code')\n")
        check("submission_python_not_executed", witness, True, True)
        assert not marker.exists()

    baseline_report = official.evaluate(ROOT / "attempts/baseline")
    public_baseline = simulator.evaluate(ROOT / "attempts/baseline")
    assert baseline_report["valid"] and not baseline_report["passed"] and baseline_report["core_score"] == 0
    assert all(metric["accurate"] and not metric["within_budget"] for metric in baseline_report["instances"])
    assert public_baseline["core_score"] == baseline_report["core_score"]
    witness_report = official.evaluate(ROOT / "evaluator/hidden/witness")
    assert witness_report["passed"]
    diagnostics = json.loads((ROOT / "evaluator/hidden/generation_diagnostics.json").read_text())
    assert all(item["occupied_unoccupied_gap"] > 0.999999999 for item in diagnostics)
    assert all(item["minimum_single_gate_deletion_error"] > 0.06 for item in diagnostics)
    report = {"passed": True, "artifact_checks": len(results), "checks": results,
              "independent_numerics": numerical, "baseline": baseline_report, "private_witness": witness_report,
              "target_sha256": witness_report["target_sha256"], "python": sys.version.split()[0],
              "numpy": np.__version__}
    (ROOT / "adversary/validation_report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"passed": True, "artifact_checks": len(results), "independent_numerics": numerical,
                      "baseline_core": baseline_report["core_score"], "witness_core": witness_report["core_score"]}, indent=2))


if __name__ == "__main__":
    main()
