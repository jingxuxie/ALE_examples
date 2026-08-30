"""Numerical independence, artifact parser, and path-security regression audit."""

import copy
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE / "participant" / "workspace"))
sys.path.insert(0, str(BASE / "evaluator"))

from evaluate import evaluate_artifact
from independent import IndependentSystem
from oracle import DeterminantCC, random_pair_matrix
from validate_oracle import validate


def numerical_audit():
    rng = np.random.default_rng(983412)
    comparisons = []
    for electrons in (2, 3):
        public = DeterminantCC(6, electrons)
        private = IndependentSystem(electrons)
        energies = (np.array([-1.2, -0.6, 0.6, 0.9, 1.3, 1.6]) if electrons == 2
                    else np.array([-1.2, -0.9, -0.5, 0.5, 0.9, 1.2]))
        for trial in range(8):
            interaction = random_pair_matrix(rng, 0.02 + 0.02 * trial)
            hamiltonian, one_body, tensor = public.hamiltonian(energies, interaction)
            independent_hamiltonian, independent_one_body, independent_fock = private.build(energies, interaction)
            amplitudes = rng.normal(0, 0.07, public.count)
            public_equations = public.equations(hamiltonian, amplitudes)
            private_equations = private.equations(independent_hamiltonian, amplitudes)
            errors = {"hamiltonian": float(np.max(np.abs(hamiltonian - independent_hamiltonian))),
                      "one_body": float(np.max(np.abs(one_body - independent_one_body))),
                      "residual": float(np.max(np.abs(public_equations[0] - private_equations[0]))),
                      "jacobian": float(np.max(np.abs(public_equations[1] - private_equations[1]))),
                      "hbar": float(np.max(np.abs(public_equations[2] - private_equations[2])))}
            for label, public_hessian, private_hessian in zip(("real_hessian", "imaginary_hessian"),
                                                            public.hf_stability(hamiltonian), private.stability(hamiltonian)):
                errors[label] = float(np.max(np.abs(public_hessian - private_hessian)))
            result = public.solve(hamiltonian)
            if not result.converged:
                raise AssertionError("calibration system failed to converge")
            public_diagnostics = public.diagnostics(hamiltonian, result)
            private_diagnostics = private.diagnose(energies, interaction, result.amplitudes)
            errors["occupations"] = float(max(abs(np.array(public_diagnostics["occupations"])
                                                  - private_diagnostics["occupations"])))
            errors["energy"] = abs(public_diagnostics["cc_energy"] - private_diagnostics["cc_energy"])
            errors["dad"] = abs(public_diagnostics["rdm_dad"] - private_diagnostics["rdm_dad"])
            if electrons == 2:
                errors["ccsd_fci_energy"] = private_diagnostics["energy_error"]
                errors["ccsd_fci_rdm_spectrum"] = float(max(abs(np.array(private_diagnostics["occupations"])
                                                               - private_diagnostics["exact_occupations"])))
            comparisons.append({"electrons": electrons, "trial": trial, "errors": errors,
                                "passed": all(value < 2e-8 for value in errors.values())})
    return {"passed": all(row["passed"] for row in comparisons), "comparisons": comparisons,
            "maximum_error": max(max(row["errors"].values()) for row in comparisons)}


def parser_audit(output_directory=None):
    output_directory = BASE / "adversary" / "generation_3" if output_directory is None else Path(output_directory)
    cases = output_directory / "cases"
    cases.mkdir(parents=True, exist_ok=True)
    example = json.loads((BASE / "participant" / "workspace" / "example.json").read_text())
    witness_path = BASE / "evaluator" / "hidden" / "calibration_refined" / "candidate.json"
    tests = []

    def check(name, raw=None, path=None, directory=None, expected_admissible=False):
        if path is None:
            path = cases / (name + ".json")
            path.write_bytes(raw if isinstance(raw, bytes) else raw.encode())
        report = evaluate_artifact(path, cases if directory is None else directory)
        admissible = report.get("diagnostics", {}).get("admissible", False)
        passed = report["passed"] is False and admissible == expected_admissible and report["score"] == 0
        tests.append({"name": name, "audit_passed": passed, "reason": report["reason"],
                      "admissible": admissible, "runtime_seconds": report["runtime_seconds"]})

    check("empty", "")
    check("invalid_utf8", b"\xff\xfe")
    check("truncated", '{"schema_version":')
    check("array_top_level", "[]")
    check("null_top_level", "null")
    check("duplicate_key", '{"schema_version":1,"schema_version":1}')
    check("oversize", " " * 65537)
    check("deep_nesting", "[" * 1500 + "0" + "]" * 1500)
    for field in example:
        altered = copy.deepcopy(example)
        del altered[field]
        check("missing_" + field, json.dumps(altered))
    altered = copy.deepcopy(example)
    altered["claimed_score"] = 1
    check("extra_key", json.dumps(altered))
    for version in (True, 1.0, "1", 2):
        altered = copy.deepcopy(example)
        altered["schema_version"] = version
        check("version_" + repr(version), json.dumps(altered))
    for value, label in [(float("nan"), "nan"), (float("inf"), "infinity"), (-float("inf"), "negative_infinity"),
                         (True, "boolean"), ("0", "numeric_string"), (None, "null"), ([0], "nested")]:
        altered = copy.deepcopy(example)
        altered["amplitudes"][0] = value
        check("amplitude_" + label, json.dumps(altered))
    altered = copy.deepcopy(example)
    altered["amplitudes"][0] = 1.2345
    check("overflow_literal", json.dumps(altered).replace("1.2345", "1e999"))
    altered = copy.deepcopy(example)
    altered["pair_matrix"][0] = [0] * 14
    check("wrong_pair_row", json.dumps(altered))
    altered = copy.deepcopy(example)
    altered["amplitudes"].append(0)
    check("wrong_amplitude_length", json.dumps(altered))
    altered = copy.deepcopy(example)
    altered["pair_matrix"][0][1] = 0.1
    check("asymmetric", json.dumps(altered))
    altered = copy.deepcopy(example)
    altered["pair_matrix"][0][0] = 1.6
    check("entry_limit", json.dumps(altered))
    altered = copy.deepcopy(example)
    altered["pair_matrix"] = np.ones((15, 15)).tolist()
    check("frobenius_limit", json.dumps(altered))
    altered = copy.deepcopy(example)
    altered["amplitudes"][0] = 1.3
    check("amplitude_limit", json.dumps(altered))
    altered = copy.deepcopy(example)
    altered["orbital_energies"][0] -= 0.01
    check("changed_fock_spectrum", json.dumps(altered))
    altered = copy.deepcopy(example)
    altered["amplitudes"][0] += 1e-4
    check("forged_stationary_root", json.dumps(altered))
    check("missing_file", path=cases / "never_created.json")
    check("directory_as_file", path=cases)
    check("outside_submission", path=witness_path)
    for label, target in [("private_witness_symlink", witness_path),
                          ("dangling_private_symlink", BASE / "evaluator" / "hidden" / "future_witness.json")]:
        link = cases / (label + ".json")
        if not os.path.lexists(link):
            link.symlink_to(target)
        check(label, path=link)
    directory_link = cases / "linked_directory"
    if not os.path.lexists(directory_link):
        directory_link.symlink_to(witness_path.parent, target_is_directory=True)
    check("symlinked_parent", path=directory_link / "candidate.json")
    fifo = cases / "fifo.json"
    if not os.path.lexists(fifo):
        os.mkfifo(fifo)
    check("fifo", path=fifo)
    check("valid_nonwitness", json.dumps(example), expected_admissible=True)
    parent_reports = []
    for name, path in [("private_witness_symlink", cases / "private_witness_symlink.json"),
                       ("outside_submission", witness_path), ("missing_file", cases / "never_created.json")]:
        process = subprocess.run([sys.executable, "-I", str(BASE / "evaluator" / "evaluate.py"),
                                  str(path), "--submission-dir", str(cases)], capture_output=True, text=True, timeout=50)
        report = json.loads(process.stdout)
        parent_reports.append({"name": name, "audit_passed": report["passed"] is False and report["score"] == 0,
                               "reason": report["reason"]})
    for temporary_path in (cases / "private_witness_symlink.json", cases / "dangling_private_symlink.json", directory_link, fifo):
        temporary_path.unlink()
    return {"passed": all(row["audit_passed"] for row in tests + parent_reports),
            "case_count": len(tests) + len(parent_reports), "cases": tests, "parent_cli_cases": parent_reports}


def main():
    started = time.monotonic()
    output_directory = BASE / "adversary" / "generation_3"
    freeze = json.loads((output_directory / "freeze.json").read_text())
    frozen_match = all(hashlib.sha256((BASE / "participant" / name).read_bytes()).hexdigest() == digest
                       for name, digest in freeze["participant_files"].items())
    public_limits = json.loads((BASE / "participant" / "workspace" / "constraints.json").read_text())
    private_limits = json.loads((BASE / "evaluator" / "hidden" / "constraints.json").read_text())
    report = {"public_oracle_validation": validate(), "independence": numerical_audit(),
              "adversarial": parser_audit(), "participant_freeze_matches": frozen_match,
              "public_private_constraints_match": public_limits == private_limits,
              "runtime_seconds": time.monotonic() - started}
    report["passed"] = (report["public_oracle_validation"]["passed"] and report["independence"]["passed"]
                        and report["adversarial"]["passed"] and frozen_match and public_limits == private_limits)
    (output_directory / "audit.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({"passed": report["passed"], "adversarial_cases": report["adversarial"]["case_count"],
                      "independent_max_error": report["independence"]["maximum_error"],
                      "runtime_seconds": report["runtime_seconds"]}, indent=2), flush=True)
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
