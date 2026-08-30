"""Repeat physical, numerical, provenance and immutability checks privately."""

import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"
sys.dont_write_bytecode = True
import numpy as np

SIDECAR = Path(__file__).resolve().parent
ROOT = SIDECAR.parents[1]
sys.path.insert(0, str(ROOT / "evaluator" / "hidden"))
from physics import INPUT_KEYS, direct_rows, metrics


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    assert path.is_file() and not path.is_symlink(), str(path)
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (60, 61))
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024 ** 3, 3 * 1024 ** 3))
    started = time.process_time()
    summary = json.loads((SIDECAR / "summary.json").read_text())
    protocol = json.loads((SIDECAR / "protocol.json").read_text())
    plan = json.loads((SIDECAR / "plan.json").read_text())
    passed = []

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        passed.append(name)

    check("prospective_only", summary["prospective_only"] and not summary["promoted_generation"])
    check("no_v4_test_or_failure_claim", not summary["actual_v4_tested"] and not summary["actual_v4_failure_claimed"])
    check("no_public_assets_or_launch", not summary["new_public_assets"] and not summary["fresh_launch_performed"])
    check("bounded_case_count", 0 < summary["certified_cases"] <= summary["attempted_cases"] <= 4)
    for name, expected in protocol["copied_source_sha256"].items():
        check("copied_source:" + name, digest(SIDECAR / name) == expected)
    for name, expected in protocol["active_sealed_files"].items():
        check("active_unchanged:" + name, digest(ROOT / name) == expected)

    cases = []
    instance_hashes = []
    for report in summary["case_reports"]:
        if not report["reference_valid"]:
            continue
        case_id = report["case_id"]
        directory = SIDECAR / "cases" / case_id
        parameters = json.loads((directory / "parameters.json").read_text())
        certificate = json.loads((directory / "certificate.json").read_text())
        instance = load(directory / "instance.npz")
        primary = load(directory / "reference.npz")
        secondary = load(directory / "oracle_2.npz")
        count = int(instance["n_freq"])
        weights = instance["weights"]
        patches = len(weights)
        temperature = float(instance["temperature"])
        energies = instance["omega"]
        coupling = instance["coupling"]
        coulomb = instance["coulomb"]
        labels = np.array(parameters["band"])
        prefix = case_id + ":"
        check(prefix + "public_input_only", set(instance) == set(INPUT_KEYS))
        check(prefix + "numeric_finite", all(value.dtype.kind in "fiu" and np.isfinite(value).all()
                                             for value in instance.values()))
        check(prefix + "weights", bool(np.all(weights > 0)) and abs(float(weights.sum()) - 1) < 1e-14)
        check(prefix + "dimensions", count == parameters["n_freq"] and patches == parameters["patches"]
              and instance["initial_delta"].shape == (patches, count)
              and coupling.shape == (4, patches, patches) and coulomb.shape == (patches, patches))
        check(prefix + "positive_distinct_modes", bool(np.all(energies > 0)) and len(np.unique(energies)) == 4)
        check(prefix + "attractive_symmetric_spectra", bool(np.all(coupling > 0))
              and np.allclose(coupling, coupling.transpose(0, 2, 1), rtol=0, atol=1e-13))
        check(prefix + "repulsive_symmetric_coulomb", bool(np.all(coulomb >= 0))
              and np.allclose(coulomb, coulomb.T, rtol=0, atol=1e-13))
        integrated = (coupling.sum(axis=0) * weights).sum(axis=1)
        check(prefix + "moderate_integrated_coupling", bool(np.all((integrated > 0) & (integrated < 4))))
        check(prefix + "lambda_metadata", abs(float(integrated.max()) - parameters["integrated_lambda_max"]) < 1e-13)
        ratios = []
        for matrix in coupling:
            singular_values = np.linalg.svd(matrix, compute_uv=False)
            ratios.append(float(singular_values[-1] / singular_values[0]))
        check(prefix + "distinct_full_rank_patches", min(ratios) > 1e-10)
        cutoff_ratio = (2 * count - 1) * np.pi * temperature / energies.max()
        check(prefix + "preserved_frequency_window", 17.15 < cutoff_ratio < 17.17)
        check(prefix + "low_temperature", abs(float(energies.max() / temperature)
                                               / parameters["max_phonon_over_temperature"] - 1) < 1e-13)
        eigenvalues = np.array(certificate["isolated_sheet_eigenvalues"])
        check(prefix + "joint_large_nearcritical", count >= 16384
              and np.any((eigenvalues > 1) & (eigenvalues <= 1 + 1.1e-8)))
        check(prefix + "full_instability", certificate["normal_pairing_eigenvalue"] > 1)
        if len(eigenvalues) > 1:
            check(prefix + "weak_positive_links", 0 < parameters["interband_factor"] <= 3e-12)
        instance_hash = digest(directory / "instance.npz")
        instance_hashes.append(instance_hash)
        check(prefix + "instance_hash", instance_hash == certificate["instance_sha256"] == parameters["instance_sha256"])
        check(prefix + "reference_hash", digest(directory / "reference.npz") == certificate["reference_sha256"])
        check(prefix + "reference_fields", set(primary) == set(secondary) == {"delta", "z"}
              and all(value.shape == (patches, count) and np.isfinite(value).all()
                      for value in list(primary.values()) + list(secondary.values())))
        repeated = {}
        for name, output in (("primary", primary), ("secondary", secondary)):
            full = metrics(instance, output["delta"], output["z"], primary["delta"])
            direct = direct_rows(instance, output["delta"], output["z"])
            check(prefix + name + "_exact_residual", max(full["gap_residual"], full["z_residual"],
                                                        direct["gap_residual"], direct["z_residual"]) < 5e-13)
            check(prefix + name + "_nonzero_branch", full["sign_correct"] and full["branch_error"] < 2e-6
                  and float(np.min(output["delta"][:, 0]) / (np.pi * temperature)) > 1e-9)
            repeated[name] = {"all_frequency": full, "direct_rows": direct}
        check(prefix + "independent_starts", certificate["initial_amplitude_factors"] == [0.6, 1.7])
        check(prefix + "no_joint_budget_claim", certificate["joint_12_cpu_attainability"] ==
              "not_asserted_by_this_offline_certificate" and not certificate["actual_v4_failure_claimed"])
        comparisons = {}
        for name, result in report["comparators"].items():
            if not result["tested"] or "quality" not in result:
                comparisons[name] = result
                continue
            output = load(directory / (name + "_output.npz"))
            orientation = 1 if np.dot(weights, output["delta"][:, 0]) >= 0 else -1
            aligned = orientation * output["delta"]
            scale = np.maximum(np.max(np.abs(primary["delta"]), axis=1), np.pi * temperature * 1e-10)
            patch_error = np.max(np.abs(aligned - primary["delta"]) / scale[:, None], axis=1)
            check(prefix + name + "_branch_report", abs(float(patch_error.max()) - result["quality"]["branch_error"]) < 1e-12)
            sheet_details = []
            for label in np.unique(labels):
                selected = labels == label
                amplitude_ratio = float(np.max(np.abs(aligned[selected, 0])) /
                                        np.max(np.abs(primary["delta"][selected, 0])))
                sheet_details.append({"sheet": int(label), "worst_branch_error": float(patch_error[selected].max()),
                                      "low_frequency_amplitude_ratio": amplitude_ratio})
            comparisons[name] = {"accepted": result["accepted"], "cpu_seconds": result["execution"]["cpu_seconds"],
                                 "quality": result["quality"], "sheets": sheet_details,
                                 "observed_failure": "collapsed_normal_branch" if max(
                                     item["low_frequency_amplitude_ratio"] for item in sheet_details) < 1e-3
                                 else "weak_sheet_branch_and_or_residual"}
        cases.append({"case_id": case_id, "patches": patches, "n_freq": count, "bands": len(eigenvalues),
                      "cutoff_over_max_phonon": float(cutoff_ratio), "max_phonon_over_temperature": float(energies.max() / temperature),
                      "integrated_lambda_range": [float(integrated.min()), float(integrated.max())],
                      "minimum_patch_singular_value_ratio": min(ratios), "certificate_recheck": repeated,
                      "comparators": comparisons})
    check("distinct_generated_instances", len(set(instance_hashes)) == len(instance_hashes))
    elapsed = time.process_time() - started
    check("aggregate_cpu_including_audit", summary["aggregate_cpu_seconds"] + elapsed < plan["cpu_budget_seconds"])
    result = {"passed": True, "checks_passed": len(passed), "checks": passed, "cases": cases,
              "active_sealed_files_verified": len(protocol["active_sealed_files"]),
              "active_seal_unchanged": True, "audit_cpu_seconds": elapsed,
              "aggregate_build_and_audit_cpu_seconds": summary["aggregate_cpu_seconds"] + elapsed,
              "prospective_only": True, "actual_v4_tested": False,
              "new_joint_same_budget_attainability": "unknown; offline branch certificates only"}
    (SIDECAR / "audit.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key not in ("checks", "cases")}))


if __name__ == "__main__":
    main()
