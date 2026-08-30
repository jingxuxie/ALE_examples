"""Public determinant conventions, exact excitation rotations, and validation."""

import itertools
import json
import math
import os
from pathlib import Path
import stat
import time
from dataclasses import dataclass
from functools import lru_cache

import numpy as np


FIDELITY_THRESHOLD = 0.999999999
ANGLE_LIMIT = math.pi
MAX_OUTPUT_BYTES = 131072
NORM_TOLERANCE = 5e-12
DEFAULT_TARGETS = Path(__file__).resolve().parents[1] / "input" / "targets.json"


class ValidationError(ValueError):
    """Invalid input data, never a participant exception or executable object."""


@dataclass(frozen=True)
class Excitation:
    annihilate: tuple
    create: tuple


@dataclass(frozen=True)
class Case:
    case_id: str
    n_orbitals: int
    n_electrons: int
    n_alpha: int
    n_beta: int
    reference_mask: int
    max_gates: int
    determinants: tuple
    target: np.ndarray


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValidationError("nonfinite JSON constant")


def read_json(path, byte_limit=MAX_OUTPUT_BYTES):
    """Read bounded, regular, non-symlink UTF-8 JSON with unique object keys."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode):
            raise ValidationError("submission must be a regular file")
        if metadata.st_size > byte_limit:
            raise ValidationError("JSON exceeds byte limit")
        contents = stream.read(byte_limit + 1)
    if len(contents) > byte_limit:
        raise ValidationError("JSON exceeds byte limit")
    return json.loads(
        contents.decode("utf-8"),
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
    )


def _keys(value, expected, label):
    if type(value) is not dict or set(value) != set(expected):
        raise ValidationError(label + " has incorrect keys or type")


def _integer(value, label):
    if type(value) is not int:
        raise ValidationError(label + " must be an integer, not boolean")
    return value


def _finite_number(value, label):
    if type(value) not in (int, float):
        raise ValidationError(label + " must be a real number, not boolean")
    try:
        numeric = float(value)
    except (ValueError, OverflowError) as error:
        raise ValidationError(label + " is not finite") from error
    if not math.isfinite(numeric):
        raise ValidationError(label + " is not finite")
    return numeric


@lru_cache(maxsize=16)
def determinant_basis(n_orbitals, n_electrons):
    """Increasing integer masks, orbital zero at the least-significant bit."""
    return tuple(
        mask for mask in range(1 << n_orbitals)
        if mask.bit_count() == n_electrons
    )


def load_cases(path=DEFAULT_TARGETS):
    data = read_json(path, 1048576)
    _keys(data, ("schema_version", "fidelity_threshold", "cases"), "targets")
    if _integer(data["schema_version"], "schema_version") != 1:
        raise ValidationError("unsupported targets schema")
    if data["fidelity_threshold"] != FIDELITY_THRESHOLD:
        raise ValidationError("target threshold does not match frozen policy")
    if type(data["cases"]) is not list or len(data["cases"]) != 3:
        raise ValidationError("exactly three targets are required")
    cases = []
    identifiers = set()
    for specification in data["cases"]:
        _keys(specification, (
            "case_id", "n_orbitals", "n_electrons", "n_alpha", "n_beta",
            "reference_mask", "max_gates", "determinants", "target_amplitudes",
        ), "target case")
        identifier = specification["case_id"]
        if type(identifier) is not str or not identifier or identifier in identifiers:
            raise ValidationError("invalid or duplicate target identifier")
        identifiers.add(identifier)
        integers = {key: _integer(specification[key], key) for key in (
            "n_orbitals", "n_electrons", "n_alpha", "n_beta",
            "reference_mask", "max_gates",
        )}
        n_orbitals = integers["n_orbitals"]
        n_electrons = integers["n_electrons"]
        if n_orbitals not in (8, 10) or not 0 < n_electrons < n_orbitals:
            raise ValidationError("unsupported target sector")
        if not 0 < integers["max_gates"] <= 20:
            raise ValidationError("invalid target gate cap")
        if not all(0 <= integers[key] <= n_orbitals // 2 for key in ("n_alpha", "n_beta")):
            raise ValidationError("invalid spin counts")
        if integers["n_alpha"] + integers["n_beta"] != n_electrons:
            raise ValidationError("inconsistent spin counts")
        determinants = determinant_basis(n_orbitals, n_electrons)
        supplied_basis = specification["determinants"]
        if type(supplied_basis) is not list or any(type(mask) is not int for mask in supplied_basis):
            raise ValidationError("invalid determinant list")
        if tuple(supplied_basis) != determinants:
            raise ValidationError("target determinant basis is not canonical")
        reference = integers["reference_mask"]
        if reference not in determinants:
            raise ValidationError("reference is outside the number sector")
        alpha_mask = sum(1 << orbital for orbital in range(0, n_orbitals, 2))
        if (reference & alpha_mask).bit_count() != integers["n_alpha"]:
            raise ValidationError("reference is outside the spin sector")
        amplitudes = specification["target_amplitudes"]
        if type(amplitudes) is not list or len(amplitudes) != len(determinants):
            raise ValidationError("incorrect target dimension")
        target = np.array([_finite_number(value, "amplitude") for value in amplitudes])
        if abs(float(target @ target) - 1.0) > NORM_TOLERANCE:
            raise ValidationError("target is not normalized")
        for mask, amplitude in zip(determinants, target):
            if (mask & alpha_mask).bit_count() != integers["n_alpha"] and amplitude != 0.0:
                raise ValidationError("target leaks outside the spin sector")
        target.setflags(write=False)
        cases.append(Case(identifier, **integers, determinants=determinants, target=target))
    return tuple(cases)


def reference_state(case):
    state = np.zeros(len(case.determinants))
    state[case.determinants.index(case.reference_mask)] = 1.0
    return state


def allowed_excitations(n_orbitals):
    """Every canonical, disjoint, spin-preserving rank-one/rank-two excitor."""
    result = []
    for rank in (1, 2):
        groups = list(itertools.combinations(range(n_orbitals), rank))
        for annihilate, create in itertools.combinations(groups, 2):
            if set(annihilate).isdisjoint(create) and sorted(
                orbital % 2 for orbital in annihilate
            ) == sorted(orbital % 2 for orbital in create):
                result.append(Excitation(annihilate, create))
    return tuple(result)


def _excited_mask(mask, excitation):
    sign = 1
    for orbital in excitation.annihilate:
        if not (mask >> orbital) & 1:
            return None
        if (mask & ((1 << orbital) - 1)).bit_count() % 2:
            sign = -sign
        mask ^= 1 << orbital
    for orbital in reversed(excitation.create):
        if (mask >> orbital) & 1:
            return None
        if (mask & ((1 << orbital) - 1)).bit_count() % 2:
            sign = -sign
        mask ^= 1 << orbital
    return mask, sign


@lru_cache(maxsize=4096)
def rotation_pairs(n_orbitals, n_electrons, excitation):
    """Return disjoint (source, destination, fermion sign) array triples."""
    determinants = determinant_basis(n_orbitals, n_electrons)
    positions = {mask: index for index, mask in enumerate(determinants)}
    sources, destinations, signs = [], [], []
    for index, mask in enumerate(determinants):
        transformed = _excited_mask(mask, excitation)
        if transformed is not None:
            destination, sign = transformed
            sources.append(index)
            destinations.append(positions[destination])
            signs.append(sign)
    arrays = (
        np.array(sources, dtype=np.intp),
        np.array(destinations, dtype=np.intp),
        np.array(signs, dtype=np.float64),
    )
    for array in arrays:
        array.setflags(write=False)
    return arrays


def apply_rotation(state, pairs, theta):
    """Return exp(theta*(E-E†)) state, without modifying state."""
    sources, destinations, signs = pairs
    cosine, sine = math.cos(theta), math.sin(theta)
    result = state.copy()
    result[sources] = cosine * state[sources] - signs * sine * state[destinations]
    result[destinations] = signs * sine * state[sources] + cosine * state[destinations]
    return result


def apply_generator(state, pairs):
    sources, destinations, signs = pairs
    result = np.zeros_like(state)
    result[sources] = -signs * state[destinations]
    result[destinations] = signs * state[sources]
    return result


def circuit_state(case, gates):
    """Apply a sequence of (Excitation, theta) pairs, first-listed first."""
    state = reference_state(case)
    for excitation, theta in gates:
        state = apply_rotation(
            state, rotation_pairs(case.n_orbitals, case.n_electrons, excitation), theta,
        )
    return state


def squared_overlap(target, state):
    numerator = float(abs(np.vdot(target, state)) ** 2)
    denominator = float(np.vdot(target, target).real * np.vdot(state, state).real)
    if not math.isfinite(numerator) or not math.isfinite(denominator) or denominator <= 0:
        raise ValidationError("nonfinite or zero state norm")
    return min(1.0, max(0.0, numerator / denominator))


def validate_submission(submission, cases):
    _keys(submission, ("schema_version", "circuits"), "submission")
    if _integer(submission["schema_version"], "schema_version") != 1:
        raise ValidationError("unsupported submission schema")
    circuits = submission["circuits"]
    if type(circuits) is not list or len(circuits) != len(cases):
        raise ValidationError("include every case exactly once")
    lookup = {case.case_id: case for case in cases}
    parsed = {}
    for circuit in circuits:
        _keys(circuit, ("case_id", "gates"), "circuit")
        identifier = circuit["case_id"]
        if type(identifier) is not str or identifier not in lookup or identifier in parsed:
            raise ValidationError("unknown or duplicate case_id")
        case = lookup[identifier]
        gates = circuit["gates"]
        if type(gates) is not list or len(gates) > case.max_gates:
            raise ValidationError(identifier + ": invalid gates list or gate budget exceeded")
        parsed_gates = []
        for gate in gates:
            _keys(gate, ("annihilate", "create", "theta"), "gate")
            annihilate, create = gate["annihilate"], gate["create"]
            if type(annihilate) is not list or type(create) is not list:
                raise ValidationError("orbital groups must be lists")
            if len(annihilate) not in (1, 2) or len(create) != len(annihilate):
                raise ValidationError("only singles and doubles are allowed")
            for group in (annihilate, create):
                if any(type(orbital) is not int or not 0 <= orbital < case.n_orbitals for orbital in group):
                    raise ValidationError("orbital index out of range or not integer")
                if sorted(set(group)) != group:
                    raise ValidationError("orbital groups must be strictly increasing")
            if not set(annihilate).isdisjoint(create):
                raise ValidationError("annihilate/create groups must be disjoint")
            if tuple(annihilate) >= tuple(create):
                raise ValidationError("noncanonical excitation orientation")
            if sorted(orbital % 2 for orbital in annihilate) != sorted(orbital % 2 for orbital in create):
                raise ValidationError("excitation must preserve both spin counts")
            theta = _finite_number(gate["theta"], "theta")
            if abs(theta) > ANGLE_LIMIT:
                raise ValidationError("theta outside [-pi, pi]")
            parsed_gates.append((Excitation(tuple(annihilate), tuple(create)), theta))
        parsed[identifier] = tuple(parsed_gates)
    if set(parsed) != set(lookup):
        raise ValidationError("missing target case")
    return parsed


def failure_report(reason, runtime_seconds=0.0):
    return {
        "core": 0.0, "worst_fidelity": 0.0, "pass": False,
        "reason": reason, "runtime_seconds": runtime_seconds,
        "fidelity_threshold": FIDELITY_THRESHOLD, "cases": [],
    }


def evaluate_path(submission_path, targets_path=DEFAULT_TARGETS):
    started = time.perf_counter()
    try:
        cases = load_cases(targets_path)
        parsed = validate_submission(read_json(submission_path), cases)
        results = []
        for case in cases:
            state = circuit_state(case, parsed[case.case_id])
            norm_squared = float(np.vdot(state, state).real)
            if not np.isfinite(state).all() or abs(norm_squared - 1.0) > NORM_TOLERANCE:
                raise ValidationError("nonfinite state or norm drift")
            fidelity = squared_overlap(case.target, state)
            results.append({
                "case_id": case.case_id, "fidelity": fidelity,
                "infidelity": max(0.0, 1.0 - fidelity),
                "gate_count": len(parsed[case.case_id]), "max_gates": case.max_gates,
                "state_norm_squared": norm_squared, "pass": fidelity >= FIDELITY_THRESHOLD,
            })
        worst = min(result["fidelity"] for result in results)
        passed = all(result["pass"] for result in results)
        report = {
            "core": worst, "worst_fidelity": worst, "pass": passed,
            "reason": "ok" if passed else "fidelity below threshold: " + ", ".join(
                result["case_id"] for result in results if not result["pass"]
            ),
            "fidelity_threshold": FIDELITY_THRESHOLD, "cases": results,
        }
    except (OSError, ValueError, TypeError, OverflowError, RecursionError) as error:
        report = failure_report("invalid input: " + type(error).__name__ + ": " + str(error)[:240])
    report["runtime_seconds"] = time.perf_counter() - started
    return report
