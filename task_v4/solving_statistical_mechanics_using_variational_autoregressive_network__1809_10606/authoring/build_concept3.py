"""Private generation, numerical validation, baseline calibration, and freeze."""

import argparse
import datetime
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import secrets
import tempfile
import time
import zipfile

import numpy as np


ROOT = Path(__file__).resolve().parents[1] / "concept_3"


def module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(result)
    return result


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def enumeration(model, beta, delta=None, evidence=None):
    count = model.columns * model.height
    integers = np.arange(1 << count, dtype=np.int64)
    spins = 2 * ((integers[:, None] >> np.arange(count)) & 1) - 1
    array = spins.reshape(-1, model.columns, model.height)
    energy = np.sum(array[:, :, :-1] * array[:, :, 1:] * model.vertical, axis=(1, 2))
    energy += np.sum(array[:, :-1, :] * array[:, 1:, :] * model.horizontal, axis=(1, 2))
    applied = model.fields if delta is None else model.fields + delta
    energy += np.sum(array * applied, axis=(1, 2))
    logits = beta * energy
    if evidence is not None:
        logits[~np.all((evidence == 0) | (array == evidence), axis=(1, 2))] = -np.inf
    shift = logits.max()
    weights = np.exp(logits - shift)
    log_partition = float(shift + np.log(weights.sum()))
    probabilities = weights / weights.sum()
    marginals = []
    for column in range(model.columns):
        codes = (integers >> (column * model.height)) & ((1 << model.height) - 1)
        marginals.append(np.bincount(codes, weights=probabilities, minlength=1 << model.height))
    return log_partition, np.asarray(marginals), spins, probabilities


def dense_reference(model, beta, delta):
    states = model.states.astype(float)
    logits = beta * (model.vertical @ (states[:, :-1] * states[:, 1:]).T +
                      (model.fields + delta) @ states.T)
    shifts = logits.max(axis=1)
    unary = np.exp(logits - shifts[:, None])
    matrices, matrix_shifts = [], []
    for column in range(model.columns - 1):
        values = beta * (states * model.horizontal[column]) @ states.T
        matrix_shifts.append(float(values.max()))
        matrices.append(np.exp(values - values.max()))
    forward = [unary[0] / unary[0].sum()]
    log_partition = shifts[0] + np.log(unary[0].sum())
    for column, matrix in enumerate(matrices):
        weights = (forward[-1] @ matrix) * unary[column + 1]
        log_partition += np.log(weights.sum()) + shifts[column + 1] + matrix_shifts[column]
        forward.append(weights / weights.sum())
    backward = [None] * model.columns
    backward[-1] = np.ones(len(states))
    for column in range(model.columns - 2, -1, -1):
        weights = matrices[column] @ (unary[column + 1] * backward[column + 1])
        backward[column] = weights / weights.sum()
    marginals = np.asarray(forward) * np.asarray(backward)
    marginals /= marginals.sum(axis=1, keepdims=True)
    return float(log_partition), marginals


def transfer_checks(transfer, rng):
    residuals = {"enumeration_log_partition": 0.0, "enumeration_marginal": 0.0,
                 "clamped_log_partition": 0.0, "spin_flip": 0.0, "edge_derivative": 0.0}
    trials = 0
    for height, columns in ((1, 4), (2, 3), (3, 3), (4, 3)):
        vertical = rng.uniform(-0.85, 0.85, (columns, height - 1))
        horizontal = rng.uniform(-0.85, 0.85, (columns - 1, height))
        fields = rng.uniform(-0.2, 0.2, (columns, height))
        model = transfer.StripIsing(vertical, horizontal, fields)
        delta = rng.uniform(-0.2, 0.2, fields.shape)
        for beta in (0.65, 1.0, 1.3):
            truth_log, truth_marginal, spins, probabilities = enumeration(model, beta, delta)
            actual_log = model.log_partition(beta, delta)
            actual_marginal = model.column_marginals(beta, delta)
            residuals["enumeration_log_partition"] = max(residuals["enumeration_log_partition"], abs(actual_log - truth_log))
            residuals["enumeration_marginal"] = max(residuals["enumeration_marginal"], float(np.max(abs(actual_marginal - truth_marginal))))
            flipped = transfer.StripIsing(vertical, horizontal, -fields)
            flipped_marginal = flipped.column_marginals(beta, -delta)[:, ::-1]
            residuals["spin_flip"] = max(residuals["spin_flip"], float(np.max(abs(actual_marginal - flipped_marginal))))
            evidence = np.zeros_like(fields, dtype=np.int8)
            evidence.flat[::3] = spins[3, ::3]
            expected_clamp = enumeration(model, beta, delta, evidence)[0]
            residuals["clamped_log_partition"] = max(residuals["clamped_log_partition"], abs(expected_clamp - model.log_partition(beta, delta, evidence)))
            increment = 1e-5
            positive, negative = horizontal.copy(), horizontal.copy()
            positive[0, 0] += increment
            negative[0, 0] -= increment
            derivative = (transfer.StripIsing(vertical, positive, fields).log_partition(beta, delta) -
                          transfer.StripIsing(vertical, negative, fields).log_partition(beta, delta)) / (2 * increment)
            expected_derivative = beta * np.sum(probabilities * spins[:, 0] * spins[:, height])
            residuals["edge_derivative"] = max(residuals["edge_derivative"], abs(derivative - expected_derivative))
            trials += 1
    if max(residuals.values()) > 1e-8:
        raise AssertionError(residuals)
    zero = transfer.StripIsing(np.zeros((3, 2)), np.zeros((2, 3)), np.zeros((3, 3)))
    assert abs(zero.log_partition(1.3) - 9 * np.log(2)) < 1e-12
    assert np.max(abs(zero.column_marginals(1.3) - 0.125)) < 1e-12
    tiny = transfer.StripIsing(np.array([[0.35], [-0.55]]), np.array([[0.4, 0.65]]),
                               np.array([[0.08, -0.12], [0.14, 0.04]]))
    _, _, _, probabilities = enumeration(tiny, 1.15)
    samples = tiny.sample(1.15, 100000, rng)
    codes = ((samples + 1) // 2) @ (1 << np.arange(4))
    frequencies = np.bincount(codes, minlength=16) / len(samples)
    sampling_error = float(np.max(abs(frequencies - probabilities)))
    assert sampling_error < 0.008
    residuals.update({"enumeration_cases": trials, "zero_coupling_pass": True,
                      "sampling_max_absolute_error_100000": sampling_error})
    return residuals


def artifact_checks(evaluator, truth, identifiers, private):
    cases = {}
    with tempfile.TemporaryDirectory(dir=ROOT / "adversary", prefix="validation_") as directory:
        root = Path(directory)
        def write(name, probabilities=truth, ids=identifiers, **extra):
            path = root / name
            np.savez(path, probabilities=np.asarray(probabilities), query_ids=np.asarray(ids), **extra)
            return path
        valid = write("valid.npz")
        oracle_result = evaluator.evaluate(valid, private)
        cases["oracle_control_pass"] = oracle_result["passed"]
        score_fields = ("core_score", "worst_family_score", "runtime_resource_score")
        cases["valid_report_score_fields"] = all(name in oracle_result and
                                                  0 <= oracle_result[name] <= 1
                                                  for name in score_fields)
        malformed = {}
        for name, replacement in (("nan", np.nan), ("inf", np.inf), ("negative", -0.1), ("zero", 0.0)):
            changed = truth.copy()
            changed[0, 0] = replacement
            malformed[name] = write(name + ".npz", changed)
        malformed["normalization"] = write("normalization.npz", truth * 1.001)
        malformed["shape"] = write("shape.npz", truth[:, :-1])
        malformed["float32"] = write("float32.npz", truth.astype(np.float32))
        malformed["object_pickle"] = write("object.npz", truth.astype(object))
        malformed["wrong_ids"] = write("ids.npz", ids=identifiers[::-1])
        malformed["wrong_unicode_width"] = write("width.npz", ids=identifiers.astype("<U25"))
        malformed["extra_member"] = write("extra.npz", extra=np.ones(1))
        malformed["missing"] = root / "missing.npz"
        malformed["symlink"] = root / "symlink.npz"
        malformed["symlink"].symlink_to(valid.name)
        malformed["oversize"] = root / "oversize.npz"
        malformed["oversize"].write_bytes(b"x" * 65537)
        malformed["truncated"] = root / "truncated.npz"
        malformed["truncated"].write_bytes(valid.read_bytes()[:100])
        with zipfile.ZipFile(valid) as original:
            members = {name: original.read(name) for name in original.namelist()}
        malformed["duplicate_member"] = root / "duplicate.npz"
        with zipfile.ZipFile(malformed["duplicate_member"], "w") as archive:
            for name, payload in members.items():
                archive.writestr(name, payload)
            archive.writestr("query_ids.npy", members["query_ids.npy"])
        malformed["zip_bomb"] = root / "bomb.npz"
        with zipfile.ZipFile(malformed["zip_bomb"], "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("probabilities.npy", b"0" * 1000000)
            archive.writestr("query_ids.npy", members["query_ids.npy"])
        for name, path in malformed.items():
            result = evaluator.evaluate(path, private)
            cases[name + "_rejected"] = (result["valid"] is False and result["passed"] is False
                                           and all(result.get(field) == 0.0 for field in score_fields))
        compressed = root / "compressed.npz"
        np.savez_compressed(compressed, probabilities=truth, query_ids=identifiers)
        cases["compressed_valid_pass"] = evaluator.evaluate(compressed, private)["passed"]
        assert all(cases.values()), cases
    return cases


def build():
    started = time.monotonic()
    frozen = ROOT / "adversary" / "FREEZE.json"
    if frozen.exists():
        raise SystemExit("Already frozen; refuse regeneration. Validate the existing package instead.")
    public = ROOT / "participant" / "input"
    private = ROOT / "evaluator" / "hidden"
    controls = ROOT / "adversary"
    for directory in (public, private, controls):
        directory.mkdir(parents=True, exist_ok=True)
    private.chmod(0o700)
    transfer = module("concept3_transfer", ROOT / "participant" / "transfer.py")
    baseline = module("concept3_baseline", ROOT / "participant" / "baseline.py")
    evaluator = module("concept3_evaluator", ROOT / "evaluator" / "evaluate.py")
    generation_path = private / "generation.json"
    if generation_path.exists():
        seed = int(json.loads(generation_path.read_text())["seed"])
    else:
        seed = secrets.randbits(128)
        save_json(generation_path, {"seed": str(seed), "sampler": "numpy PCG64, backward exact strip sampling",
                                   "targets_prefixed": evaluator.TARGETS, "design": "96-spin latent response v1"})
    sequence = np.random.SeedSequence(seed)
    model_sequence, sampling_sequence, validation_sequence = sequence.spawn(3)
    rng = np.random.default_rng(model_sequence)
    sample_rng = np.random.default_rng(sampling_sequence)
    validation_rng = np.random.default_rng(validation_sequence)
    validation = {"transfer": transfer_checks(transfer, validation_rng)}
    height, columns = 8, 12
    readout_columns = [0, 1, 3, 4, 6, 7, 9, 10]
    hidden = []
    for column in range(columns):
        offset = (2 * column + 1) % height
        rows = [(offset + index) % height for index in range(2 if column in readout_columns else 4)]
        hidden.extend(column * height + row for row in rows)
    hidden = sorted(hidden)
    visible = sorted(set(range(height * columns)) - set(hidden))
    edges = transfer.lattice_edges(height, columns)
    signs = np.where(rng.random(len(edges)) < 0.10, -1, 1).astype(np.int8)
    couplings = signs * rng.uniform(0.30, 0.95, len(edges))
    fields = rng.uniform(-0.12, 0.12, height * columns)
    spec = {"version": 1, "height": height, "columns": columns, "n_spins": 96,
            "edges": edges.tolist(), "edge_signs": signs.tolist(), "visible_indices": visible,
            "hidden_indices": hidden, "parameter_prior": {
                "coupling_magnitudes": {"distribution": "independent uniform", "bounds": [0.30, 0.95]},
                "fields": {"distribution": "independent uniform", "bounds": [-0.12, 0.12]},
                "signs": "known individually; no additional sharing"}}
    save_json(public / "model.json", spec)
    model = transfer.model_from_edges(spec, couplings, fields)
    np.savez(private / "model.npz", couplings=couplings, fields=fields)
    betas = np.asarray([0.65, 1.0], dtype="<f8")
    configurations = np.stack([model.sample(float(beta), 8192, sample_rng)[:, visible] for beta in betas])
    np.savez_compressed(public / "train.npz", betas=betas, visible_spins=configurations)
    queries = []
    for family in evaluator.FAMILIES:
        for index, column in enumerate(readout_columns):
            readout = [spin for spin in visible if spin // height == column]
            assert len(readout) == 6
            beta = 0.85 if family == "interpolation" else (1.15 if index % 2 == 0 else 1.3)
            field_indices = [readout[index % 6], readout[(index + 2) % 6], readout[(index + 4) % 6]] if family == "fields" else []
            field_values = [0.16, -0.14, 0.10] if family == "fields" else []
            queries.append({"id": family + "_%02d" % index, "family": family, "beta": beta,
                            "readout": readout, "field_indices": field_indices, "field_values": field_values})
    save_json(public / "queries.json", queries)
    truth = []
    dense_error, dense_log_error = 0.0, 0.0
    for query in queries:
        delta = np.zeros((columns, height))
        delta.flat[query["field_indices"]] = query["field_values"]
        probabilities = model.joint(query["beta"], query["readout"], delta)
        truth.append(probabilities)
        dense_log, dense_marginals = dense_reference(model, query["beta"], delta)
        dense_error = max(dense_error, float(np.max(abs(dense_marginals - model.column_marginals(query["beta"], delta)))))
        dense_log_error = max(dense_log_error, abs(dense_log - model.log_partition(query["beta"], delta)))
    truth = np.asarray(truth, dtype="<f8")
    identifiers = np.asarray([query["id"] for query in queries], dtype="<U24")
    assert dense_error < 1e-11 and dense_log_error < 1e-10
    assert np.all(truth > 0) and np.max(abs(truth.sum(axis=1) - 1)) < 1e-14
    np.savez(private / "labels.npz", probabilities=truth, query_ids=identifiers)
    save_json(private / "scoring.json", {"families": [query["family"] for query in queries], "targets": evaluator.TARGETS})
    baseline_dir = controls / "baseline"
    baseline_dir.mkdir(exist_ok=True)
    predictions, baseline_ids = baseline.predict(public)
    np.savez(baseline_dir / "predictions.npz", probabilities=predictions, query_ids=baseline_ids)
    baseline_score = evaluator.evaluate(baseline_dir)
    save_json(controls / "baseline_score.json", baseline_score)
    assert baseline_score["valid"], baseline_score
    if baseline_score["passed"]:
        save_json(controls / "BUILD_BLOCKED.json", {"reason": "weak baseline passes; data not frozen; ratchet requires explicit review",
                                                   "baseline": baseline_score})
        raise SystemExit("Weak baseline passes fixed gates: refusing to freeze or signal ready.")
    validation["artifact_checks"] = artifact_checks(evaluator, truth, identifiers, private)
    validation["dense_full_instance"] = {"queries": 24, "max_marginal_error": dense_error,
                                         "max_log_partition_error": dense_log_error}
    lookup = {spin: index for index, spin in enumerate(visible)}
    readout_sample_errors = []
    for condition, beta in enumerate(betas):
        for column in readout_columns:
            readout = [spin for spin in visible if spin // height == column]
            observed = configurations[condition][:, [lookup[spin] for spin in readout]]
            codes = ((observed + 1) // 2) @ (1 << np.arange(6))
            empirical = np.bincount(codes, minlength=64) / 8192
            readout_sample_errors.append(float(np.max(abs(empirical - model.joint(float(beta), readout)))))
    validation["data"] = {"n_spins": 96, "visible": len(visible), "hidden": len(hidden),
                          "hidden_hidden_edges": sum(int(first in hidden and second in hidden) for first, second in edges),
                          "training_shape": list(configurations.shape), "minimum_true_query_probability": float(truth.min()),
                          "maximum_empirical_training_readout_error": max(readout_sample_errors),
                          "fresh_agents_launched": 0, "solvability": "unknown; no fitted-public-data solver evaluated",
                          "oracle_control_meaning": "evaluator correctness only, not evidence of inferential attainability"}
    validation["build_seconds"] = time.monotonic() - started
    save_json(controls / "validation.json", validation)
    save_json(ROOT / "status.json", {"mode": "D", "status": "ready_for_fresh_launch", "frozen": True,
                                     "targets": evaluator.TARGETS, "baseline_passed": False,
                                     "solvability": "unknown", "fresh_agents_launched": 0})
    for path in private.iterdir():
        path.chmod(0o600)
    files = {}
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path != frozen:
            files[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    save_json(frozen, {"frozen_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       "targets": evaluator.TARGETS, "files_sha256": files,
                       "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                       "launch_status": "no participant launched; freeze precedes fresh attempt",
                       "solvability": "unknown", "baseline_metrics": baseline_score["metrics"]})
    print(json.dumps({"ready": True, "baseline": baseline_score["metrics"],
                      "baseline_families": baseline_score["family_mean_kl"], "validation": validation,
                      "root": str(ROOT)}, indent=2))


def validate_existing():
    controls = ROOT / "adversary"
    freeze_path = controls / "FREEZE.json"
    previous_text = freeze_path.read_text()
    previous = json.loads(previous_text)
    evaluator = module("concept3_evaluator", ROOT / "evaluator" / "evaluate.py")
    baseline = module("concept3_baseline", ROOT / "participant" / "baseline.py")
    private = ROOT / "evaluator" / "hidden"
    assert previous["targets"] == evaluator.TARGETS
    data_hashes = {}
    for name, digest in previous["files_sha256"].items():
        if name.startswith(("participant/input/", "evaluator/private/", "evaluator/hidden/")):
            current_name = name.replace("evaluator/private/", "evaluator/hidden/", 1)
            assert hashlib.sha256((ROOT / current_name).read_bytes()).hexdigest() == digest, current_name
            data_hashes[current_name] = digest
    assert len(data_hashes) == 7
    assert private.is_dir() and not (ROOT / "evaluator" / "private").exists()
    with np.load(private / "labels.npz", allow_pickle=False) as labels:
        truth, identifiers = labels["probabilities"], labels["query_ids"]
    predictions, baseline_ids = baseline.predict(ROOT / "participant" / "input")
    with np.load(controls / "baseline" / "predictions.npz", allow_pickle=False) as saved:
        assert np.array_equal(saved["probabilities"], predictions)
        assert np.array_equal(saved["query_ids"], baseline_ids)
    baseline_score = evaluator.evaluate(controls / "baseline")
    assert baseline_score["valid"] and not baseline_score["passed"]
    assert baseline_score["metrics"] == previous["baseline_metrics"]
    save_json(controls / "baseline_score.json", baseline_score)
    if (controls / "cli_smoke").is_dir():
        save_json(controls / "cli_smoke_score.json", evaluator.evaluate(controls / "cli_smoke"))
    validation = json.loads((controls / "validation.json").read_text())
    validation["artifact_checks"] = artifact_checks(evaluator, truth, identifiers, private)
    validation["layout_reporting_revision"] = {
        "hidden_directory": "evaluator/hidden", "scientific_files_unchanged": data_hashes,
        "targets_unchanged": True, "baseline_metrics_unchanged": True,
        "valid_and_invalid_score_fields_checked": True,
        "resource_limit": "four-core affinity; 8 GiB address space per process",
        "solvability": "unknown; oracle controls are not public-data fitted solvers"}
    save_json(controls / "validation.json", validation)
    status = json.loads((ROOT / "status.json").read_text())
    status.update({"status": "ready_for_fresh_launch", "hidden_directory": "evaluator/hidden",
                   "report_schema": "physical metrics plus core/worst_family/runtime_resource scores"})
    save_json(ROOT / "status.json", status)
    history = controls / "FREEZE.layout_v1.json"
    if not history.exists():
        history.write_text(previous_text)
    files = {}
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path != freeze_path:
            files[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    save_json(freeze_path, {"frozen_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                           "targets": evaluator.TARGETS, "files_sha256": files,
                           "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                           "previous_freeze_sha256": hashlib.sha256(previous_text.encode()).hexdigest(),
                           "revision": "layout/reporting only; scientific data and targets unchanged",
                           "solvability": "unknown", "baseline_metrics": baseline_score["metrics"]})
    print(json.dumps({"ready": True, "baseline": baseline_score,
                      "scientific_files_preserved": len(data_hashes),
                      "artifact_checks_passed": len(validation["artifact_checks"]),
                      "hidden_directory": str(private), "freeze": str(freeze_path)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-existing", action="store_true")
    arguments = parser.parse_args()
    validate_existing() if arguments.validate_existing else build()
