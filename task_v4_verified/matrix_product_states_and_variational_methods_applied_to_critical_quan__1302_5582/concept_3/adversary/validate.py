import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from unittest import mock

import numpy as np
from scipy import linalg


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
sys.path.insert(0, str(ROOT / "evaluator/hidden"))
import evaluate
import teacher


CHECKS = []


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def rejects(name, function, exception=Exception):
    try:
        function()
    except exception:
        CHECKS.append(name)
        return
    raise AssertionError("Accepted forbidden input: " + name)


def scientific_checks():
    cutoff, omega = 6, 1.3
    coordinate, square, fourth, momentum_square = [operator.toarray()
        for operator in teacher.projected_operators(cutoff, omega)]
    occupation = np.arange(cutoff)
    check("projected_q2_analytic_diagonal", np.allclose(np.diag(square), (2 * occupation + 1) / (2 * omega)))
    check("projected_q4_analytic_diagonal", np.allclose(np.diag(fourth),
        3 * (2 * occupation ** 2 + 2 * occupation + 1) / (4 * omega ** 2)))
    check("projected_p2_analytic_diagonal", np.allclose(np.diag(momentum_square), omega * (2 * occupation + 1) / 2))
    check("not_power_of_truncated_coordinate", np.linalg.norm(fourth - np.linalg.matrix_power(coordinate, 4)) > 1)
    harmonic = (momentum_square + omega ** 2 * square) / 2
    check("projected_harmonic_boundary_exact", np.allclose(harmonic, np.diag(omega * (occupation + 0.5)), atol=1e-13))
    nodes, weights = np.polynomial.hermite.hermgauss(16)
    basis = np.ones((16, cutoff))
    basis[:, 1] = np.sqrt(2.0) * nodes
    for degree in range(2, cutoff):
        basis[:, degree] = (np.sqrt(2.0 / degree) * nodes * basis[:, degree - 1]
                            - np.sqrt((degree - 1.0) / degree) * basis[:, degree - 2])
    quadrature = {}
    for power, expected in ((1, coordinate), (2, square), (4, fourth)):
        operator = basis.T @ ((weights * (nodes / np.sqrt(omega)) ** power)[:, None] * basis) / np.sqrt(np.pi)
        check("independent_hermite_quadrature_power_%d" % power, np.allclose(operator, expected, atol=2e-13))
        quadrature[power] = operator
    mass, coupling = -1.7, 0.4
    matrix, origin = teacher.hamiltonian(2, cutoff, mass, coupling, omega)
    local = momentum_square / 2 + (mass + coupling) * quadrature[2] / 2 + quadrature[4] / 4
    independent = (np.kron(local, np.eye(cutoff)) + np.kron(np.eye(cutoff), local)
                   - coupling * np.kron(quadrature[1], quadrature[1]) - origin * np.eye(cutoff ** 2))
    check("independent_full_hamiltonian_quadrature", np.allclose(matrix.toarray(), independent, atol=5e-13))
    check("hamiltonian_symmetric", np.max(np.abs((matrix - matrix.T).toarray())) < 1e-13)
    occupations, parity = teacher.basis_indices(2, cutoff)
    check("exact_parity_blocks", matrix[parity == 0][:, parity == 1].nnz == 0)
    larger, larger_origin = teacher.hamiltonian(2, cutoff + 2, mass, coupling, omega)
    embedding = occupations[:, 0] * (cutoff + 2) + occupations[:, 1]
    check("nested_galerkin_projection", np.allclose(larger[embedding][:, embedding].toarray(), matrix.toarray(), atol=1e-13))
    check("cutoff_independent_origin", origin == larger_origin)
    result = teacher.spectrum(2, cutoff, mass, coupling, omega)
    for sector in (0, 1):
        reference = linalg.eigvalsh(matrix[parity == sector][:, parity == sector].toarray())[:2]
        check("parity_spectrum_dense_agreement_%d" % sector,
              np.allclose(reference, result["shifted_energies_dimensionless"][sector], rtol=1e-12, atol=1e-12))


def data_checks():
    evaluate.verify_integrity()
    contract = evaluate.load_json(ROOT / "evaluator/hidden/target_contract.json")
    certificates = evaluate.load_json(ROOT / "evaluator/hidden/certificates.json")["certificates"]
    private_by_id = {certificate["id"]: certificate for certificate in certificates}
    training = evaluate.load_json(ROOT / "participant/input/train.json")["cases"]
    validation = evaluate.load_json(ROOT / "participant/input/validation_inputs.json")["cases"]
    hidden = evaluate.load_json(ROOT / "evaluator/hidden/test_inputs.json")["cases"]
    public_labels = evaluate.load_json(ROOT / "participant/input/validation_labels.json")["predictions"]
    private_labels = evaluate.load_json(ROOT / "evaluator/hidden/test_labels.json")["predictions"]
    labels = {case["id"]: case["targets"] for case in training + public_labels + private_labels}
    all_cases = training + validation + hidden
    check("312_unique_ids", len(set(case["id"] for case in all_cases)) == len(all_cases) == 312)
    check("312_certificates", len(certificates) == len(private_by_id) == 312)
    realizations = set()
    for split, cases in (("train", training), ("validation", validation), ("hidden", hidden)):
        for family in contract["families"]:
            check("balanced_%s_%s" % (split, family), sum(case["family"] == family for case in cases)
                  == contract["counts_per_family"][split])
        for case in cases:
            certificate = private_by_id[case["id"]]
            scale = (case["lambda"] / 6) ** (1 / 3)
            final = certificate["history"][-1]
            realization = (case["sites"], round(case["mu2"] / scale ** 2, 12), round(case["kappa"] / scale ** 2, 12))
            if realization in realizations:
                raise AssertionError("Duplicated physical realization")
            realizations.add(realization)
            assert certificate["split"] == split
            assert certificate["accepted"] and not certificate["uncertainty_is_rigorous_tail_bound"]
            assert len(certificate["history"]) >= 3 and certificate["label_cutoff"] >= 36
            assert np.max(certificate["last_two_cutoff_log_changes"]) <= 2e-5
            assert max(certificate["independent_basis_log_change"]) <= 2e-5
            for record in (final, certificate["independent_basis"]):
                assert min(record["gaps_dimensionless"]) >= 1e-6
                assert max(record["residual_roundoff_gap_ratio"]) <= 2e-6
                assert np.max(record["state_residuals_dimensionless"]) <= 1e-10
            assert certificate["independent_basis"]["omega_dimensionless"] != final["omega_dimensionless"]
            actual = [labels[case["id"]][target] for target in evaluate.TARGETS]
            assert np.allclose(actual, scale * np.array(final["gaps_dimensionless"]), rtol=2e-15, atol=0)
            assert len(case["spectra"]) == 6
            assert {record["cutoff"] for record in case["spectra"]} == {4, 6, 8}
            if split != "train":
                assert "targets" not in case
            for record in case["spectra"]:
                even, odd = record["even_energies"], record["odd_energies"]
                differences = [odd[0] - even[0], even[1] - even[0], odd[1] - odd[0]]
                assert np.allclose(differences, [record["signed_gaps"][target] for target in evaluate.TARGETS], atol=1e-13)
                assert np.all(np.isfinite(even + odd))
                assert np.min(record["boundary_weights"]) >= 0 and np.max(record["boundary_weights"]) <= 1
    check("all_gap_labels_direct_and_certified", True)
    check("no_shared_dimensionless_hamiltonians", len(realizations) == 312)
    public_text = "".join(path.read_text() for path in (ROOT / "participant").rglob("*")
                          if path.is_file() and path.suffix in (".py", ".json", ".md"))
    check("no_hidden_ids_in_public_assets", all(case["id"] not in public_text for case in hidden))
    ledger = evaluate.load_json(ROOT / "evaluator/hidden/generation_seeds.json")
    check("no_generator_seeds_in_public_assets", all(str(job[3]) not in public_text for job in ledger["jobs"]))
    check("target_digest_unchanged", ledger["contract_sha256"] == hashlib.sha256(
        (ROOT / "evaluator/hidden/target_contract.json").read_bytes()).hexdigest())
    reference = evaluate.parse_predictions({"schema_version": 1, "predictions": private_labels},
                                          [case["id"] for case in hidden])
    raw = []
    for case in hidden:
        finest = [record for record in case["spectra"] if record["cutoff"] == 8]
        chosen = min(finest, key=lambda record: np.sum(record["boundary_weights"]))
        raw.append([max(abs(chosen["signed_gaps"][target]), 1e-12) for target in evaluate.TARGETS])
    raw_metrics = evaluate.score_predictions(np.array(raw), reference, [case["family"] for case in hidden])
    (ROOT / "attempts/raw_low_cutoff_hidden.json").write_text(json.dumps(raw_metrics, indent=2, allow_nan=False) + "\n")
    return {"schema_version": 1, "cases": hidden}, contract["resources"]


def parser_checks(temporary):
    ids = ["first", "second"]
    template = {"schema_version": 1, "predictions": [{"id": identifier,
        "targets": {target: 1.0 for target in evaluate.TARGETS}} for identifier in ids]}
    check("valid_prediction_parses", evaluate.parse_predictions(template, ids).shape == (2, 3))
    reversed_payload = copy.deepcopy(template)
    reversed_payload["predictions"].reverse()
    check("id_order_invariant", np.array_equal(evaluate.parse_predictions(template, ids),
                                              evaluate.parse_predictions(reversed_payload, ids)))
    for value in (0, -1, True, None, "1", float("nan"), float("inf"), -float("inf"), 10 ** 1000):
        payload = copy.deepcopy(template)
        payload["predictions"][0]["targets"]["odd_gap"] = value
        rejects("invalid_gap_" + str(value)[:20], lambda: evaluate.parse_predictions(payload, ids), evaluate.InvalidSubmission)
    mutations = {
        "missing_id": lambda payload: payload["predictions"].pop(),
        "duplicate_id": lambda payload: payload["predictions"][1].update(id="first"),
        "unknown_id": lambda payload: payload["predictions"][1].update(id="unknown"),
        "extra_target": lambda payload: payload["predictions"][0]["targets"].update(extra=1),
        "missing_target": lambda payload: payload["predictions"][0]["targets"].pop("odd_gap"),
        "extra_field": lambda payload: payload.update(extra=1),
        "boolean_version": lambda payload: payload.update(schema_version=True),
        "float_version": lambda payload: payload.update(schema_version=1.0)
    }
    for name, mutate in mutations.items():
        payload = copy.deepcopy(template)
        mutate(payload)
        rejects(name, lambda: evaluate.parse_predictions(payload, ids), evaluate.InvalidSubmission)
    for ordinal, text in enumerate(("{", "{} {}", '{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}', '{"a":-Infinity}')):
        path = temporary / "malformed.json"
        path.write_text(text)
        rejects("strict_json_%d" % ordinal, lambda: evaluate.load_json(path), evaluate.InvalidSubmission)
    perfect = np.ones((2, 3))
    check("perfect_score_is_one", evaluate.score_predictions(perfect, perfect, ["single_L2"] * 2, 0)["score"] == 1.0)
    doubled = evaluate.score_predictions(2 * perfect, perfect, ["single_L2"] * 2, 0)
    check("log_score_exact_factor_two", abs(doubled["mean_log_error"] - np.log(2)) < 1e-15)
    check("relative_score_exact_factor_two", doubled["median_relative_error"] == 1.0)
    extreme = evaluate.score_predictions(np.array([[1e-300, 1e300, 1.0]]), np.ones((1, 3)), ["single_L2"], 0)
    check("extreme_finite_metrics_strict_json", bool(json.dumps(extreme, allow_nan=False)))


def sandbox_checks(temporary, inputs, limits):
    submission = temporary / "submission"
    submission.mkdir()
    shutil.copyfile(ROOT / "adversary/fixture_predict.py", submission / "predict.py")

    def configure(mode, **values):
        (submission / "fixture.json").write_text(json.dumps(dict(mode=mode, **values)))

    forbidden = [str(ROOT / "evaluator/hidden/test_labels.json"), str(ROOT / "evaluator/evaluate.py"),
                 str(ROOT / "adversary/validate.py"), "/evaluator/hidden/test_labels.json",
                 "/runner.py", "/proc/1/root" + str(ROOT / "evaluator/hidden/test_labels.json")]
    configure("probe", forbidden_reads=forbidden)
    payload, elapsed = evaluate.run_submission(submission, inputs, limits)
    check("isolated_runtime_all_probes_blocked", all(payload.values()) and len(payload) == len(forbidden) + 8)
    configure("raw", text='{"schema_version":1,"predictions":[NaN]}')
    rejects("subprocess_nan_output", lambda: evaluate.run_submission(submission, inputs, limits), evaluate.InvalidSubmission)
    configure("raw", text="{not json")
    rejects("subprocess_malformed_output", lambda: evaluate.run_submission(submission, inputs, limits), evaluate.InvalidSubmission)
    configure("symlink_output")
    rejects("output_symlink", lambda: evaluate.run_submission(submission, inputs, limits), evaluate.InvalidSubmission)
    for mode in ("sleep", "cpu", "memory", "oversized"):
        configure(mode)
        constrained = dict(limits, wall_seconds=1 if mode == "sleep" else 5, cpu_seconds=1 if mode == "cpu" else 30)
        rejects("resource_" + mode, lambda: evaluate.run_submission(submission, inputs, constrained), evaluate.InvalidSubmission)
    (submission / "linked").symlink_to(ROOT / "evaluator/hidden/test_labels.json")
    rejects("submission_symlink", lambda: evaluate.stage_submission(submission, temporary / "staged", 1024 ** 2), evaluate.InvalidSubmission)
    with mock.patch.object(evaluate.shutil, "which", return_value=None):
        rejects("missing_sandbox_fails_closed", lambda: evaluate.sandbox_command(temporary), RuntimeError)
    return payload


def tamper_check(temporary):
    copied = temporary / "trusted"
    manifest = evaluate.load_json(ROOT / "evaluator/hidden/integrity.json")
    for filename in list(manifest["sha256"]) + ["evaluator/hidden/integrity.json"]:
        destination = copied / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / filename, destination)
    evaluate.verify_integrity(copied)
    target = copied / "evaluator/hidden/test_labels.json"
    target.write_text(target.read_text() + " ")
    rejects("hidden_label_tampering_detected", lambda: evaluate.verify_integrity(copied), RuntimeError)


def main():
    scientific_checks()
    inputs, limits = data_checks()
    with tempfile.TemporaryDirectory(prefix="checks-", dir=ROOT / "adversary") as temporary:
        temporary = Path(temporary)
        parser_checks(temporary)
        probes = sandbox_checks(temporary, inputs, limits)
        tamper_check(temporary)
    report = {"status": "passed", "check_count": len(CHECKS), "checks": CHECKS,
              "sandbox_probes": probes, "agent_launches": 0,
              "scope": "builder self-checks, not participant performance or hardness evidence"}
    (ROOT / "attempts/validation_report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": "passed", "check_count": len(CHECKS)}))


if __name__ == "__main__":
    main()
