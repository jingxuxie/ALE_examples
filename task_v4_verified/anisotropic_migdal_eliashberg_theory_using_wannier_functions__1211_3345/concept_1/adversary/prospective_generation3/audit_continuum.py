"""Audit resolved continuum data, independent roots, actual failures and extended controls."""

import hashlib
import json
import os
from pathlib import Path
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"
sys.dont_write_bytecode = True
import numpy as np

SIDECAR = Path(__file__).resolve().parent
ROOT = SIDECAR.parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
import evaluate


def load(path):
    assert path.is_file() and not path.is_symlink()
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


def main():
    started = time.process_time()
    selection = json.loads((ROOT / "adversary/generation_3/selection.json").read_text())
    protocol = json.loads((SIDECAR / "protocol.json").read_text())
    checks = []

    def check(name, value):
        if not value:
            raise AssertionError(name)
        checks.append(name)

    actual = {}
    extended = {}
    probe_cost = 0
    for folder in ("actual_v4_continuum", "actual_v4_continuum_06"):
        report = json.loads((SIDECAR / folder / "evaluation.json").read_text())
        check(folder + ":same_budget", report["resources"] == {"cpu_seconds": 12, "memory_mb": 2048, "threads": 1, "wall_seconds": 1800})
        check(folder + ":actual_code", report["solver_sha256"] == hashlib.sha256((ROOT / "champions/generation_3/solve.py").read_bytes()).hexdigest())
        actual.update({record["case_id"]: record for record in report["cases"]})
        probe_cost += report["aggregate_cpu_seconds"]
    for folder in ("v4_continuum_deadline_lifted", "v4_continuum_06_deadline_lifted"):
        report = json.loads((SIDECAR / folder / "evaluation.json").read_text())
        check(folder + ":extended_not_target", report["resources"]["cpu_seconds"] == 90 and not report["same_target_resource_test"])
        for record in report["cases"]:
            extended[record["case_id"]] = (record, SIDECAR / folder / (record["case_id"] + "_output.npz"))
        probe_cost += report["aggregate_cpu_seconds"]
    check("extended_algorithm_byte_identity", (SIDECAR / "continuum_extended/actual_v4.py").read_bytes() ==
          (ROOT / "champions/generation_3/solve.py").read_bytes())
    records = []
    for case_id in selection["replacements"].values():
        directory = SIDECAR / "continuum_cases" / case_id
        parameters = json.loads((directory / "parameters.json").read_text())
        certificate = json.loads((directory / "certificate.json").read_text())
        instance = load(directory / "instance.npz")
        reference = load(directory / "reference.npz")
        spectrum = load(directory / "spectral_parameters.npz")
        check(case_id + ":public_input_only", set(instance) == set(evaluate.INPUT_KEYS))
        check(case_id + ":finite_numeric", all(value.dtype.kind in "fiu" and np.isfinite(value).all() for value in instance.values()))
        check(case_id + ":resolved_96_bins", len(np.unique(instance["omega"])) == parameters["n_modes"] == 96
              and parameters["normalized_kernel_difference_vs_192_bins"] < 1e-8)
        check(case_id + ":positive_symmetric", np.all(instance["omega"] > 0) and np.all(instance["coupling"] > 0)
              and np.allclose(instance["coupling"], instance["coupling"].transpose(0, 2, 1), rtol=0, atol=1e-13))
        check(case_id + ":distinct_patch_and_mode_structure", parameters["spectral_matrix_rank_relative_1e_8"] > 50
              and parameters["minimum_patch_singular_ratio"] > 1e-10 and parameters["maximum_relative_noncommutator"] > 0.05)
        profile = np.sum(spectrum["amplitudes"][None, :] * np.exp(-0.5 *
                         ((spectrum["log_nodes"][:, None, None, None] - spectrum["centers"][None, :]) /
                          spectrum["widths"][None, :]) ** 2), axis=1)
        spectral_weights = spectrum["log_quadrature_weights"][:, None, None] * profile
        spectral_weights /= spectral_weights.sum(axis=0)
        permutation = spectrum["patch_permutation"]
        rebuilt = spectrum["integrated_coupling"][None, :] * spectral_weights[:, permutation][:, :, permutation]
        reconstruction_error = float(np.max(np.abs(rebuilt - instance["coupling"]) /
                                             spectrum["integrated_coupling"][None, :]))
        check(case_id + ":smooth_profile_reconstruction", reconstruction_error < 2e-14)
        check(case_id + ":fixed_integrated_lambda", np.allclose(instance["coupling"].sum(axis=0), spectrum["integrated_coupling"], rtol=2e-14, atol=0)
              and 0 < parameters["integrated_lambda_min"] < parameters["integrated_lambda_max"] < 2)
        check(case_id + ":fixed_frequency_window", 17.15 < parameters["finite_cutoff_over_physical_phonon_upper"] < 17.17)
        check(case_id + ":independent_nonzero_certificate", certificate["valid"] and certificate["normal_pairing_eigenvalue"] > 1.0001
              and certificate["minimum_low_gap_over_piT"] > 1e-7 and certificate["initial_amplitude_factors"] == [0.65, 1.5])
        for key in ("primary_all_frequency", "second_start_all_frequency", "primary_direct_rows", "second_start_direct_rows"):
            check(case_id + ":" + key, certificate[key]["gap_residual"] < 5e-12 and certificate[key]["z_residual"] < 5e-12)
        check(case_id + ":cross_start", certificate["second_start_all_frequency"]["branch_error"] < 1e-6)
        for name, key in (("instance.npz", "instance_sha256"), ("reference.npz", "reference_sha256")):
            check(case_id + ":hash:" + name, hashlib.sha256((directory / name).read_bytes()).hexdigest() == certificate[key])
        execution = actual[case_id]["execution"]
        check(case_id + ":actual_cpu_failure", execution["returncode"] == -24 and execution["cpu_seconds"] > 11.5 and not execution["wall_timeout"])
        extended_record, extended_path = extended[case_id]
        timed = {"execution": extended_record["execution"], "output_available": extended_path.is_file(),
                 "quality_passed": False, "same_target_resource_test": False}
        check(case_id + ":large_resource_margin", timed["execution"]["cpu_seconds"] > 24)
        if timed["output_available"]:
            output = load(extended_path)
            timed["quality"] = evaluate.metrics(instance, output["delta"], output["z"], reference["delta"])
            timed["quality_passed"] = evaluate.accepted(timed["quality"])
            check(case_id + ":extended_quality", timed["quality_passed"])
        else:
            check(case_id + ":extended_lower_bound", timed["execution"]["returncode"] == -24)
        records.append({"case_id": case_id, "family": parameters["family"], "n_freq": parameters["n_freq"],
                        "patches": parameters["patches"], "n_modes": parameters["n_modes"],
                        "normal_pairing_eigenvalue": certificate["normal_pairing_eigenvalue"],
                        "normalized_kernel_difference_vs_192_bins": parameters["normalized_kernel_difference_vs_192_bins"],
                        "spectral_reconstruction_error": reconstruction_error,
                        "integrated_lambda_range": [parameters["integrated_lambda_min"], parameters["integrated_lambda_max"]],
                        "spectral_matrix_rank_relative_1e_8": parameters["spectral_matrix_rank_relative_1e_8"],
                        "minimum_patch_singular_ratio": parameters["minimum_patch_singular_ratio"],
                        "maximum_relative_noncommutator": parameters["maximum_relative_noncommutator"],
                        "reference_quality": certificate["primary_all_frequency"],
                        "cross_start_branch_error": certificate["second_start_all_frequency"]["branch_error"],
                        "actual_v4_same_budget": actual[case_id], "deadline_lifted_control": timed,
                        "offline_reference_cpu_seconds": certificate["offline_cpu_seconds"]})
    for name, expected in protocol["active_sealed_files"].items():
        check("active_unchanged:" + name, hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected)
    generation_cost = json.loads((SIDECAR / "continuum_generation.json").read_text())["cpu_seconds"]
    certificates = [json.loads(path.read_text()) for path in (SIDECAR / "continuum_cases").glob("*/certificate.json")]
    reference_cost = sum(record["offline_cpu_seconds"] for record in certificates)
    audit_cost = time.process_time() - started
    accounted = generation_cost + probe_cost + reference_cost + audit_cost + 2 * len(certificates)
    check("bounded_search_cpu", accounted < 1800)
    result = {"passed": True, "checks_passed": len(checks), "checks": checks, "cases": records,
              "actual_v4_selected_accepted": 0, "selected_count": 4,
              "joint_12_cpu_attainability_established": False,
              "offline_certificates_do_not_establish_joint_attainability": True,
              "root_cause": "Resolved anisotropic phonon-continuum mode sums expose joint spectral/frequency computational cost. These failures do not rely on diminishing lambda-1, duplicate modes, padding, input filenames, or a polynomial-degree branch trap.",
              "actual_v4_joint_pool_passed": 4, "actual_v4_joint_pool_total": 4,
              "active_seal_unchanged": True, "active_sealed_files_verified": len(protocol["active_sealed_files"]),
              "cpu_accounting": {"generation": generation_cost, "candidate_probes_including_parent": probe_cost,
                                 "offline_references": reference_cost, "audit": audit_cost,
                                 "worker_startup_allowance": 2 * len(certificates), "accounted_total": accounted,
                                 "additional_budget": 1800},
              "new_fresh_launch_performed": False, "active_assets_modified": False}
    (SIDECAR / "continuum_audit.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key not in ("checks", "cases")}))


if __name__ == "__main__":
    main()
