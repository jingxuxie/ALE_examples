import json
import math
import os
from pathlib import Path
import stat

import numpy as np
from scipy.special import expit, logsumexp


class InvalidWitness(ValueError):
    pass


def enumerate_spins(count):
    identifiers = np.arange(1 << count, dtype=np.uint32)
    positions = np.arange(count, dtype=np.uint32)
    return (2 * ((identifiers[:, None] >> positions) & 1).astype(np.int8) - 1).astype(np.float64)


def torus_edges(side=4):
    edges = []
    for row in range(side):
        for column in range(side):
            site = side * row + column
            edges.append((site, side * row + (column + 1) % side))
            edges.append((site, side * ((row + 1) % side) + column))
    return edges


def frustrated_plaquettes(bonds, side=4):
    signs = []
    for row in range(side):
        for column in range(side):
            site = side * row + column
            right = side * row + (column + 1) % side
            down = side * ((row + 1) % side) + column
            signs.append(bonds[2 * site] * bonds[2 * right + 1] * bonds[2 * down] * bonds[2 * site + 1])
    return int(sum(value == -1 for value in signs))


def reject_constant(value):
    raise InvalidWitness("non-finite JSON constant: " + value)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidWitness("duplicate JSON key: " + key)
        result[key] = value
    return result


def read_witness(directory, spec):
    path = Path(directory) / "witness.json"
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as error:
        raise InvalidWitness("cannot open regular witness.json: " + str(error)) from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise InvalidWitness("witness.json must be a regular file")
        if metadata.st_size > spec["maximum_json_bytes"]:
            raise InvalidWitness("witness.json exceeds byte limit")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            content = handle.read(spec["maximum_json_bytes"] + 1)
        if len(content) > spec["maximum_json_bytes"]:
            raise InvalidWitness("witness.json exceeds byte limit")
        document = json.loads(content.decode("utf-8"), object_pairs_hook=unique_object, parse_constant=reject_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise InvalidWitness("malformed JSON: " + str(error)) from error
    finally:
        os.close(descriptor)
    return document, content


def finite_number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def validate_witness(document, spec):
    keys = {"schema_version", "bonds", "beta", "order", "weights", "pattern", "radius"}
    if type(document) is not dict or set(document) != keys:
        raise InvalidWitness("object must have exactly the seven documented keys")
    if type(document["schema_version"]) is not int or document["schema_version"] != spec["schema_version"]:
        raise InvalidWitness("schema_version must be integer 1")
    count = spec["n"]
    bonds = document["bonds"]
    if type(bonds) is not list or len(bonds) != 2 * count or any(type(value) is not int or value not in (-1, 1) for value in bonds):
        raise InvalidWitness("bonds must be 32 integer signs")
    beta = document["beta"]
    if not finite_number(beta) or not spec["beta_min"] <= beta <= spec["beta_max"]:
        raise InvalidWitness("beta must be finite and in [1,3]")
    order = document["order"]
    if type(order) is not list or len(order) != count or any(type(value) is not int for value in order) or sorted(order) != list(range(count)):
        raise InvalidWitness("order must be a permutation of integers 0..15")
    pattern = document["pattern"]
    if type(pattern) is not list or len(pattern) != count or any(type(value) is not int or value not in (-1, 1) for value in pattern):
        raise InvalidWitness("pattern must be 16 integer signs")
    radius = document["radius"]
    if type(radius) is not int or radius not in spec["allowed_radii"]:
        raise InvalidWitness("radius must be integer 2, 3, or 4")
    weights = document["weights"]
    if type(weights) is not list or len(weights) != count:
        raise InvalidWitness("weights must have 16 rows")
    row_norms = []
    for position, row in enumerate(weights):
        if type(row) is not list or len(row) != count or any(not finite_number(value) for value in row):
            raise InvalidWitness("every weight row must contain 16 finite numbers")
        if any(value != 0 for value in row[position:]):
            raise InvalidWitness("diagonal and upper-triangular weights must be exactly zero")
        try:
            norm = math.fsum(abs(value) for value in row)
        except OverflowError as error:
            raise InvalidWitness("weight row norm overflow") from error
        if norm > math.log(99):
            raise InvalidWitness("weight row L1 exceeds ln(99)")
        row_norms.append(norm)
    frustrated = frustrated_plaquettes(bonds)
    if not spec["frustrated_min"] <= frustrated <= spec["frustrated_max"]:
        raise InvalidWitness("frustrated plaquette count is outside [4,12]")
    return {"frustrated_plaquettes": frustrated, "maximum_row_l1": max(row_norms), "row_l1": row_norms}


def exact_statistics(spins, dimensionless_energy, weights, order, pattern, radius):
    count = spins.shape[1]
    ordered = spins[:, order]
    logits = ordered @ weights.T
    log_proposal = -np.logaddexp(0.0, -ordered * logits).sum(axis=1)
    proposal = np.exp(log_proposal)
    log_partition = float(logsumexp(-dimensionless_energy))
    log_target = -dimensionless_energy - log_partition
    target = np.exp(log_target)
    reward = dimensionless_energy + log_proposal
    mean_reward = float(proposal @ reward)
    centered = reward - mean_reward
    residuals = (ordered + 1.0) / 2.0 - expit(logits)
    gradient = np.tril((residuals * (proposal * centered)[:, None]).T @ ordered, -1)
    distance = np.count_nonzero(spins != np.asarray(pattern), axis=1)
    sector = np.minimum(distance, count - distance) <= radius
    entropy = float(-proposal @ log_proposal)
    mean_energy_proposal = float(proposal @ dimensionless_energy)
    mean_energy_target = float(target @ dimensionless_energy)
    metrics = {
        "entropy": entropy,
        "reverse_kl": float(proposal @ (log_proposal - log_target)),
        "reward_variance": float(proposal @ np.square(centered)),
        "gradient_infinity": float(np.max(np.abs(gradient))),
        "energy_error_per_spin": abs(mean_energy_proposal - mean_energy_target) / count,
        "target_sector_mass": float(target[sector].sum()),
        "proposal_sector_mass": float(proposal[sector].sum()),
        "mean_dimensionless_energy_proposal": mean_energy_proposal,
        "mean_dimensionless_energy_target": mean_energy_target,
        "mean_reward": mean_reward,
        "log_partition": log_partition,
        "proposal_normalization_error": abs(float(proposal.sum()) - 1.0),
        "target_normalization_error": abs(float(target.sum()) - 1.0),
        "proposal_symmetry_error": float(np.max(np.abs(proposal - proposal[::-1]))),
        "target_symmetry_error": float(np.max(np.abs(target - target[::-1]))),
        "minimum_log_proposal": float(log_proposal.min()),
        "minimum_binary_conditional": float(expit(-np.abs(logits)).min()),
    }
    if not all(math.isfinite(value) for value in metrics.values()) or not np.isfinite(gradient).all():
        raise ArithmeticError("non-finite exact calculation")
    return metrics, gradient


def gate_report(metrics, spec):
    gates = {
        "entropy": ("min", "entropy_min"),
        "reverse_kl": ("min", "reverse_kl_min"),
        "reward_variance": ("max", "reward_variance_max"),
        "gradient_infinity": ("max", "gradient_infinity_max"),
        "energy_error_per_spin": ("max", "energy_error_per_spin_max"),
        "target_sector_mass": ("min", "target_sector_mass_min"),
        "proposal_sector_mass": ("max", "proposal_sector_mass_max"),
    }
    results = {}
    tolerance = spec["metric_absolute_tolerance"]
    for name, (direction, key) in gates.items():
        measured = metrics[name]
        threshold = spec[key]
        if direction == "min":
            passed = measured >= threshold - tolerance
            score = max(0.0, min(1.0, measured / threshold))
        else:
            passed = measured <= threshold + tolerance
            score = 1.0 if measured <= 0.0 else min(1.0, threshold / measured)
        results[name] = {"measured": measured, "direction": direction, "threshold": threshold, "passed": bool(passed), "score": float(score)}
    failing = [name for name, result in results.items() if not result["passed"]]
    worst = min(results, key=lambda name: results[name]["score"])
    score = results[worst]["score"]
    return {"gates": results, "failing_gates": failing, "worst_gate": worst,
            "core_score": score, "worst_score": score, "worst_family_score": score,
            "passed": not failing, "reason": "all frozen gates satisfied" if not failing else "failed gates: " + ", ".join(failing)}


def evaluate_document(document, spec):
    validation = validate_witness(document, spec)
    spins = enumerate_spins(spec["n"])
    edges = torus_edges(spec["lattice_side"])
    features = np.column_stack([spins[:, first] * spins[:, second] for first, second in edges])
    energy = -document["beta"] * (features @ np.asarray(document["bonds"], dtype=np.float64))
    metrics, gradient = exact_statistics(spins, energy, np.asarray(document["weights"], dtype=np.float64), document["order"], document["pattern"], document["radius"])
    for name in ("proposal_normalization_error", "target_normalization_error"):
        if metrics[name] > spec["normalization_absolute_tolerance"]:
            raise ArithmeticError(name + " exceeded tolerance")
    for name in ("proposal_symmetry_error", "target_symmetry_error"):
        if metrics[name] > spec["symmetry_absolute_tolerance"]:
            raise ArithmeticError(name + " exceeded tolerance")
    result = gate_report(metrics, spec)
    result.update(valid=True, evaluator_valid=True, metrics=metrics, gradient=gradient.tolist(), validation=validation)
    return result
