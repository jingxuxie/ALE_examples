"""Generation-two DAD identity, invariance, and ratchet-only regression audit."""

import hashlib
import json
import os
import sys
import time
from pathlib import Path

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

BASE = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "participant" / "workspace"))
sys.path.insert(0, str(BASE / "evaluator"))
sys.path.insert(0, str(BASE / "evaluator" / "hidden"))

from api import CONSTRAINTS, endpoint_failures
from audit import numerical_audit, parser_audit
from evaluate import evaluate_artifact
from independent import IndependentSystem
from oracle import CCResult, DeterminantCC, random_pair_matrix
from validate_oracle import validate


def main():
    started = time.monotonic()
    rng = np.random.default_rng(7729401)
    identities = []
    for electrons in (2, 3):
        public = DeterminantCC(6, electrons)
        private = IndependentSystem(electrons)
        energies = ([-1.2, -0.6, 0.6, 0.9, 1.3, 1.6] if electrons == 2 else CONSTRAINTS["orbital_energies"])
        for trial in range(6):
            interaction = random_pair_matrix(rng, scale=0.03 + 0.035 * trial)
            hamiltonian, _, _ = public.hamiltonian(energies, interaction)
            result = public.solve(hamiltonian)
            multipliers, left, _ = public.lambda_state(result)
            density = public.rdm(left, result.right)
            antisymmetric = density - density.T
            expected = float(np.sqrt(np.sum(antisymmetric * antisymmetric) / electrons))
            public_value = public.diagnostics(hamiltonian, result)["rdm_dad"]
            private_value = private.diagnose(np.array(energies), interaction, result.amplitudes)["rdm_dad"]
            rotation, _ = np.linalg.qr(rng.normal(size=(6, 6)))
            rotated = rotation.T @ density @ rotation
            invariant = float(np.linalg.norm(rotated - rotated.T, ord="fro") / np.sqrt(electrons))
            error = max(abs(expected - public_value), abs(expected - private_value), abs(expected - invariant))
            identities.append({"electrons": electrons, "trial": trial, "expected": expected,
                               "max_error": error, "passed": error < 2e-12})
    example_path = BASE / "participant" / "workspace" / "example.json"
    zero_report = evaluate_artifact(example_path, example_path.parent)
    zero_diagnostics = zero_report["diagnostics"]
    boundaries = []
    for value, expected_failure in [(0.0, False), (0.001, False), (0.00100000001, True),
                                    (float("nan"), True), (float("inf"), True)]:
        probe = dict(zero_diagnostics)
        probe["rdm_dad"] = value
        observed = "rdm_dad" in endpoint_failures(probe)
        boundaries.append({"value": str(value), "expected_failure": expected_failure,
                           "observed_failure": observed, "passed": observed == expected_failure})
    old_witnesses = []
    for label, relative in [("champion", "champions/generation_1/submission.json"),
                            ("replicate_1", "attempts/v_1/submission.json"),
                            ("replicate_2", "attempts/v_1_r2/submission.json")]:
        path = BASE / relative
        if not path.is_file():
            continue
        report = evaluate_artifact(path, path.parent)
        old_witnesses.append({"label": label, "passed": report["passed"] is False
                             and report["reason"] == "constraints_failed: rdm_dad",
                             "dad": report["diagnostics"]["rdm_dad"],
                             "raw_violation": report["diagnostics"]["occupation_violation"]})
        if label == "champion":
            manual = json.loads(path.read_text())
            manual["rdm_dad"] = 0.0
            forged_path = OUTPUT / "forged_dad.json"
            forged_path.write_text(json.dumps(manual, allow_nan=False))
            forged_report = evaluate_artifact(forged_path, OUTPUT)
            forged_path.unlink()
    original_limits = json.loads((BASE / "adversary/generation_1_snapshot/participant/workspace/constraints.json").read_text())
    private_limits = json.loads((BASE / "evaluator/hidden/constraints.json").read_text())
    unchanged = dict(CONSTRAINTS)
    added = unchanged.pop("rdm_dad_max")
    preservation = json.loads((OUTPUT / "preservation_before.json").read_text())
    preserved = all(hashlib.sha256((BASE / name).read_bytes()).hexdigest() == digest
                    for name, digest in preservation.items())
    report = {"identity_checks": identities, "boundary_checks": boundaries,
              "old_witness_rejection": old_witnesses,
              "zero_example_admissible": zero_diagnostics["admissible"] and zero_diagnostics["rdm_dad"] == 0,
              "claimed_dad_rejected": forged_report["passed"] is False and forged_report["reason"].startswith("invalid_artifact"),
              "only_added_bound": unchanged == original_limits and added == 0.001,
              "private_public_constraints_identical": private_limits == CONSTRAINTS,
              "historical_files_preserved": preserved, "public_oracle_sanity": validate(),
              "independent_numerics": numerical_audit(), "security": parser_audit(OUTPUT),
              "runtime_seconds": time.monotonic() - started}
    report["passed"] = (all(row["passed"] for row in identities + boundaries + old_witnesses)
                        and report["zero_example_admissible"] and report["claimed_dad_rejected"]
                        and report["only_added_bound"] and report["private_public_constraints_identical"]
                        and report["historical_files_preserved"] and report["public_oracle_sanity"]["passed"]
                        and report["independent_numerics"]["passed"] and report["security"]["passed"])
    (OUTPUT / "dad_audit.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({"passed": report["passed"], "dad_identity_count": len(identities),
                      "security_cases": report["security"]["case_count"],
                      "only_added_bound": report["only_added_bound"],
                      "historical_files_preserved": report["historical_files_preserved"],
                      "runtime_seconds": report["runtime_seconds"]}, indent=2), flush=True)
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
