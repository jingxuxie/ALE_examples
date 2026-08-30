"""Private independent-draw audit of scalar inversion; never reads release labels."""

import hashlib
import json
import secrets
import sys
import time
from datetime import datetime, timezone
from functools import lru_cache
from itertools import combinations, product
from pathlib import Path

import numpy as np
from scipy.linalg import eigh
from scipy.optimize import brentq
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/input/workspace"))
from generator import (FAMILIES, Hamiltonian, PAIR_INDEX, TRIPLE_INDEX, accepted_sample,
                       basis, ground, label, low_order_features, matrix)


def protected_hashes():
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for directory in ("participant", "evaluator")
            for path in sorted((ROOT / directory).rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts}


def public_skeleton(features):
    n_pairs, n_virtual = int(features["n_pairs"]), int(features["n_virtual"])
    size = n_pairs + n_virtual
    return Hamiltonian(n_pairs, n_virtual, int(features["family"]),
                       features["onsite"][:size].copy(), features["density"][:size, :size].copy(),
                       np.zeros((size, size)), features["occupied_profile"][:n_pairs].copy(),
                       features["positions"][:n_virtual].copy(), features["groups"][:n_virtual].copy())


def curve(base, direction, magnitude):
    energies, vectors = eigh(base + magnitude * direction, subset_by_index=(0, 0),
                             check_finite=False, driver="evr")
    vector = vectors[:, 0]
    return float(energies[0]), float(vector @ direction @ vector)


def bracket_root(function, lower, upper):
    if abs(function(lower)) <= 2e-13:
        return lower
    if abs(function(upper)) <= 2e-13:
        return upper
    return float(brentq(function, lower, upper, xtol=2e-13, rtol=1e-14))


@lru_cache(maxsize=None)
def virtual_edge_direction(n_pairs):
    occupancy, edges = basis(n_pairs + 2, n_pairs)
    rows, columns, sources, destinations = edges
    mask = (((sources == n_pairs) & (destinations == n_pairs + 1)) |
            ((sources == n_pairs + 1) & (destinations == n_pairs)))
    direction = np.zeros((len(occupancy), len(occupancy)))
    direction[rows[mask], columns[mask]] = 1.0
    direction[columns[mask], rows[mask]] = 1.0
    return direction


def pair_roots(base, direction, target):
    lower, upper = .012, .28
    lower_energy, lower_slope = curve(base, direction, lower)
    upper_energy, upper_slope = curve(base, direction, upper)
    if lower_slope < upper_slope - 1e-10:
        raise AssertionError("Ground-energy concavity check failed")
    turning = None
    intervals = [(lower, upper)]
    if lower_slope > 0 and upper_slope < 0:
        turning = float(brentq(lambda magnitude: curve(base, direction, magnitude)[1],
                              lower, upper, xtol=2e-13))
        intervals = [(lower, turning), (turning, upper)]
    roots = []
    for start, finish in intervals:
        function = lambda magnitude: curve(base, direction, magnitude)[0] - target
        start_value, finish_value = function(start), function(finish)
        if abs(start_value) <= 2e-13:
            roots.append(start)
        if abs(finish_value) <= 2e-13:
            roots.append(finish)
        if start_value * finish_value < 0:
            roots.append(bracket_root(function, start, finish))
    distinct = []
    for root in sorted(roots):
        if not distinct or abs(root - distinct[-1]) > 1e-8:
            distinct.append(float(root))
    if not distinct:
        raise AssertionError("No pair root inside declared support")
    return distinct, {"lower_slope": lower_slope, "upper_slope": upper_slope,
                      "turning_point": turning}


def select_by_triples(model, features, candidates, signs):
    domains = {edge: set(range(len(values))) for edge, values in candidates.items()}
    ambiguous = {edge for edge, domain in domains.items() if len(domain) > 1}
    constraints, separation = [], []
    triple_evaluations = 0
    for index, triple in enumerate(TRIPLE_INDEX):
        if triple[-1] >= model.n_virtual:
            continue
        edges = tuple(combinations(tuple(int(value) for value in triple), 2))
        if not (set(edges) & ambiguous):
            continue
        target = features["reference_energy"] + features["cas3"][index]
        allowed = []
        for choices in product(*(sorted(domains[edge]) for edge in edges)):
            for edge, choice in zip(edges, choices):
                first, second = (model.n_pairs + value for value in edge)
                model.hopping[first, second] = signs[edge] * candidates[edge][choice]
                model.hopping[second, first] = model.hopping[first, second]
            error = abs(ground(model, tuple(int(value) for value in triple)) - target)
            triple_evaluations += 1
            if error <= 1e-10:
                allowed.append(choices)
            else:
                separation.append(error)
        if not allowed:
            raise AssertionError("No triple-compatible branch assignment")
        constraints.append((edges, allowed))
    passes = 0
    changed = True
    while changed:
        changed = False
        passes += 1
        for edges, allowed in constraints:
            compatible = [choices for choices in allowed if
                          all(choice in domains[edge] for edge, choice in zip(edges, choices))]
            if not compatible:
                raise AssertionError("Empty branch domain during local propagation")
            for position, edge in enumerate(edges):
                remaining = domains[edge] & {choices[position] for choices in compatible}
                if remaining != domains[edge]:
                    domains[edge] = remaining
                    changed = True
    unresolved = sum(len(domain) > 1 for domain in domains.values())
    for edge, domain in domains.items():
        first, second = (model.n_pairs + value for value in edge)
        model.hopping[first, second] = signs[edge] * candidates[edge][min(domain)]
        model.hopping[second, first] = model.hopping[first, second]
    return {"raw_branch_assignments": 2 ** len(ambiguous), "unresolved_after_local_propagation": unresolved,
            "triple_constraint_count": len(constraints), "triple_evaluations": triple_evaluations,
            "propagation_passes": passes, "global_branch_search_performed": False,
            "minimum_rejected_triple_energy_difference": min(separation) if separation else None}


def audit_model(source, features, truth):
    started = time.perf_counter()
    inferred = public_skeleton(features)
    source_amplitudes = []
    for virtual in range(inferred.n_virtual):
        orbital = inferred.n_pairs + virtual
        base = matrix(inferred, (virtual,))
        inferred.hopping[:inferred.n_pairs, orbital] = -inferred.occupied_profile
        inferred.hopping[orbital, :inferred.n_pairs] = -inferred.occupied_profile
        direction = matrix(inferred, (virtual,)) - base
        target = features["reference_energy"] + features["cas1"][virtual]
        amplitude = bracket_root(lambda value: curve(base, direction, value)[0] - target, .07, .30)
        source_amplitudes.append(amplitude)
        inferred.hopping[:inferred.n_pairs, orbital] = -inferred.occupied_profile * amplitude
        inferred.hopping[orbital, :inferred.n_pairs] = inferred.hopping[:inferred.n_pairs, orbital]
    candidates, signs, curves = {}, {}, []
    for index, pair in enumerate(PAIR_INDEX):
        if pair[-1] >= inferred.n_virtual:
            continue
        edge = tuple(int(value) for value in pair)
        sign = float(features["pair_sign"][index])
        target = features["reference_energy"] + features["cas2"][index]
        roots, diagnostic = pair_roots(matrix(inferred, edge),
                                       sign * virtual_edge_direction(inferred.n_pairs), target)
        candidates[edge], signs[edge] = roots, sign
        first, second = (inferred.n_pairs + value for value in edge)
        inferred.hopping[first, second] = sign * roots[0]
        inferred.hopping[second, first] = sign * roots[0]
        curves.append({"edge": list(edge), "sign": int(sign), "roots": roots, **diagnostic})
    ambiguous = [row for row in curves if len(row["roots"]) > 1]
    branch_report = select_by_triples(inferred, features, candidates, signs) if ambiguous else {
        "raw_branch_assignments": 1, "unresolved_after_local_propagation": 0,
        "triple_constraint_count": 0, "triple_evaluations": 0,
        "propagation_passes": 0, "global_branch_search_performed": False,
        "minimum_rejected_triple_energy_difference": None}
    prediction = None
    if branch_report["unresolved_after_local_propagation"] == 0:
        prediction = ground(inferred) - features["reference_energy"] - features["truncated_correlation"]
    actual_amplitudes = -source.occupied_profile @ source.hopping[:source.n_pairs, source.n_pairs:]
    positive_slopes = [row["upper_slope"] for row in curves if row["sign"] > 0]
    return {"family": FAMILIES[source.family], "n_pairs": source.n_pairs, "n_virtual": source.n_virtual,
            "edge_count": len(curves), "positive_edge_count": sum(row["sign"] > 0 for row in curves),
            "curves_with_interior_turning_point": sum(row["turning_point"] is not None for row in curves),
            "ambiguous_edge_count": len(ambiguous), "ambiguous_edges": ambiguous,
            "minimum_positive_edge_upper_slope": min(positive_slopes) if positive_slopes else None,
            "source_amplitude_max_error": float(np.max(np.abs(np.asarray(source_amplitudes) - actual_amplitudes))),
            "recovered_hopping_max_error": float(np.max(np.abs(inferred.hopping - source.hopping)))
            if prediction is not None else None,
            "tail_absolute_error": abs(float(prediction) - truth["tail"]) if prediction is not None else None,
            "absolute_tail": abs(truth["tail"]), "reference_weight": truth["reference_weight"],
            "inversion_seconds": time.perf_counter() - started, **branch_report}


def support_stress():
    n_pairs, n_virtual = 2, 6
    onsite = np.asarray([-.089, -.081, .73, .735, 1.15, 1.25, 1.35, 1.45])
    density = np.full((8, 8), .02)
    np.fill_diagonal(density, 0.0)
    profile = np.ones(2) / np.sqrt(2)
    amplitudes = np.asarray([.30, .07, .07, .07, .07, .07])
    positions = np.asarray([.05, .2, .35, .55, .72, .9])
    groups = (positions > np.median(positions)).astype(np.int8)
    for special_edge in (.08, .10, .12, .14, .16, .18, .20, .22):
        hopping = np.zeros((8, 8))
        hopping[:2, 2:] = -profile[:, None] * amplitudes[None, :]
        hopping[2:, :2] = hopping[:2, 2:].T
        hopping[2:, 2:] = .10
        np.fill_diagonal(hopping, 0.0)
        hopping[2, 3] = hopping[3, 2] = special_edge
        model = Hamiltonian(n_pairs, n_virtual, 1, onsite, density, hopping, profile, positions, groups)
        features = low_order_features(model)
        truth = label(model, features)
        result = audit_model(model, features, truth)
        accepted = (truth["reference_weight"] >= .85 and abs(truth["tail"]) >= 1.5e-4 and
                    features["diagonal_gaps"][:2, :6].min() >= .8)
        if result["ambiguous_edge_count"] and accepted:
            return {"found": True, "is_iid_distribution_draw": False,
                    "description": "Deliberately extreme but support-valid positive-transfer model; not used in empirical rates.",
                    "common_virtual_energy_scale_witness": .855,
                    "onsite": onsite.tolist(), "density_off_diagonal": .02,
                    "occupied_profile": profile.tolist(), "source_amplitudes": amplitudes.tolist(),
                    "default_virtual_edge_magnitude": .10, "special_virtual_edge_0_1": special_edge,
                    "minimum_diagonal_gap": float(features["diagonal_gaps"][:2, :6].min()),
                    "accepted_by_release_curation": bool(accepted), "audit": result}
    return {"found": False, "is_iid_distribution_draw": False,
            "description": "Eight deliberate extreme support probes found no accepted ambiguous example."}


def validate_stress_alternative(stress):
    if not stress["found"]:
        return None
    onsite = np.asarray(stress["onsite"])
    density = np.full((8, 8), stress["density_off_diagonal"])
    np.fill_diagonal(density, 0.0)
    profile = np.asarray(stress["occupied_profile"])
    amplitudes = np.asarray(stress["source_amplitudes"])
    hopping = np.zeros((8, 8))
    hopping[:2, 2:] = -profile[:, None] * amplitudes[None, :]
    hopping[2:, :2] = hopping[:2, 2:].T
    hopping[2:, 2:] = stress["default_virtual_edge_magnitude"]
    np.fill_diagonal(hopping, 0.0)
    hopping[2, 3] = hopping[3, 2] = stress["special_virtual_edge_0_1"]
    positions = np.asarray([.05, .2, .35, .55, .72, .9])
    model = Hamiltonian(2, 6, 1, onsite, density, hopping, profile, positions,
                        (positions > np.median(positions)).astype(np.int8))
    original = low_order_features(model)
    edge = stress["audit"]["ambiguous_edges"][0]
    alternative = max(edge["roots"], key=lambda value: abs(value - stress["special_virtual_edge_0_1"]))
    model.hopping[2, 3] = model.hopping[3, 2] = alternative
    changed = low_order_features(model)
    truth = label(model, changed)
    minimum_gap = float(changed["diagonal_gaps"][:2, :6].min())
    return {"alternative_edge_magnitude": alternative,
            "singleton_max_difference": float(np.max(np.abs(changed["cas1"] - original["cas1"]))),
            "pair_max_difference": float(np.max(np.abs(changed["cas2"] - original["cas2"]))),
            "triple_max_difference": float(np.max(np.abs(changed["cas3"] - original["cas3"]))),
            "alternative_reference_weight": truth["reference_weight"],
            "alternative_absolute_tail": abs(truth["tail"]),
            "alternative_minimum_gap": minimum_gap,
            "alternative_passes_release_curation": bool(truth["reference_weight"] >= .85 and
                                                        abs(truth["tail"]) >= 1.5e-4 and minimum_gap >= .8)}


def main():
    started = time.perf_counter()
    before = protected_hashes()
    seed = secrets.randbits(128)
    rng = np.random.default_rng(seed)
    rows = []
    with threadpool_limits(limits=1):
        for index in range(100):
            family = index % 6
            n_pairs = 2 + (index // 6) % 2
            n_virtual = 6 + (index // 12) % 4
            source, features, truth, rejected = accepted_sample(rng, n_pairs, n_virtual, family)
            row = audit_model(source, features, truth)
            row["rejections_before_acceptance"] = rejected
            rows.append(row)
            if (index + 1) % 20 == 0:
                print("independent_models", index + 1, "ambiguous_edges",
                      sum(value["ambiguous_edge_count"] for value in rows), flush=True)
        stress = support_stress()
        stress["alternative_branch_validation"] = validate_stress_alternative(stress)
    if protected_hashes() != before:
        raise AssertionError("Public/evaluator files changed during private audit")
    errors = [row["tail_absolute_error"] for row in rows if row["tail_absolute_error"] is not None]
    summary = {"independent_accepted_models": len(rows), "pair_curves": sum(row["edge_count"] for row in rows),
               "positive_pair_curves": sum(row["positive_edge_count"] for row in rows),
               "models_with_ambiguous_edges": sum(row["ambiguous_edge_count"] > 0 for row in rows),
               "ambiguous_edges": sum(row["ambiguous_edge_count"] for row in rows),
               "curves_with_interior_turning_point": sum(row["curves_with_interior_turning_point"] for row in rows),
               "models_requiring_global_branch_search": sum(row["unresolved_after_local_propagation"] > 0 for row in rows),
               "models_using_no_triples_for_inference": sum(row["triple_evaluations"] == 0 for row in rows),
               "maximum_source_amplitude_error": max(row["source_amplitude_max_error"] for row in rows),
               "tail_rmse": float(np.sqrt(np.mean(np.square(errors)))),
               "maximum_tail_absolute_error": max(errors),
               "total_inversion_seconds": sum(row["inversion_seconds"] for row in rows),
               "family_counts": {family: sum(row["family"] == family for row in rows) for family in FAMILIES}}
    report = {"created_utc": datetime.now(timezone.utc).isoformat(), "audit_seed_not_release_seed": seed,
              "sampling": "100 independent accepted models, deterministic size/family stratification; no release cases parsed",
              "root_method": "ground-energy concavity; endpoint HF slopes locate any interior maximum, then bracket each monotone branch",
              "root_energy_tolerance": 2e-13, "triple_branch_tolerance": 1e-10,
              "summary": summary, "independent_model_metrics": rows, "rare_support_stress": stress,
              "runtime_seconds": time.perf_counter() - started,
              "public_and_evaluator_unchanged": True, "protected_sha256": before,
              "no_new_generation_or_training_dataset_built": True,
              "released_hidden_predictions_generated": False}
    destination = ROOT / "adversary/v1_inverse_audit.json"
    if destination.exists():
        raise RuntimeError("Refusing to overwrite a previous audit")
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"summary": summary, "stress": stress,
                      "runtime_seconds": report["runtime_seconds"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
