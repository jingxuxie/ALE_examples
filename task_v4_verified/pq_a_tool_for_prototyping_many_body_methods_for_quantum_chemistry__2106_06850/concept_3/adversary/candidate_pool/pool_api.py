"""Private pool-only adapter; never changes or imports active participant files."""

import argparse
import itertools
import json
import math
from pathlib import Path
import subprocess
import sys
import time
from functools import lru_cache

sys.dont_write_bytecode = True

import numpy as np

import base_engine as engine


ROOT = Path(__file__).resolve().parent
SUPPORT_TOLERANCE = 1e-10
RANK_TOLERANCE = 1e-8
MINIMUM_AMPLITUDE = 1e-6
MINIMUM_SCHMIDT_VALUE = 1e-4
MINIMUM_EFFECTIVE_RANK_FRACTION = 0.55
MINIMUM_LATE_SPECTRUM_CHANGE = 0.006


def save_assets(files, replace=False):
    patch = "*** Begin Patch\n"
    for relative, data in files.items():
        path = ROOT / relative
        if not path.resolve().is_relative_to(ROOT):
            raise ValueError("pool writes cannot leave candidate_pool")
        content = data if isinstance(data, str) else json.dumps(data, indent=2, allow_nan=False) + "\n"
        if path.exists():
            if not replace:
                raise FileExistsError("refusing to replace existing pool asset: " + relative)
            old = path.read_text(encoding="utf-8")
            patch += "*** Update File: " + str(path) + "\n@@\n"
            patch += "".join("-" + line + "\n" for line in old.splitlines())
        else:
            patch += "*** Add File: " + str(path) + "\n"
        patch += "".join("+" + line + "\n" for line in content.splitlines())
    patch += "*** End Patch\n"
    subprocess.run(["apply_patch"], input=patch, text=True, check=True, capture_output=True)


def load_cases(path):
    data = engine.read_json(path, 16 * 1024 * 1024)
    engine._keys(data, ("schema_version", "fidelity_threshold", "cases"), "pool targets")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise engine.ValidationError("unsupported schema")
    if data["fidelity_threshold"] != engine.FIDELITY_THRESHOLD:
        raise engine.ValidationError("fidelity threshold must match the active policy")
    if type(data["cases"]) is not list or not 1 <= len(data["cases"]) <= 32:
        raise engine.ValidationError("pool requires 1 to 32 cases")
    cases, identifiers = [], set()
    for specification in data["cases"]:
        engine._keys(specification, (
            "case_id", "n_orbitals", "n_electrons", "n_alpha", "n_beta", "reference_mask",
            "max_gates", "determinants", "target_amplitudes",
        ), "case")
        identifier = specification["case_id"]
        if type(identifier) is not str or not identifier or identifier in identifiers:
            raise engine.ValidationError("invalid case identifier")
        identifiers.add(identifier)
        integers = {name: engine._integer(specification[name], name) for name in (
            "n_orbitals", "n_electrons", "n_alpha", "n_beta", "reference_mask", "max_gates",
        )}
        sector = integers["n_orbitals"], integers["n_electrons"]
        permitted_depths = {(10, 4): (24, 28, 32), (10, 6): (24, 28, 32), (12, 6): (28, 32)}
        if sector not in permitted_depths or integers["max_gates"] not in permitted_depths[sector]:
            raise engine.ValidationError("unsupported pool sector or depth")
        if integers["n_alpha"] != integers["n_beta"] or 2 * integers["n_alpha"] != integers["n_electrons"]:
            raise engine.ValidationError("invalid fixed spin sector")
        if integers["reference_mask"] != (1 << integers["n_electrons"]) - 1:
            raise engine.ValidationError("incorrect pool reference determinant")
        basis = engine.determinant_basis(*sector)
        supplied = specification["determinants"]
        if type(supplied) is not list or any(type(mask) is not int for mask in supplied) or tuple(supplied) != basis:
            raise engine.ValidationError("incorrect full fixed-N basis")
        supplied = specification["target_amplitudes"]
        if type(supplied) is not list or len(supplied) != len(basis):
            raise engine.ValidationError("incorrect target dimension")
        target = np.array([engine._finite_number(value, "amplitude") for value in supplied])
        if abs(float(target @ target) - 1.0) > engine.NORM_TOLERANCE:
            raise engine.ValidationError("target normalization failure")
        alpha_mask = sum(1 << orbital for orbital in range(0, integers["n_orbitals"], 2))
        if any(value != 0.0 and (mask & alpha_mask).bit_count() != integers["n_alpha"] for mask, value in zip(basis, target)):
            raise engine.ValidationError("target spin-sector leakage")
        target.setflags(write=False)
        cases.append(engine.Case(identifier, **integers, determinants=basis, target=target))
    return tuple(cases)


@lru_cache(maxsize=4)
def spin_layout(n_orbitals, n_electrons):
    half_orbitals, half_electrons = n_orbitals // 2, n_electrons // 2
    configurations = tuple(mask for mask in range(1 << half_orbitals) if mask.bit_count() == half_electrons)
    positions = {mask: index for index, mask in enumerate(configurations)}
    indices, rows, columns, signs = [], [], [], []
    for index, mask in enumerate(engine.determinant_basis(n_orbitals, n_electrons)):
        alpha = sum(((mask >> (2 * site)) & 1) << site for site in range(half_orbitals))
        beta = sum(((mask >> (2 * site + 1)) & 1) << site for site in range(half_orbitals))
        if alpha not in positions or beta not in positions:
            continue
        inversions = sum(
            (beta & ((1 << site) - 1)).bit_count()
            for site in range(half_orbitals) if (alpha >> site) & 1
        )
        indices.append(index)
        rows.append(positions[alpha])
        columns.append(positions[beta])
        signs.append(-1.0 if inversions % 2 else 1.0)
    return tuple(np.asarray(values) for values in (indices, rows, columns, signs)) + (len(configurations),)


def metrics(state, n_orbitals, n_electrons):
    indices, rows, columns, signs, dimension = spin_layout(n_orbitals, n_electrons)
    coefficients = state[indices]
    matrix = np.zeros((dimension, dimension))
    matrix[rows, columns] = signs * coefficients
    singular_values = np.linalg.svd(matrix, compute_uv=False)
    probabilities = singular_values ** 2
    probabilities /= probabilities.sum()
    positive = probabilities[probabilities > 0]
    entropy = float(-np.sum(positive * np.log(positive)))
    return {
        "spin_sector_dimension": int(len(indices)), "schmidt_dimension": dimension,
        "support": int(np.count_nonzero(np.abs(coefficients) > SUPPORT_TOLERANCE)),
        "support_above_1e-8": int(np.count_nonzero(np.abs(coefficients) > 1e-8)),
        "minimum_absolute_amplitude": float(np.min(np.abs(coefficients))),
        "schmidt_rank": int(np.count_nonzero(singular_values > RANK_TOLERANCE)),
        "minimum_schmidt_value": float(singular_values[-1]),
        "schmidt_values": singular_values.tolist(), "entropy_nats": entropy,
        "effective_schmidt_rank": math.exp(entropy),
        "participation_ratio": float(1.0 / np.sum(coefficients ** 4)),
    }


def dense_entangled(diagnostics):
    return (
        diagnostics["support"] == diagnostics["spin_sector_dimension"]
        and diagnostics["schmidt_rank"] == diagnostics["schmidt_dimension"]
        and diagnostics["minimum_absolute_amplitude"] >= MINIMUM_AMPLITUDE
        and diagnostics["minimum_schmidt_value"] >= MINIMUM_SCHMIDT_VALUE
        and diagnostics["effective_schmidt_rank"] >= MINIMUM_EFFECTIVE_RANK_FRACTION * diagnostics["schmidt_dimension"]
    )


def opposite_spin_double(excitation):
    return len(excitation.annihilate) == 2 and sum(orbital % 2 for orbital in excitation.annihilate) == 1


def evaluate(submission_path, targets_path=ROOT / "targets.json"):
    started = time.perf_counter()
    try:
        cases = load_cases(targets_path)
        parsed = engine.validate_submission(engine.read_json(submission_path), cases)
        results = []
        for case in cases:
            state = engine.circuit_state(case, parsed[case.case_id])
            if not np.isfinite(state).all() or abs(float(state @ state) - 1.0) > engine.NORM_TOLERANCE:
                raise engine.ValidationError("invalid simulated state")
            fidelity = engine.squared_overlap(case.target, state)
            results.append({"case_id": case.case_id, "fidelity": fidelity,
                            "gate_count": len(parsed[case.case_id]), "max_gates": case.max_gates,
                            "pass": fidelity >= engine.FIDELITY_THRESHOLD})
        worst = min(result["fidelity"] for result in results)
        passed = all(result["pass"] for result in results)
        report = {"core": worst, "worst_fidelity": worst, "pass": passed,
                  "reason": "ok" if passed else "fidelity below unchanged threshold", "cases": results,
                  "fidelity_threshold": engine.FIDELITY_THRESHOLD}
    except (OSError, ValueError, TypeError, OverflowError, RecursionError) as error:
        report = engine.failure_report("invalid pool submission: " + str(error)[:240])
    report["runtime_seconds"] = time.perf_counter() - started
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", required=True)
    parser.add_argument("--targets", default=str(ROOT / "targets.json"))
    arguments = parser.parse_args()
    report = evaluate(arguments.submission, arguments.targets)
    print(json.dumps(report, indent=2, allow_nan=False))
    raise SystemExit(0 if report["pass"] else 1)
