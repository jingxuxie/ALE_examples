import hashlib
import json
import math
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from scipy.linalg import expm
from scipy.special import expit


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
sys.path.insert(0, str(ROOT / "evaluator" / "hidden"))
from evaluate import evaluate, load_submission, score_predictions
from simulator import predict, unpack


IDENTITY = np.eye(2, dtype=complex)
PAULI = np.array([[[0, 1], [1, 0]], [[0, -1j], [1j, 0]], [[1, 0], [0, -1]]], dtype=complex)
INPUTS = np.array([[0., 0.], [1., 0.], [-1., 0.], [0., 1.], [0., -1.]])
PREPS = np.array([[1., 0., 0.], [-1., 0., 0.], [0., 1., 0.], [0., -1., 0.], [0., 0., 1.], [0., 0., -1.]])


def load(path):
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


def channel(density, error, gate, gamma, depolarization):
    ideal_hamiltonian = np.zeros((2, 2), dtype=complex)
    if gate:
        axis = 0 if gate in (1, 2) else 1
        direction = 1. if gate in (1, 3) else -1.
        ideal_hamiltonian = direction * np.pi * PAULI[axis] / 4.
    unitary = expm(-0.5j * np.einsum("k,kab->ab", error, PAULI)) @ expm(-1j * ideal_hamiltonian)
    evolved = unitary @ density @ unitary.conj().T
    first = np.diag([1., np.sqrt(1. - gamma)])
    second = np.array([[0., np.sqrt(gamma)], [0., 0.]])
    evolved = first @ evolved @ first.conj().T + second @ evolved @ second.conj().T
    return (1. - depolarization) * evolved + depolarization * np.trace(evolved) * IDENTITY / 2.


def density_prediction(parameters, record):
    fields = unpack(parameters)
    time_value = float(record["time"])
    initial = (IDENTITY + 0.985 * np.einsum("k,kab->ab", PREPS[int(record["preparation"])], PAULI)) / 2.
    occupied = expit(fields["reset"] @ [1., 2. * time_value - 1., math.sin(2. * math.pi * time_value)])
    joint = np.stack([(1. - occupied) * initial, occupied * initial])
    memory = np.zeros(2)
    minimum_eigenvalue = 1.
    maximum_trace_error = 0.
    for position in range(int(record["length"])):
        gate = int(record["gates"][position])
        phase = 2. * math.pi * fields["frequency"][0] * time_value
        common = (fields["gate_bias"][gate] + fields["memory_matrix"] @ memory
                  + fields["drift_sin"] * math.sin(phase) + fields["drift_cos"] * math.cos(phase))
        branches = np.stack([channel(joint[state], common + (2 * state - 1) * fields["latent_vector"],
                                    gate, fields["gamma"][gate], fields["depolarization"][gate])
                             for state in range(2)])
        features = np.array([1., float(gate != 0), memory[0] - memory[1], math.sin(2. * math.pi * time_value)])
        probability_01, probability_10 = expit(fields["transition"] @ features)
        transition = np.array([[1. - probability_01, probability_01], [probability_10, 1. - probability_10]])
        joint = np.einsum("sd,sab->dab", transition, branches)
        memory = fields["retention"] * memory + (1. - fields["retention"]) * INPUTS[gate]
        minimum_eigenvalue = min(minimum_eigenvalue, float(np.linalg.eigvalsh(joint).min()))
        maximum_trace_error = max(maximum_trace_error, float(abs(np.trace(joint.sum(axis=0)) - 1.)))
    expectation = float(np.trace(joint.sum(axis=0) @ PAULI[int(record["measurement"])]).real)
    return 0.008 + 0.979 * (1. - expectation) / 2., minimum_eigenvalue, maximum_trace_error


def physics_audit(parameters, splits):
    generator = np.random.default_rng(317029)
    differences = []
    eigenvalues = []
    trace_errors = []
    checked = 0
    for split in splits.values():
        selected = generator.choice(len(split["ids"]), 16, replace=False)
        for index in selected:
            record = {key: values[index] for key, values in split.items()}
            subset = {key: values[index:index + 1] for key, values in split.items()}
            device_parameters = parameters[int(record["device"])]
            probability, minimum_eigenvalue, trace_error = density_prediction(device_parameters, record)
            bloch_probability = float(predict(device_parameters, subset)[0])
            differences.append(abs(probability - bloch_probability))
            eigenvalues.append(minimum_eigenvalue)
            trace_errors.append(trace_error)
            checked += 1
    choi_minimum = 1.
    choi_trace_error = 0.
    for iteration in range(48):
        error = generator.uniform(-0.25, 0.25, 3)
        gamma = float(generator.uniform(0., 0.02))
        depolarization = float(generator.uniform(0., 0.02))
        gate = int(generator.integers(5))
        choi = np.zeros((4, 4), dtype=complex)
        for row in range(2):
            for column in range(2):
                basis = np.zeros((2, 2), dtype=complex)
                basis[row, column] = 1.
                evolved = channel(basis, error, gate, gamma, depolarization)
                choi[2 * row:2 * row + 2, 2 * column:2 * column + 2] = evolved
                choi_trace_error = max(choi_trace_error, float(abs(np.trace(evolved) - (row == column))))
        choi_minimum = min(choi_minimum, float(np.linalg.eigvalsh(choi).min()))
    minimum_transition = 1.
    maximum_transition = 0.
    for device_parameters in parameters:
        fields = unpack(device_parameters)
        features = np.column_stack([np.ones(2048), generator.integers(0, 2, 2048),
                                    generator.uniform(-2., 2., 2048), generator.uniform(-1., 1., 2048)])
        transitions = expit(features @ fields["transition"].T)
        minimum_transition = min(minimum_transition, float(transitions.min()))
        maximum_transition = max(maximum_transition, float(transitions.max()))
    assert max(differences) < 2e-11, differences
    assert min(eigenvalues) > -2e-12
    assert max(trace_errors) < 2e-11
    assert choi_minimum > -2e-12 and choi_trace_error < 2e-12
    assert 0. < minimum_transition < maximum_transition < 1.
    return {"independent_density_matrix_circuits": checked,
            "maximum_bloch_density_probability_difference": max(differences),
            "minimum_joint_density_eigenvalue": min(eigenvalues),
            "maximum_total_trace_error": max(trace_errors),
            "independent_choi_checks": 48, "minimum_choi_eigenvalue": choi_minimum,
            "maximum_channel_trace_error": choi_trace_error,
            "transition_probability_range_in_8192_probes": [minimum_transition, maximum_transition]}


def protocol_audit(labels, protocol):
    base = {"ids": labels["ids"].tolist(), "p1": labels["p1"].tolist()}
    passed_checks = []
    with tempfile.TemporaryDirectory(prefix="audit_cases_", dir=ROOT / "adversary") as temporary:
        path = Path(temporary) / "candidate.json"
        valid_payload = json.dumps(base)
        payloads = {
            "missing_key": json.dumps({"ids": base["ids"]}),
            "extra_key": json.dumps(dict(base, metadata=3)),
            "missing_id": json.dumps({"ids": base["ids"][:-1], "p1": base["p1"][:-1]}),
            "extra_id": json.dumps({"ids": base["ids"] + [999999], "p1": base["p1"] + [0.5]}),
            "duplicate_id": json.dumps({"ids": [base["ids"][1]] + base["ids"][1:], "p1": base["p1"]}),
            "unknown_id": json.dumps({"ids": [-100] + base["ids"][1:], "p1": base["p1"]}),
            "boolean_id": json.dumps({"ids": [True] + base["ids"][1:], "p1": base["p1"]}),
            "string_id": json.dumps({"ids": ["0"] + base["ids"][1:], "p1": base["p1"]}),
            "probability_boolean": json.dumps({"ids": base["ids"], "p1": [False] + base["p1"][1:]}),
            "probability_string": json.dumps({"ids": base["ids"], "p1": ["0.5"] + base["p1"][1:]}),
            "probability_nested": json.dumps({"ids": base["ids"], "p1": [[0.5]] + base["p1"][1:]}),
            "probability_negative": json.dumps({"ids": base["ids"], "p1": [-0.1] + base["p1"][1:]}),
            "probability_over_one": json.dumps({"ids": base["ids"], "p1": [1.01] + base["p1"][1:]}),
            "probability_nan": json.dumps({"ids": base["ids"], "p1": [float("nan")] + base["p1"][1:]}),
            "probability_infinite": json.dumps({"ids": base["ids"], "p1": [float("inf")] + base["p1"][1:]}),
            "duplicate_key": valid_payload[:-1] + ', "ids": []}',
            "malformed": '{"ids":',
            "oversize": " " * (protocol["max_submission_bytes"] + 1),
            "executable_not_run": 'raise RuntimeError("This code must not run")',
        }
        for name, payload in payloads.items():
            path.write_text(payload)
            result = evaluate(path)
            assert not result["valid"] and not result["passed"], (name, result)
            assert all(key in result for key in ["core_score", "worst_family_score", "runtime_seconds", "reason"])
            passed_checks.append(name)
        path.write_text(json.dumps({"ids": base["ids"][::-1], "p1": base["p1"][::-1]}))
        decoded = load_submission(path, labels["ids"], protocol["max_submission_bytes"])
        assert np.array_equal(decoded, labels["p1"])
        result = evaluate(path)
        assert result["valid"] and result["passed"] and result["core_score"] == 1.
        link = Path(temporary) / "linked_predictions.json"
        link.symlink_to(path)
        linked_result = evaluate(link)
        assert not linked_result["valid"] and not linked_result["passed"]
        passed_checks.append("symlink_to_otherwise_valid_predictions")
        dangling = Path(temporary) / "dangling_predictions.json"
        dangling.symlink_to(Path(temporary) / "missing.json")
        dangling_result = evaluate(dangling)
        assert not dangling_result["valid"] and not dangling_result["passed"]
        passed_checks.append("dangling_symlink")
        directory_result = evaluate(Path(temporary))
        assert not directory_result["valid"] and not directory_result["passed"]
        passed_checks.append("directory_not_regular_file")
    synthetic = dict(labels, p1=np.full(len(labels["ids"]), 0.5))
    aggregate_failure = score_predictions(np.full(len(labels["ids"]), 0.521), synthetic, protocol, bootstrap=False)
    assert not aggregate_failure["passed"] and aggregate_failure["worst_family_score"] > 0.5
    predictions = synthetic["p1"].copy()
    family = next(iter(protocol["family_rmse_max"]))
    predictions[labels["family"] == family] += 0.026
    family_failure = score_predictions(predictions, synthetic, protocol, bootstrap=False)
    assert not family_failure["passed"] and family_failure["core_score"] > 0.5
    predictions = synthetic["p1"].copy()
    predictions[(labels["family"] == family) & (labels["device"] == 0)] += 0.041
    cell_failure = score_predictions(predictions, synthetic, protocol, bootstrap=False)
    assert not cell_failure["passed"] and cell_failure["core_score"] > 0.5 and cell_failure["worst_family_score"] > 0.5
    return {"invalid_submissions_rejected": passed_checks, "reordered_ids_accepted": True,
            "perfect_score_internal_consistency_only": True,
            "aggregate_family_cell_guards_independently_tested": True,
            "submission_code_is_never_imported_or_executed": True}


def data_audit(splits):
    seen = set()
    shot_statistics = {}
    for name, data in splits.items():
        assert all(array.dtype.kind != "O" for array in data.values())
        assert "p1" not in data and "parameters" not in data
        for row in range(len(data["ids"])):
            length = int(data["length"][row])
            word = data["gates"][row, :length]
            assert np.all((word >= 0) & (word <= 4))
            assert np.all(data["gates"][row, length:] == -1)
            key = (int(data["device"][row]), float(data["time"][row]), int(data["preparation"][row]),
                   int(data["measurement"][row]), tuple(word))
            assert key not in seen
            seen.add(key)
        if name != "queries":
            truth = load(ROOT / "evaluator" / "hidden" / (name + "_truth.npz"))["p1"]
            assert np.all(data["count_one"] >= 0) and np.all(data["count_one"] <= data["shots"])
            standardized = (data["count_one"] - data["shots"] * truth) / np.sqrt(data["shots"] * truth * (1. - truth))
            mean = float(np.mean(standardized))
            variance = float(np.var(standardized))
            assert abs(mean) < 5. / np.sqrt(len(truth)) and abs(variance - 1.) < 0.12
            shot_statistics[name] = {"standardized_count_mean": mean, "standardized_count_variance": variance}
    manifest = json.loads((ROOT / "participant" / "input" / "manifest.json").read_text())
    assert all(hashlib.sha256((ROOT / "participant" / "input" / name).read_bytes()).hexdigest() == digest
               for name, digest in manifest.items())
    return {"unique_records_across_all_splits": len(seen), "split_overlap": 0,
            "public_archives_have_no_truth_or_object_arrays": True, "public_manifest_verified": True,
            "finite_shot_sampling_checks": shot_statistics}


def main():
    started = time.perf_counter()
    parameters = load(ROOT / "evaluator" / "hidden" / "parameters.npz")["parameters"]
    splits = {name: load(ROOT / "participant" / "input" / (name + ".npz"))
              for name in ["train", "development", "queries"]}
    labels = load(ROOT / "evaluator" / "hidden" / "truth.npz")
    protocol = json.loads((ROOT / "evaluator" / "hidden" / "protocol.json").read_text())
    result = {"physics": physics_audit(parameters, splits), "data": data_audit(splits),
              "evaluator": protocol_audit(labels, protocol), "all_checks_passed": True}
    result["runtime_seconds"] = time.perf_counter() - started
    (ROOT / "adversary" / "audit_results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
