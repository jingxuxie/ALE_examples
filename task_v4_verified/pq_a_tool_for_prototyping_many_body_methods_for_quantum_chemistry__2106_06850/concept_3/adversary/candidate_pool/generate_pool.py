"""Bounded private physical-complexity search, not a contestant-algorithm probe."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import secrets
import sys
import time

sys.dont_write_bytecode = True

import numpy as np

from pool_api import (
    ROOT, MINIMUM_LATE_SPECTRUM_CHANGE, dense_entangled, engine, metrics,
    opposite_spin_double, save_assets, spin_layout,
)


class Sector:
    def __init__(self, n_orbitals, n_electrons):
        self.n_orbitals, self.n_electrons = n_orbitals, n_electrons
        self.basis = engine.determinant_basis(n_orbitals, n_electrons)
        self.labels = engine.allowed_excitations(n_orbitals)
        self.pairs = tuple(engine.rotation_pairs(n_orbitals, n_electrons, label) for label in self.labels)
        self.maps, self.signs = [], []
        dimension = len(self.basis)
        for sources, destinations, signs in self.pairs:
            mapping = np.full(dimension + 1, dimension, dtype=np.intp)
            coefficients = np.zeros(dimension + 1)
            mapping[sources], mapping[destinations] = destinations, sources
            coefficients[sources], coefficients[destinations] = signs, -signs
            self.maps.append(mapping)
            self.signs.append(coefficients)
        self.commutator_cache = {}

    def noncommuting(self, left, right):
        key = tuple(sorted((left, right)))
        if key not in self.commutator_cache:
            left_map, right_map = self.maps[left], self.maps[right]
            left_sign, right_sign = self.signs[left], self.signs[right]
            first_target, second_target = left_map[right_map], right_map[left_map]
            first_sign = right_sign * left_sign[right_map]
            second_sign = left_sign * right_sign[left_map]
            self.commutator_cache[key] = bool(np.any(
                (first_sign != second_sign) | ((first_target != second_target) & ((first_sign != 0) | (second_sign != 0)))
            ))
        return self.commutator_cache[key]


def physical_score(diagnostics):
    dimension = diagnostics["schmidt_dimension"]
    sector = diagnostics["spin_sector_dimension"]
    return (4.0 * diagnostics["support"] / sector
            + 2.0 * diagnostics["schmidt_rank"] / dimension
            + diagnostics["entropy_nats"] / math.log(dimension)
            + 0.6 * diagnostics["participation_ratio"] / sector)


def make_candidate(identifier, sector, depth, seed, deadline):
    random = np.random.default_rng(seed)
    prefix_depth = 16 if sector.n_orbitals == 10 else 20
    single_positions = (0, 2, 4, 7, 10) if sector.n_orbitals == 10 else (0, 2, 4, 6, 9, 12, 15)
    case = engine.Case(identifier, sector.n_orbitals, sector.n_electrons,
                       sector.n_electrons // 2, sector.n_electrons // 2,
                       (1 << sector.n_electrons) - 1, depth, sector.basis, np.zeros(len(sector.basis)))
    last_failure = None
    for trial in range(64):
        if time.perf_counter() > deadline:
            raise TimeoutError("bounded generation time exceeded")
        state = engine.reference_state(case)
        labels, angles, history = [], [], [dict(prefix_length=0, **metrics(state, case.n_orbitals, case.n_electrons))]
        for position in range(depth):
            is_single = position in single_positions
            spin = single_positions.index(position) % 2 if is_single else None
            available = [index for index, label in enumerate(sector.labels)
                         if index not in labels
                         and (len(label.annihilate) == 1 and label.annihilate[0] % 2 == spin
                              if is_single else opposite_spin_double(label))
                         and (not labels or sector.noncommuting(labels[-1], index))]
            random.shuffle(available)
            available = available[:72]
            winner, winning_score = None, -math.inf
            previous_spectrum = np.asarray(history[-1]["schmidt_values"])
            for index in available:
                tangent = engine.apply_generator(state, sector.pairs[index])
                if float(tangent @ tangent) < 0.05:
                    continue
                for angle_trial in range(2 if is_single else 1):
                    theta = float(random.uniform(0.42, 1.20) * random.choice((-1, 1)))
                    proposal = engine.apply_rotation(state, sector.pairs[index], theta)
                    effect = float(np.linalg.norm(proposal - state))
                    if effect < 0.10:
                        continue
                    diagnostics = metrics(proposal, case.n_orbitals, case.n_electrons)
                    spectrum_change = float(np.linalg.norm(np.asarray(diagnostics["schmidt_values"]) - previous_spectrum))
                    if position + 1 >= prefix_depth and not dense_entangled(diagnostics):
                        continue
                    if position >= prefix_depth and spectrum_change < MINIMUM_LATE_SPECTRUM_CHANGE:
                        continue
                    score = physical_score(diagnostics) + float(random.uniform(-0.025, 0.025))
                    if score > winning_score:
                        winning_score = score
                        diagnostics.update(prefix_length=position + 1, state_step_l2=effect,
                                           schmidt_spectrum_step_l2=spectrum_change,
                                           gate_family="single" if is_single else "opposite_spin_double")
                        winner = index, theta, proposal, diagnostics
            if winner is None:
                last_failure = {"trial": trial, "prefix_length": position, "last_metrics": history[-1]}
                break
            index, theta, state, diagnostics = winner
            labels.append(index)
            angles.append(theta)
            history.append(diagnostics)
        if len(labels) != depth:
            continue
        gates = [{"annihilate": list(sector.labels[index].annihilate), "create": list(sector.labels[index].create),
                  "theta": theta} for index, theta in zip(labels, angles)]
        target = {"case_id": identifier, "n_orbitals": case.n_orbitals, "n_electrons": case.n_electrons,
                  "n_alpha": case.n_alpha, "n_beta": case.n_beta, "reference_mask": case.reference_mask,
                  "max_gates": depth, "determinants": list(case.determinants), "target_amplitudes": state.tolist()}
        metadata = {"case_id": identifier, "private_seed": str(seed), "accepted_trial": trial,
                    "dense_full_rank_prefix_depth": prefix_depth,
                    "late_opposite_spin_double_count": depth - prefix_depth,
                    "single_count": len(single_positions), "opposite_spin_double_count": depth - len(single_positions),
                    "distinct_gate_count": len(set(labels)), "allowed_gate_count": len(sector.labels),
                    "minimum_absolute_angle": min(map(abs, angles)), "maximum_absolute_angle": max(map(abs, angles)),
                    "earliest_full_support_prefix": next(entry["prefix_length"] for entry in history if entry["support"] == entry["spin_sector_dimension"]),
                    "earliest_full_schmidt_rank_prefix": next(entry["prefix_length"] for entry in history if entry["schmidt_rank"] == entry["schmidt_dimension"]),
                    "prefixes": history}
        return target, {"case_id": identifier, "gates": gates}, metadata
    raise RuntimeError("physical-complexity criteria not reached: " + json.dumps(last_failure))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replicates", type=int, default=3, choices=(2, 3, 4))
    parser.add_argument("--seconds", type=int, default=480)
    arguments = parser.parse_args()
    if (ROOT / "targets.json").exists() or (ROOT / "cases").exists():
        raise RuntimeError("pool already exists; refusing to overwrite or regenerate")
    started = time.perf_counter()
    deadline = started + arguments.seconds
    sectors = {(10, 4): Sector(10, 4), (10, 6): Sector(10, 6), (12, 6): Sector(12, 6)}
    specifications = [(n_orbitals, n_electrons, depth) for n_orbitals, n_electrons, depths in (
        (10, 4, (24, 28, 32)), (10, 6, (24, 28, 32)), (12, 6, (28, 32)),
    ) for depth in depths for replicate in range(arguments.replicates)]
    targets, certificates, metadata, index, skipped = [], [], [], [], []
    for n_orbitals, n_electrons, depth in specifications:
        identifier = "pool_%03d" % (len(targets) + 1)
        seed = secrets.randbits(128)
        try:
            target, certificate, diagnostics = make_candidate(identifier, sectors[n_orbitals, n_electrons], depth, seed, deadline)
        except (RuntimeError, TimeoutError) as error:
            if n_orbitals != 12:
                raise
            skipped.append({"n_orbitals": n_orbitals, "n_electrons": n_electrons, "depth": depth,
                            "reason": str(error)[:300], "optional_sector": True})
            continue
        target_document = {"schema_version": 1, "fidelity_threshold": engine.FIDELITY_THRESHOLD, "cases": [target]}
        certificate_document = {"schema_version": 1, "circuits": [certificate]}
        save_assets({"cases/" + identifier + "/targets.json": target_document,
                     "cases/" + identifier + "/certificate.json": certificate_document,
                     "cases/" + identifier + "/metadata.json": diagnostics})
        targets.append(target)
        certificates.append(certificate)
        metadata.append(diagnostics)
        index.append({"case_id": identifier, "n_orbitals": n_orbitals, "n_electrons": n_electrons,
                      "gate_cap": depth, "targets_path": "cases/" + identifier + "/targets.json",
                      "private_certificate_path": "cases/" + identifier + "/certificate.json",
                      "private_metadata_path": "cases/" + identifier + "/metadata.json",
                      "dense_full_rank_prefix_depth": diagnostics["dense_full_rank_prefix_depth"],
                      "late_opposite_spin_double_count": diagnostics["late_opposite_spin_double_count"],
                      "final_metrics": diagnostics["prefixes"][-1]})
        print(json.dumps({"accepted": identifier, "sector": [n_orbitals, n_electrons], "depth": depth,
                          "late_doubles": diagnostics["late_opposite_spin_double_count"],
                          "support": diagnostics["prefixes"][-1]["support"],
                          "schmidt_rank": diagnostics["prefixes"][-1]["schmidt_rank"],
                          "effective_rank": diagnostics["prefixes"][-1]["effective_schmidt_rank"]}), flush=True)
    if not 16 <= len(targets) <= 32:
        raise RuntimeError("insufficient valid pool cases")
    certificate_document = json.dumps({"schema_version": 1, "circuits": certificates}, separators=(",", ":"), allow_nan=False) + "\n"
    if len(certificate_document.encode()) > engine.MAX_OUTPUT_BYTES:
        raise RuntimeError("aggregate certificate exceeds unchanged JSON cap")
    save_assets({
        "targets.json": {"schema_version": 1, "fidelity_threshold": engine.FIDELITY_THRESHOLD, "cases": targets},
        "certificates.json": certificate_document,
        "metadata.json": {"confidential": True, "date": "2026-08-28", "cases": metadata, "skipped_optional_specs": skipped,
                          "runtime_seconds": time.perf_counter() - started, "numpy_version": np.__version__,
                          "engine_snapshot_sha256": hashlib.sha256((ROOT / "base_engine.py").read_bytes()).hexdigest(),
                          "no_current_attempts_read": True, "active_task_modified": False},
        "index.json": {"confidential": True, "status": "generated_pending_verification", "case_count": len(targets),
                       "fidelity_threshold": engine.FIDELITY_THRESHOLD, "cases": index},
    })
    print(json.dumps({"generated": len(targets), "runtime_seconds": time.perf_counter() - started}), flush=True)


if __name__ == "__main__":
    main()
