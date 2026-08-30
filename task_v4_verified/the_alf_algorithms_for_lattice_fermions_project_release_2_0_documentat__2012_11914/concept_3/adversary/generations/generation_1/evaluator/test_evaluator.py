"""Private static scorer controls and optional sandboxed process controls."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import zipfile

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True

import numpy as np
from scipy.linalg import solve_triangular

from evaluate import ROOT, decision, evaluate, load, verify_manifest
from runtime import ExecutionError, execute_submission, read_prediction
from physics import kernel, observables, wasserstein
from scoring import score_prediction, validate_prediction


def rejected(callable_object):
    try:
        callable_object()
    except (ValueError, TypeError, zipfile.BadZipFile):
        return True
    return False


def fingerprints(directory):
    return {
        str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


def static_controls():
    before = fingerprints(ROOT / "participant")
    verify_manifest()
    inputs = load(ROOT / "evaluator/hidden/heldout_input.npz")
    labels = load(ROOT / "evaluator/hidden/heldout_labels.npz")
    low = observables(labels["spectral_mass"], inputs["omega_edges"])["low_mass"]
    oracle = {
        "sample_id": labels["sample_id"].copy(),
        "spectral_mass": labels["spectral_mass"].copy(),
        "low_mass_quantiles": np.repeat(low[:, None], 3, axis=1),
    }
    oracle_path = ROOT / "evaluator/hidden/oracle_control_predictions.npz"
    np.savez_compressed(oracle_path, **oracle)
    oracle_score = score_prediction(read_prediction(oracle_path), inputs, labels)
    assert oracle_score["core_score"] > 100.0 - 1e-10
    assert oracle_score["worst_family_score"] > 100.0 - 1e-10
    assert decision(oracle_score, 0.0)[0]
    malformed = {}

    def check(name, mutate):
        prediction = {key: value.copy() for key, value in oracle.items()}
        mutate(prediction)
        malformed[name] = rejected(lambda: validate_prediction(prediction, inputs))
        assert malformed[name], name

    check("missing_key", lambda prediction: prediction.pop("low_mass_quantiles"))
    check("untrusted_runtime_field", lambda prediction: prediction.update(runtime_seconds=np.array(0.0)))
    check("nan_mass", lambda prediction: prediction["spectral_mass"].__setitem__((0, 0), np.nan))
    check("infinite_quantile", lambda prediction: prediction["low_mass_quantiles"].__setitem__((0, 2), np.inf))
    check("negative_mass", lambda prediction: prediction["spectral_mass"].__setitem__((0, 0), -0.01))
    check("normalization", lambda prediction: prediction["spectral_mass"].__setitem__(0, prediction["spectral_mass"][0] * 0.9))
    check("wrong_shape", lambda prediction: prediction.update(spectral_mass=prediction["spectral_mass"][:, :-1]))
    check("integer_mass", lambda prediction: prediction.update(spectral_mass=prediction["spectral_mass"].astype(np.int64)))
    check("complex_mass", lambda prediction: prediction.update(spectral_mass=prediction["spectral_mass"].astype(np.complex128)))
    check("object_mass", lambda prediction: prediction.update(spectral_mass=prediction["spectral_mass"].astype(object)))
    check("reordered_ids", lambda prediction: prediction.update(sample_id=prediction["sample_id"][::-1]))
    check("wrong_id_dtype", lambda prediction: prediction.update(sample_id=prediction["sample_id"].astype(np.float64)))
    check("crossed_quantiles", lambda prediction: prediction["low_mass_quantiles"].__setitem__(0, [0.8, 0.5, 0.1]))
    check("out_of_range_quantile", lambda prediction: prediction["low_mass_quantiles"].__setitem__((0, 2), 1.1))
    with tempfile.TemporaryDirectory(dir=ROOT / "evaluator/hidden") as temporary:
        directory = Path(temporary)
        bad_archive = directory / "extra.npz"
        np.savez_compressed(bad_archive, **oracle, runtime_seconds=np.array(0.0))
        malformed["archive_extra_field"] = rejected(lambda: read_prediction(bad_archive))
        assert malformed["archive_extra_field"]
        symlink = directory / "symlink.npz"
        symlink.symlink_to(oracle_path)
        malformed["archive_symlink"] = rejected(lambda: read_prediction(symlink))
        assert malformed["archive_symlink"]
        object_archive = directory / "object.npz"
        np.savez_compressed(object_archive, sample_id=oracle["sample_id"], spectral_mass=oracle["spectral_mass"].astype(object), low_mass_quantiles=oracle["low_mass_quantiles"])
        malformed["archive_object_dtype"] = rejected(lambda: read_prediction(object_archive))
        assert malformed["archive_object_dtype"]
        not_zip = directory / "not_zip.npz"
        not_zip.write_text("not an npz")
        malformed["invalid_archive"] = rejected(lambda: read_prediction(not_zip))
        assert malformed["invalid_archive"]
    identifiers = []
    mass_hashes = set()
    for name in ("train", "validation", "heldout"):
        location = ROOT / ("evaluator/hidden" if name == "heldout" else "participant/input")
        split_inputs = load(location / f"{name}_input.npz")
        split_labels = load(location / f"{name}_labels.npz")
        assert np.array_equal(split_inputs["sample_id"], split_labels["sample_id"])
        identifiers.extend(int(identifier) for identifier in split_inputs["sample_id"])
        for mass in split_labels["spectral_mass"]:
            digest = hashlib.sha256(mass.tobytes()).hexdigest()
            assert digest not in mass_hashes
            mass_hashes.add(digest)
        np.linalg.cholesky(split_inputs["covariance"])
        assert np.all(np.diff(split_inputs["tau"], axis=1) > 0.0)
        assert np.allclose(split_labels["spectral_mass"].sum(axis=1), 1.0)
    assert len(identifiers) == len(set(identifiers))
    mahalanobis = []
    for row, beta in enumerate(inputs["beta"]):
        response = kernel(beta, inputs["tau"][row], inputs["omega_edges"])
        assert np.allclose(response[0] + response[-1], 1.0, atol=2e-14)
        residual = inputs["correlation"][row] - response @ labels["spectral_mass"][row]
        whitened = solve_triangular(np.linalg.cholesky(inputs["covariance"][row]), residual, lower=True)
        mahalanobis.append(float(whitened @ whitened))
    assert 30.0 < np.mean(mahalanobis) < 90.0
    with np.errstate(over="raise", invalid="raise"):
        stable_response = kernel(1000.0, np.array([0.0, 500.0, 1000.0]), inputs["omega_edges"])
    assert np.all(np.isfinite(stable_response))
    left = np.zeros((1, 256))
    right = np.zeros((1, 256))
    left[0, 0] = 1.0
    right[0, -1] = 1.0
    assert np.allclose(wasserstein(left, right, inputs["omega_edges"]), 15.9375)
    uniform = {
        "sample_id": inputs["sample_id"],
        "spectral_mass": np.full_like(labels["spectral_mass"], 1.0 / 256),
        "low_mass_quantiles": np.tile([0.0, 0.0625, 1.0], (len(low), 1)),
    }
    uniform_score = score_prediction(uniform, inputs, labels)
    assert not decision(uniform_score, 0.0)[0]
    assert before == fingerprints(ROOT / "participant")
    report = {
        "all_passed": True,
        "participant_unchanged": True,
        "oracle": {
            "kind": "static evaluator positive control, NOT a demonstrated prediction solution",
            "submitted_process_executed": False,
            "artifact": str(oracle_path.relative_to(ROOT)),
            "core_score": oracle_score["core_score"],
            "worst_family_score": oracle_score["worst_family_score"],
            "passes_scientific_thresholds_only": True,
            "achievability_inference": "none; oracle is constructed from private labels in the trusted test process",
        },
        "malformed_rejections": malformed,
        "uniform_negative_control": uniform_score,
        "dataset_checks": {
            "unique_ids": len(identifiers),
            "unique_spectra": len(mass_hashes),
            "all_covariances_spd": True,
            "heldout_mean_mahalanobis_squared": float(np.mean(mahalanobis)),
            "expected_noise_degrees_of_freedom": 56,
            "stable_extreme_beta_kernel": True,
            "wasserstein_disjoint_bins_exact": True,
        },
        "participant_fingerprints": before,
    }
    destination = ROOT / "evaluator/hidden/static_validation_report.json"
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key not in ("participant_fingerprints", "uniform_negative_control")}, indent=2))


def process_controls():
    before = fingerprints(ROOT / "participant")
    leak_denial = evaluate(ROOT / "adversary/isolation_probe")
    assert leak_denial["valid"], leak_denial
    assert not leak_denial["passed"]
    malformed = evaluate(ROOT / "adversary/malformed_output")
    assert not malformed["valid"] and not malformed["passed"], malformed
    assert "must contain exactly" in malformed["reason"], malformed
    nonfinite = evaluate(ROOT / "adversary/nonfinite_output")
    assert not nonfinite["valid"] and not nonfinite["passed"], nonfinite
    assert "must be finite" in nonfinite["reason"], nonfinite
    timeout = None
    try:
        execute_submission(
            ROOT / "adversary/timeout_probe",
            ROOT / "evaluator/hidden/heldout_input.npz",
            ROOT / "participant/input",
            wall_seconds=0.5,
        )
    except ExecutionError as error:
        timeout = {"reason": str(error), "runtime_seconds": error.runtime_seconds}
    assert timeout is not None and "wall-time limit" in timeout["reason"], timeout
    assert before == fingerprints(ROOT / "participant")
    report = {
        "all_passed": True,
        "participant_unchanged": True,
        "leak_denial": leak_denial,
        "leak_denial_assertions": "hidden labels/generator/calibration/status, absolute and proc-root paths denied; no host PID namespace; public training labels readable; submission/public mounts read-only; host home absent; network namespace isolated; one CPU and per-process RLIMIT_AS enforced",
        "malformed_extra_runtime_field": malformed,
        "malformed_nan_array": nonfinite,
        "timeout_control": timeout,
        "oracle_executed": False,
    }
    destination = ROOT / "evaluator/hidden/process_validation_report.json"
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--process-controls", action="store_true")
    arguments = parser.parse_args()
    if arguments.process_controls:
        process_controls()
    else:
        static_controls()
