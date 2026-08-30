import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import hashlib
import importlib.util
import io
import itertools
import json
import struct
import subprocess
import time
import zipfile

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import eigsh

import trusted_physics as physics

CONCEPT = Path(__file__).resolve().parents[2]
AUDIT = CONCEPT / "adversary" / "ratchet_2"


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def close(actual, expected, tolerance, name):
    error = float(np.max(np.abs(np.asarray(actual) - np.asarray(expected))))
    if error > tolerance:
        raise AssertionError(f"{name}: maximum absolute difference {error}")
    return error


def determinant(quartet, size=None):
    first, second, third, fourth = quartet
    rows = np.concatenate((np.arange(first + 1, second + 1), np.arange(third + 1, fourth + 1)))
    columns = np.concatenate((np.arange(first, second), np.arange(third, fourth)))
    differences = rows[:, None] - columns[None, :] - 0.5
    matrix = 1 / (np.pi * differences) if size is None else 1 / (size * np.sin(np.pi * differences / size))
    sign, logarithm = np.linalg.slogdet(matrix)
    return float(sign * np.exp(logarithm))


def finite_spin_certificates():
    certificates = []
    for size in (6, 8, 10, 12):
        labels = np.arange(2**size, dtype=np.int64)
        diagonal = -sum(1 - 2 * ((labels >> site) & 1) for site in range(size))
        rows = [labels]
        columns = [labels]
        for site in range(size):
            rows.append(labels)
            columns.append(labels ^ ((1 << site) | (1 << ((site + 1) % size))))
        elements = [diagonal.astype(float)] + [-np.ones(len(labels)) for unused_site in range(size)]
        hamiltonian = coo_matrix((np.concatenate(elements), (np.concatenate(rows), np.concatenate(columns))),
                                 shape=(len(labels), len(labels))).tocsr()
        energy, vectors = eigsh(hamiltonian, k=1, which="SA", tol=2e-14, v0=np.ones(len(labels)))
        ground = vectors[:, 0]
        residual = float(np.linalg.norm(hamiltonian @ ground - energy[0] * ground))
        close(energy[0], -2 / np.sin(np.pi / (2 * size)), 2e-11, "finite ED energy")
        parity = np.prod([1 - 2 * ((labels >> site) & 1) for site in range(size)], axis=0)
        parity_mean = float(np.dot(ground**2, parity))
        close(parity_mean, 1, 1e-11, "finite ED even sector")
        cases = []
        for quartet in itertools.combinations(range(size), 4):
            mask = sum(1 << site for site in quartet)
            observed = float(np.dot(ground, ground[labels ^ mask]))
            exact = determinant(quartet, size)
            difference = close(observed, exact, 2e-11, "finite ED four-X sine determinant")
            cases.append({"quartet": quartet, "spin_ed": observed, "sine_determinant": exact,
                          "absolute_difference": difference})
        certificates.append({"size": size, "ground_energy": float(energy[0]), "residual": residual,
                             "parity_mean": parity_mean, "quartet_count": len(cases),
                             "maximum_absolute_difference": max(case["absolute_difference"] for case in cases),
                             "quartets": cases})
    write_json(AUDIT / "ed_certificates.json", certificates)
    return {"quartets": sum(certificate["quartet_count"] for certificate in certificates),
            "max_absolute_difference": max(certificate["maximum_absolute_difference"] for certificate in certificates),
            "max_eigen_residual": max(certificate["residual"] for certificate in certificates)}


def score_boundaries():
    keys = ("energy_excess", "order_max_relative_error", "density_max_relative_error",
            "y_max_relative_error", "composite_order_max_relative_error")
    limits = (5e-5, .025, .1, .1, .01)
    boundary = dict(zip(keys, limits))
    assert physics.score_metrics(boundary)["passed"]
    for key, limit in zip(keys, limits):
        outside = dict(boundary)
        outside[key] = float(np.nextafter(limit, np.inf))
        assert not physics.score_metrics(outside)["passed"], key
    return {"synthetic_metric_boundary_checks": 6, "passing_tensor_constructed": False}


def malformed_cases(tensor):
    directory = AUDIT / "artifacts"
    directory.mkdir(exist_ok=True)
    cases = []

    def array_case(name, array):
        folder = directory / name
        folder.mkdir(exist_ok=True)
        path = folder / "state.npz"
        np.savez(path, A=array)
        cases.append((name, folder))

    for name, array in (("nan", np.full((2, 2, 2), np.nan)), ("odd_dimension", np.zeros((2, 3, 3))),
                        ("oversized_dimension", np.zeros((2, 26, 26))), ("wrong_rank", np.zeros((2, 2))),
                        ("nonsquare", np.zeros((2, 2, 3))), ("integer_dtype", np.zeros((2, 2, 2), dtype=int)),
                        ("object_dtype", np.zeros((2, 2, 2), dtype=object)), ("noncanonical", tensor * 2),
                        ("nonprimitive", np.array([np.eye(2), np.zeros((2, 2))]))):
        array_case(name, array)
    violated = tensor.copy()
    violated[0, 0, tensor.shape[1] // 2] = .1
    array_case("parity_violation", violated)
    for name in ("missing", "garbage", "extra_key", "missing_key", "directory", "symlink", "broken_symlink",
                 "invalid_npy", "claimed_huge_shape", "oversized_file", "compressed_expansion", "duplicate_member"):
        folder = directory / name
        folder.mkdir(exist_ok=True)
        path = folder / "state.npz"
        if name == "garbage":
            path.write_bytes(b"not a numpy archive")
        elif name == "extra_key":
            np.savez(path, A=tensor, score=1)
        elif name == "missing_key":
            np.savez(path, B=tensor)
        elif name == "directory":
            path.mkdir(exist_ok=True)
        elif name in ("symlink", "broken_symlink"):
            if path.is_symlink():
                path.unlink()
            path.symlink_to(CONCEPT / "participant" / "baseline" / "state.npz" if name == "symlink" else folder / "absent.npz")
        elif name == "invalid_npy":
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("A.npy", b"not an array")
        elif name == "claimed_huge_shape":
            header = repr({"descr": "<f8", "fortran_order": False, "shape": (2, 2**40, 2**40)}) + "\n"
            payload = b"\x93NUMPY\x01\x00" + struct.pack("<H", len(header)) + header.encode("ascii")
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("A.npy", payload)
        elif name == "oversized_file":
            path.write_bytes(b"0" * 1048577)
        elif name == "compressed_expansion":
            np.savez_compressed(path, A=np.zeros((2, 512, 512)))
        elif name == "duplicate_member":
            payload = io.BytesIO()
            np.save(payload, tensor, allow_pickle=False)
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("A.npy", payload.getvalue())
                archive.writestr("A.npy", payload.getvalue())
        cases.append((name, folder))
    outcomes = []
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    for name, folder in cases:
        trusted = physics.check(folder / "state.npz")
        assert trusted["valid"] is False and trusted["passed"] is False, name
        public_run = subprocess.run([sys.executable, str(CONCEPT / "participant" / "workspace" / "check.py"),
                                     str(folder / "state.npz")], capture_output=True, text=True, env=environment, timeout=120, check=True)
        public = json.loads(public_run.stdout)
        official_run = subprocess.run([sys.executable, str(CONCEPT / "evaluator" / "evaluate.py"),
                                       "--submission", str(folder)], capture_output=True, text=True,
                                      env=environment, timeout=125, check=True)
        official = json.loads(official_run.stdout)
        assert not public["valid"] and not official["valid"], name
        assert public["contract_version"] == official["contract_version"] == "critical-vacuum-v3"
        outcomes.append({"case": name, "trusted": trusted, "public": public, "official": official})
    for version in ((1, 0), (2, 0), (3, 0)):
        payload = io.BytesIO()
        np.lib.format.write_array(payload, tensor, version=version, allow_pickle=False)
        path = directory / f"valid_npy_{version[0]}.npz"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("A.npy", payload.getvalue())
        close(physics.load_tensor(path), tensor, 0, "supported numeric NPY version")
    write_json(AUDIT / "artifact_rejection.json", outcomes)
    return {"rejected_cases": len(outcomes), "checked_interfaces": ["trusted function", "public CLI", "official CLI"],
            "numeric_npy_versions_accepted": [1, 2, 3]}


def main():
    started = time.monotonic()
    AUDIT.mkdir(parents=True, exist_ok=True)
    contract = json.loads((CONCEPT / "participant" / "input" / "contract.json").read_text())
    quartets = json.loads((CONCEPT / "participant" / "input" / "fourpoint_quartets.json").read_text())
    assert quartets == [list(quartet) for quartet in physics.COMPOSITE_QUARTETS]
    assert len(quartets) == len({tuple(quartet) for quartet in quartets}) == 60
    assert contract["version"] == physics.CONTRACT_VERSION == "critical-vacuum-v3"
    assert contract["composite_order_channel"]["maximum_relative_error"] == .01
    assert contract["energy_excess_max"] == 5e-5
    assert contract["order_channel"]["maximum_relative_error"] == .025
    assert contract["density_channel"]["maximum_relative_error"] == contract["y_channel"]["maximum_relative_error"] == .1
    assert contract["construction_wall_seconds"] == 3600 and contract["checker_timeout_seconds"] == 120
    public_source = (CONCEPT / "participant" / "workspace" / "physics.py").read_bytes()
    trusted_source = (CONCEPT / "evaluator" / "hidden" / "trusted_physics.py").read_bytes()
    assert public_source == trusted_source
    target_audits = []
    for quartet in physics.COMPOSITE_QUARTETS:
        raw = determinant(quartet)
        first, second, third, fourth = quartet
        product = physics.exact_order(second - first) * physics.exact_order(fourth - third)
        error = close(raw - product, physics.exact_composite_covariance(quartet), 1e-12, "exact lattice covariance")
        close(raw, physics.exact_four_order(quartet), 1e-12, "exact raw four-spin order")
        close(determinant(quartet, 2**22), raw, 1e-9, "finite sine determinant infinite limit")
        target_audits.append({"quartet": quartet, "raw_cauchy_determinant": raw,
                              "exact_covariance": physics.exact_composite_covariance(quartet),
                              "absolute_difference": error})
    write_json(AUDIT / "exact_target_certificates.json", target_audits)
    finite_ed = finite_spin_certificates()
    baseline_path = CONCEPT / "participant" / "baseline" / "state.npz"
    champion = CONCEPT / "champions" / "generation_2" / "state.npz"
    assert baseline_path.read_bytes() == champion.read_bytes()
    assert not (CONCEPT / "participant" / "baseline" / "build.py").exists()
    tensor = physics.load_tensor(baseline_path)
    baseline = physics.check(baseline_path)
    assert baseline["valid"] and not baseline["passed"]
    assert all(baseline["family_scores"][family] == 1 for family in ("energy", "order", "density", "y_spin"))
    previous = json.loads((CONCEPT / "adversary" / "fourpoint_search" / "champion_v2_recheck.json").read_text())
    regression = {}
    for key in ("energy_excess", "order_correlations", "density_connected_correlations", "y_correlations"):
        regression[key] = close(baseline["metrics"][key], previous["metrics"][key], 2e-12, "unchanged v2 " + key)
    reference_path = CONCEPT / "adversary" / "fourpoint_search" / "fourpoint.py"
    specification = importlib.util.spec_from_file_location("independent_fourpoint_reference", reference_path)
    reference = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(reference)
    independent = reference.TensorContractions(tensor)
    independent_differences = []
    wrong_subtraction_differences = []
    for index, quartet in enumerate(physics.COMPOSITE_QUARTETS):
        observed = independent.evaluate(quartet)
        covariance = baseline["metrics"]["composite_order_covariances"][index]
        independent_differences.append(close(observed["covariance"], covariance, 1e-12, "independent four-point contraction"))
        raw = baseline["metrics"]["composite_order_four_spin_correlations"][index]
        left_mean, right_mean = baseline["metrics"]["composite_order_interval_means"][index]
        close(raw - left_mean * right_mean, covariance, 0, "literal own-mean subtraction")
        first, second, third, fourth = quartet
        close(left_mean, baseline["metrics"]["order_correlations"][second-first-1], 2e-13, "left interval mean")
        close(right_mean, baseline["metrics"]["order_correlations"][fourth-third-1], 2e-13, "right interval mean")
        wrong = raw - physics.exact_order(second-first) * physics.exact_order(fourth-third)
        wrong_subtraction_differences.append(abs(wrong - covariance))
    assert max(wrong_subtraction_differences) > 1e-6
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    official_run = subprocess.run([sys.executable, str(CONCEPT / "evaluator" / "evaluate.py"),
                                   "--submission", str(baseline_path.parent), "--output", str(AUDIT / "baseline_score.json")],
                                  capture_output=True, text=True, env=environment, timeout=125, check=True)
    official = json.loads(official_run.stdout)
    public_run = subprocess.run([sys.executable, str(CONCEPT / "participant" / "workspace" / "check.py"), str(baseline_path)],
                                capture_output=True, text=True, env=environment, timeout=125, check=True)
    public = json.loads(public_run.stdout)
    write_json(AUDIT / "baseline_public_score.json", public)
    assert public["metrics"] == official["metrics"] == baseline["metrics"]
    close(public["core_score"], official["core_score"], 0, "public and official scoring")
    boundaries = score_boundaries()
    rejection = malformed_cases(tensor)
    result = {"passed": True, "contract_version": physics.CONTRACT_VERSION,
              "threshold_fixed_before_fresh_attempts": .01, "quartet_count": 60,
              "finite_ed": finite_ed, "exact_target_max_absolute_difference": max(record["absolute_difference"] for record in target_audits),
              "minimum_exact_covariance": min(record["exact_covariance"] for record in target_audits),
              "independent_contraction_max_absolute_difference": max(independent_differences),
              "wrong_exact_mean_subtraction_max_absolute_difference": max(wrong_subtraction_differences),
              "v2_regression_max_absolute_differences": regression, "score_boundary_tests": boundaries,
              "artifact_rejection": rejection, "public_trusted_source_sha256": hashlib.sha256(public_source).hexdigest(),
              "baseline_sha256": hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
              "baseline_valid": baseline["valid"], "baseline_passed": baseline["passed"],
              "baseline_core_score": baseline["core_score"], "baseline_worst_family_score": baseline["worst_family_score"],
              "baseline_composite_max_relative_error": baseline["metrics"]["composite_order_max_relative_error"],
              "baseline_checker_seconds": official["runtime_seconds"], "total_validation_seconds": time.monotonic() - started,
              "passing_v3_tensor_known": False, "fresh_agents_launched": False,
              "previous_attempt_construction_code_read": False, "old_generation_archives_modified": False}
    write_json(AUDIT / "validation.json", result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
