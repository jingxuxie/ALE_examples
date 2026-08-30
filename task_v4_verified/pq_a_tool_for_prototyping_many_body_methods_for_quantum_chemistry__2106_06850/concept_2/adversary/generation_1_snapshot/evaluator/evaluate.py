"""Artifact-only, bounded-runtime evaluator with an independent trusted oracle."""

import argparse
import json
import math
import os
import stat
import subprocess
import sys
import time
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parent
LIMITS = json.loads((DIRECTORY / "hidden" / "constraints.json").read_text())


def failure(reason, runtime=0.0, diagnostics=None):
    return {"schema_version": 1, "generation": "population-witness-v1", "passed": False,
            "score": 0.0, "core_score": 0.0, "threshold": LIMITS["population_violation_min"],
            "worst": None, "runtime_seconds": float(runtime), "reason": reason,
            "diagnostics": {} if diagnostics is None else diagnostics}


def reject_constant(value):
    raise ValueError("nonfinite JSON token: " + value)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def finite_tree(value):
    if isinstance(value, dict):
        return all(finite_tree(item) for item in value.values())
    if isinstance(value, list):
        return all(finite_tree(item) for item in value)
    if type(value) is float:
        return math.isfinite(value)
    return True


def read_artifact(path, submission_directory=None):
    absolute = Path(os.path.abspath(path))
    directory = Path(os.path.abspath(submission_directory)) if submission_directory is not None else absolute.parent
    if os.path.commonpath([absolute, directory]) != str(directory) or absolute == directory:
        raise ValueError("artifact is outside submission directory")
    directory_descriptor = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in absolute.parts[1:-1]:
            next_descriptor = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                      dir_fd=directory_descriptor)
            os.close(directory_descriptor)
            directory_descriptor = next_descriptor
        descriptor = os.open(absolute.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=directory_descriptor)
        with os.fdopen(descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("artifact is not a regular file")
            raw = stream.read(LIMITS["artifact_bytes_max"] + 1)
    finally:
        os.close(directory_descriptor)
    if len(raw) > LIMITS["artifact_bytes_max"]:
        raise ValueError("artifact exceeds 65536 bytes")
    data = json.loads(raw.decode("utf-8"), parse_constant=reject_constant, object_pairs_hook=unique_object)
    if type(data) is not dict or set(data) != {"schema_version", "orbital_energies", "pair_matrix", "amplitudes"}:
        raise ValueError("artifact must have exactly the four documented keys")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError("schema_version must be integer 1")

    def vector(value, count, name):
        if type(value) is not list or len(value) != count:
            raise ValueError(name + " has wrong dimension")
        for number in value:
            if type(number) not in (int, float) or not math.isfinite(number):
                raise ValueError(name + " must contain finite JSON numbers, not booleans or strings")
        return value

    vector(data["orbital_energies"], 6, "orbital_energies")
    vector(data["amplitudes"], 18, "amplitudes")
    if type(data["pair_matrix"]) is not list or len(data["pair_matrix"]) != 15:
        raise ValueError("pair_matrix must have 15 rows")
    for row in data["pair_matrix"]:
        vector(row, 15, "pair_matrix row")
    return data


def evaluate_artifact(path, submission_directory=None):
    started = time.monotonic()
    try:
        data = read_artifact(Path(path), submission_directory)
    except (OSError, ValueError, TypeError, OverflowError, RecursionError) as error:
        return failure("invalid_artifact: " + str(error)[:240], time.monotonic() - started)
    try:
        import numpy as np

        sys.path.insert(0, str(DIRECTORY / "hidden"))
        from independent import IndependentSystem

        np.seterr(over="raise", invalid="raise", divide="raise")
        energies = np.asarray(data["orbital_energies"], dtype=float)
        interaction = np.asarray(data["pair_matrix"], dtype=float)
        amplitudes = np.asarray(data["amplitudes"], dtype=float)
        if max(abs(energies - LIMITS["orbital_energies"])) > 1e-12:
            raise ValueError("canonical orbital energies are fixed")
        if np.max(np.abs(interaction - interaction.T)) > LIMITS["symmetry_tolerance"]:
            raise ValueError("pair_matrix is not symmetric")
        if np.max(np.abs(interaction)) > LIMITS["pair_entry_max"]:
            raise ValueError("pair-matrix entry bound exceeded")
        if np.linalg.norm(interaction) > LIMITS["pair_frobenius_max"]:
            raise ValueError("pair-matrix Frobenius bound exceeded")
        if np.linalg.norm(amplitudes) > LIMITS["amplitude_norm_max"]:
            raise ValueError("amplitude norm bound exceeded")
        interaction = (interaction + interaction.T) / 2
        energies = np.array(LIMITS["orbital_energies"])
        oracle = IndependentSystem()
        diagnostics = oracle.diagnose(energies, interaction, amplitudes)
        if not finite_tree(diagnostics):
            return failure("nonfinite_oracle_diagnostics", time.monotonic() - started)
        margins = []

        def bound(name, value, threshold, lower=False, scale=None):
            if not math.isfinite(float(value)):
                raise ValueError("nonfinite constraint: " + name)
            distance = value - threshold if lower else threshold - value
            normalization = max(abs(threshold), 1e-12) if scale is None else scale
            margins.append({"constraint": name, "value": float(value), "bound": float(threshold),
                            "direction": "lower" if lower else "upper",
                            "margin": float(distance / normalization)})

        for metric, limit in [("cc_residual", "cc_residual_max"), ("lambda_residual", "lambda_residual_max"),
                              ("energy_error", "energy_error_max"), ("jacobian_condition", "jacobian_condition_max"),
                              ("lambda_norm", "lambda_norm_max"), ("amplitude_norm", "amplitude_norm_max")]:
            bound(metric, diagnostics[metric], LIMITS[limit])
        for metric, limit in [("ground_overlap", "ground_overlap_min"), ("reference_weight", "reference_weight_min"),
                              ("fci_gap", "fci_gap_min"), ("hf_real_min", "hf_curvature_min"),
                              ("hf_imaginary_min", "hf_curvature_min")]:
            bound(metric, diagnostics[metric], LIMITS[limit], lower=True)
        bound("eom_real_min", min(diagnostics["eom_real"]), LIMITS["eom_real_min"], lower=True)
        bound("pair_entry_max", np.max(np.abs(interaction)), LIMITS["pair_entry_max"])
        bound("pair_frobenius_max", np.linalg.norm(interaction), LIMITS["pair_frobenius_max"])
        for metric in ("hf_gradient", "fock_error", "hermiticity_error"):
            bound(metric, diagnostics[metric], 2e-10)
        bound("biorthogonal_normalization", abs(diagnostics["biorthogonal_norm"] - 1), 2e-8)
        bound("rdm_trace", abs(diagnostics["rdm_trace"] - 3), 2e-8)
        for metric in ("exact_rdm_trace_error", "exact_rdm_hermiticity_error", "exact_rdm_positivity_violation",
                       "right_state_rdm_positivity_violation"):
            bound(metric, diagnostics[metric], 2e-9)
        failed = [row["constraint"] for row in margins if row["margin"] < 0]
        if not failed:
            try:
                endpoint, history = oracle.continuation(energies, interaction, LIMITS["continuation_steps"])
            except (ValueError, np.linalg.LinAlgError) as error:
                diagnostics["continuation_error"] = str(error)[:160]
                return failure("continuation_solver_failed", time.monotonic() - started, diagnostics)
            if not finite_tree(history):
                return failure("nonfinite_continuation", time.monotonic() - started, diagnostics)
            path_summary = {"steps": LIMITS["continuation_steps"],
                            "min_overlap": min(row["overlap"] for row in history),
                            "min_gap": min(row["gap"] for row in history),
                            "min_jacobian_singular": min(row["jacobian_singular_min"] for row in history),
                            "max_amplitude_step": max(row["amplitude_step"] for row in history),
                            "max_cc_residual": max(row["residual"] for row in history),
                            "endpoint_error": float(np.max(np.abs(endpoint - amplitudes)))}
            diagnostics["continuation"] = path_summary
            bound("path_overlap", path_summary["min_overlap"], LIMITS["path_overlap_min"], lower=True)
            bound("path_gap", path_summary["min_gap"], LIMITS["path_gap_min"], lower=True)
            bound("path_jacobian_singular", path_summary["min_jacobian_singular"], LIMITS["path_jacobian_singular_min"], lower=True)
            bound("path_amplitude_step", path_summary["max_amplitude_step"], LIMITS["path_amplitude_step_max"])
            bound("path_cc_residual", path_summary["max_cc_residual"], LIMITS["cc_residual_max"])
            bound("path_endpoint", path_summary["endpoint_error"], LIMITS["path_endpoint_tolerance"])
            failed = [row["constraint"] for row in margins if row["margin"] < 0]
        else:
            diagnostics["continuation"] = {"not_run": "endpoint constraints failed"}
        core_score = 0.0 if failed else diagnostics["occupation_violation"]
        passed = not failed and core_score >= LIMITS["population_violation_min"]
        reason = "witness_verified" if passed else ("constraints_failed: " + ", ".join(failed) if failed else "population_violation_below_threshold")
        diagnostics["constraints"] = margins
        diagnostics["admissible"] = not failed
        return {"schema_version": 1, "generation": "population-witness-v1", "passed": bool(passed),
                "score": min(1.0, core_score / LIMITS["population_violation_min"]),
                "core_score": float(core_score), "threshold": LIMITS["population_violation_min"],
                "worst": min(margins, key=lambda row: row["margin"]),
                "runtime_seconds": time.monotonic() - started, "reason": reason, "diagnostics": diagnostics}
    except Exception as error:
        return failure("numerical_or_domain_failure: " + type(error).__name__ + ": " + str(error)[:200],
                       time.monotonic() - started)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", nargs="?")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--submission-dir", type=Path)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    arguments = parser.parse_args()
    started = time.monotonic()
    if arguments.artifact is None:
        result = failure("missing_artifact_argument")
    elif arguments.worker:
        result = evaluate_artifact(arguments.artifact, arguments.submission_dir)
    else:
        environment = os.environ.copy()
        for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
            environment[variable] = "1"
        environment.pop("PYTHONPATH", None)
        environment.pop("PYTHONHOME", None)
        try:
            artifact_path = os.path.abspath(arguments.artifact)
            submission_directory = os.path.abspath(arguments.submission_dir) if arguments.submission_dir is not None else str(Path(artifact_path).parent)
            process = subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()),
                                      artifact_path, "--submission-dir", submission_directory, "--worker"],
                                     cwd=DIRECTORY, env=environment, capture_output=True, text=True,
                                     timeout=LIMITS["evaluator_timeout_seconds"], check=False)
            if process.returncode != 0:
                result = failure("trusted_worker_failed", diagnostics={"returncode": process.returncode,
                                                                       "stderr": process.stderr[-500:]})
            else:
                result = json.loads(process.stdout, parse_constant=reject_constant)
                if not isinstance(result, dict) or not finite_tree(result):
                    result = failure("invalid_trusted_worker_report")
        except subprocess.TimeoutExpired:
            result = failure("evaluator_timeout")
        except Exception as error:
            result = failure("evaluator_infrastructure_failure: " + str(error)[:160])
        result["runtime_seconds"] = time.monotonic() - started
    text = json.dumps(result, indent=2, allow_nan=False)
    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
