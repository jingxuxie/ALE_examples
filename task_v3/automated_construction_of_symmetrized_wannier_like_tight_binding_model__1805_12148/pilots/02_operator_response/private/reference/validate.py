import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time

import numpy as np

from oracle import PILOT, solve_case
from independent_checks import check_case


specification = importlib.util.spec_from_file_location("pilot02_evaluator", PILOT / "private/evaluator.py")
evaluator = importlib.util.module_from_spec(specification)
specification.loader.exec_module(evaluator)
sys.path.insert(0, str(PILOT / "participant/workspace"))
from atomic_h import energies


def hermiticity(payload, name):
    lookup = {tuple(vector): index for index, vector in enumerate(payload["rvec"])}
    maximum = 0.0
    for index, vector in enumerate(payload["rvec"]):
        partner = lookup.get(tuple(-vector))
        if partner is None:
            maximum = max(maximum, float(np.max(np.abs(payload[name][index]))))
        else:
            reverse = payload[name][partner].swapaxes(0, 1).conj()
            maximum = max(maximum, float(np.max(np.abs(payload[name][index] - reverse))))
    return maximum


def invariants(record, expected):
    case_path = PILOT / record["input"]
    with np.load(case_path / "model.npz", allow_pickle=False) as archive:
        payload = {name: archive[name] for name in archive.files}
    optical = expected["optical_repaired"]
    gram = -1j * optical
    half_count = len(optical) // 2
    parity_sign = -1 if record["material"] == "Te" else 1
    berry = expected["berry_repaired"]
    result = {
        "ham_hermiticity_max": hermiticity(expected, "ham"),
        "connection_storage_adjoint_residual": hermiticity(expected, "connection"),
        "independent_raw_energy_relative_error": evaluator.relative_error(energies(payload), expected["energies"]),
        "optical_antihermiticity_max": float(np.max(np.abs(optical + optical.swapaxes(1, 2).conj()))),
        "optical_gram_min_eigenvalue": float(np.min(np.linalg.eigvalsh(gram))),
        "repaired_berry_momentum_parity_relative_error": evaluator.relative_error(berry[half_count:], parity_sign * berry[:half_count]),
    }
    assert result["ham_hermiticity_max"] < 2e-7, result
    assert result["independent_raw_energy_relative_error"] < 1e-10, result
    assert result["optical_antihermiticity_max"] < 1e-7, result
    assert result["optical_gram_min_eigenvalue"] > -1e-7, result
    assert result["repaired_berry_momentum_parity_relative_error"] < 5e-5, result
    return result


def score_contract_checks(expected, weak):
    perfect = evaluator.score_arrays(expected, expected, weak)["score"]
    baseline = evaluator.score_arrays(weak, expected, weak)["score"]
    intermediate = dict(expected)
    for name in ["berry_raw", "optical_raw", "berry_repaired", "optical_repaired"]:
        intermediate[name] = expected[name] * 0.5
    partial = evaluator.score_arrays(intermediate, expected, weak)["score"]
    shuffled = dict(expected)
    shuffled["rvec"] = expected["rvec"][::-1]
    for name in ["ham", "connection"]:
        shuffled[name] = expected[name][::-1]
    order_invariant = evaluator.score_arrays(shuffled, expected, weak)["score"]
    missing = dict(expected)
    missing.pop("berry_raw")
    missing_score = evaluator.score_arrays(missing, expected, weak)["score"]
    duplicate = dict(expected)
    duplicate["rvec"] = expected["rvec"].copy()
    duplicate["rvec"][0] = duplicate["rvec"][1]
    duplicate_result = evaluator.score_arrays(duplicate, expected, weak)
    assert perfect == order_invariant == 1.0
    assert 0 < baseline < 1 and 0 < partial < 1 and 0 < missing_score < 1
    assert "ham" in duplicate_result["issues"] and "connection" in duplicate_result["issues"]
    return {"exact": perfect, "weak": baseline, "half_response": partial,
            "permuted_R": order_invariant, "missing_raw_berry": missing_score}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=PILOT / "private/reference/post_audit/validation.json")
    arguments = parser.parse_args()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((PILOT / "private/reference/manifest.json").read_text())
    reports = {}
    for split, records in manifest["splits"].items():
        started = time.monotonic()
        cases = []
        for record in records:
            expected = evaluator.load_npz(PILOT / record["reference"])
            weak = evaluator.load_npz(PILOT / record["weak_reference"])
            oracle_started = time.monotonic()
            reproduced = solve_case(PILOT / record["input"])
            result = evaluator.score_arrays(reproduced, expected, weak)
            result.update(name=record["name"], family=record["material"],
                          runtime={"seconds": time.monotonic() - oracle_started},
                          invariants=invariants(record, expected),
                          independent_finite_difference=check_case(PILOT / record["input"], expected),
                          score_contract=score_contract_checks(expected, weak))
            assert result["score"] > 0.9 and not result["issues"], result
            cases.append(result)
            print("VALIDATED", split, record["name"], result["score"], flush=True)
        reports[split] = evaluator.summarize(cases, split, time.monotonic() - started)
        arguments.output.write_text(json.dumps({"method": "reexecute pinned official physics on numeric case input; independent invariants and scorer checks", "splits": reports}, indent=2) + "\n")
    print("ALL REFERENCES VALIDATED", flush=True)


if __name__ == "__main__":
    main()
