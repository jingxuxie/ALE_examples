import os
import sys


sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import hashlib
import json
import math
from pathlib import Path
import secrets
import time
from datetime import datetime, timezone

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "adversary/pool_generation_1"
sys.path.insert(0, str(ROOT / "evaluator"))
sys.path.insert(0, str(ROOT / "authoring"))
from dense_reference import dense_unitary
from kernel import circuit_unitary, score_payload, unitary_metrics


FAMILIES = ((5, 24), (6, 30), (6, 36), (7, 42))
CASES_PER_FAMILY = 6
RANK_TOLERANCE = 1e-10
MIN_NORMALIZED_SINGULAR_VALUE = 1e-5


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    contents = json.dumps(payload, separators=(",", ":"), allow_nan=False) + "\n"
    path.write_text(contents, encoding="utf-8")
    return hashlib.sha256(contents.encode("utf-8")).hexdigest()


def random_rotation(generator, qubit):
    cosine_squared = generator.uniform(0.025, 0.975)
    return {
        "gate": "U3", "qubit": qubit,
        "theta": float(2 * math.acos(math.sqrt(cosine_squared))),
        "phi": float(generator.uniform(-math.pi, math.pi)),
        "lambda": float(generator.uniform(-math.pi, math.pi)),
    }


def topology(generator, qubit_count, cnot_count):
    depths = np.array([min(cut, qubit_count - cut) for cut in range(1, qubit_count)])
    edge_counts = 2 * depths + 2
    extra = cnot_count - int(edge_counts.sum())
    probabilities = depths.astype(float) ** 1.5
    probabilities[[0, -1]] = 0
    probabilities /= probabilities.sum()
    edge_counts += generator.multinomial(extra, probabilities)
    multiset = np.repeat(np.arange(qubit_count - 1), edge_counts)
    for attempt in range(100000):
        sequence = generator.permutation(multiset).tolist()
        if any(first == second for first, second in zip(sequence, sequence[1:])):
            continue
        midpoint = len(sequence) // 2
        if len(set(sequence[:midpoint])) != qubit_count - 1:
            continue
        if len(set(sequence[midpoint:])) != qubit_count - 1:
            continue
        if any(all(sequence[index] == sequence[index % period] for index in range(len(sequence)))
               for period in range(1, len(sequence) // 2 + 1)):
            continue
        directions = generator.integers(0, 2, size=cnot_count)
        directed = [(edge, edge + 1) if direction else (edge + 1, edge)
                    for edge, direction in zip(sequence, directions)]
        return directed, edge_counts.tolist()
    raise RuntimeError("could not sample a nonperiodic well-interleaved edge sequence")


def make_circuit(generator, qubit_count, cnot_count):
    sequence, edge_counts = topology(generator, qubit_count, cnot_count)
    gates = [random_rotation(generator, qubit) for qubit in range(qubit_count)]
    for control, target in sequence:
        gates.append({"gate": "CNOT", "control": control, "target": target})
        endpoints = [control, target]
        generator.shuffle(endpoints)
        gates.extend(random_rotation(generator, qubit) for qubit in endpoints)
    return gates, edge_counts


def spectral_statistics(matrix, qubit_count):
    dimension = 2 ** qubit_count
    cuts = []
    for cut in range(1, qubit_count):
        lower_dimension = 2 ** cut
        upper_dimension = 2 ** (qubit_count - cut)
        realigned = matrix.reshape(upper_dimension, lower_dimension, upper_dimension, lower_dimension)
        realigned = realigned.transpose(1, 3, 0, 2).reshape(lower_dimension ** 2, upper_dimension ** 2)
        singular_values = np.linalg.svd(realigned, compute_uv=False)
        normalized = singular_values / math.sqrt(dimension)
        probabilities = normalized ** 2
        probabilities /= probabilities.sum()
        entropy = float(-np.sum(probabilities * np.log2(np.maximum(probabilities, 1e-300))))
        maximum_rank = min(lower_dimension ** 2, upper_dimension ** 2)
        cuts.append({
            "cut_after_qubit": cut - 1,
            "maximum_rank": maximum_rank,
            "rank": int(np.count_nonzero(singular_values > RANK_TOLERANCE)),
            "relative_rank_at_1e_6": int(np.count_nonzero(singular_values > singular_values[0] * 1e-6)),
            "singular_values": singular_values.tolist(),
            "normalized_singular_values": normalized.tolist(),
            "minimum_normalized_singular_value": float(normalized[-1]),
            "condition_number": float(singular_values[0] / singular_values[-1]),
            "entropy_bits": entropy,
            "effective_rank": float(2 ** entropy),
            "effective_rank_fraction": float(2 ** entropy / maximum_rank),
            "participation_rank": float(1.0 / np.sum(probabilities ** 2)),
            "tail_weight_beyond_rank_4": float(np.sum(probabilities[4:])),
            "tail_weight_beyond_rank_8": float(np.sum(probabilities[8:])),
            "tail_weight_beyond_rank_16": float(np.sum(probabilities[16:])),
        })
    interior = [cut for cut in cuts if cut["maximum_rank"] >= 16]
    return {
        "ranks": [cut["rank"] for cut in cuts],
        "maximum_ranks": [cut["maximum_rank"] for cut in cuts],
        "singular_values": [cut["singular_values"] for cut in cuts],
        "normalized_singular_values": [cut["normalized_singular_values"] for cut in cuts],
        "cuts": cuts,
        "minimum_interior_effective_rank_fraction": min(cut["effective_rank_fraction"] for cut in interior),
        "minimum_interior_normalized_singular_value": min(cut["minimum_normalized_singular_value"] for cut in interior),
        "minimum_interior_tail_weight_beyond_rank_4": min(cut["tail_weight_beyond_rank_4"] for cut in interior),
    }


def qualifies(statistics):
    if statistics["ranks"] != statistics["maximum_ranks"]:
        return False
    for cut in statistics["cuts"]:
        if cut["relative_rank_at_1e_6"] != cut["maximum_rank"]:
            return False
        if cut["maximum_rank"] < 16:
            continue
        fraction = 0.35 if cut["maximum_rank"] == 16 else 0.20
        if cut["effective_rank_fraction"] < fraction:
            return False
        if cut["minimum_normalized_singular_value"] < MIN_NORMALIZED_SINGULAR_VALUE:
            return False
        if cut["tail_weight_beyond_rank_4"] < 0.12:
            return False
    return True


def suite_for(matrix, qubit_count, cnot_count):
    return {
        "schema_version": 1,
        "conventions": {"qubit_order": "little_endian", "gate_order": "first_listed_first_applied"},
        "tolerances": {"infidelity": 1e-8, "normalized_frobenius": 2e-4},
        "targets": [{
            "id": "unitary_" + str(qubit_count) + "q",
            "n_qubits": qubit_count,
            "connectivity": [[qubit, qubit + 1] for qubit in range(qubit_count - 1)],
            "max_cnot": cnot_count, "max_u3": 2 * cnot_count + qubit_count + 20,
            "unitary_real": matrix.real.tolist(), "unitary_imag": matrix.imag.tolist(),
        }],
    }


def main():
    started = time.monotonic()
    if DESTINATION.exists() and any(DESTINATION.iterdir()):
        raise SystemExit("refusing to replace an existing private pool")
    DESTINATION.mkdir(parents=True, exist_ok=True)
    seed_hex = secrets.token_hex(32)
    generator = np.random.default_rng(int(seed_hex, 16))
    entries = []
    certificates = []
    families = []
    for qubit_count, cnot_count in FAMILIES:
        family_entries = []
        attempts = 0
        while len(family_entries) < CASES_PER_FAMILY:
            attempts += 1
            if attempts > 1200 or time.monotonic() - started > 220:
                raise RuntimeError("rank-screening budget exhausted before completing the pool")
            gates, edge_counts = make_circuit(generator, qubit_count, cnot_count)
            fast = circuit_unitary(qubit_count, gates)
            statistics = spectral_statistics(fast, qubit_count)
            if not qualifies(statistics):
                continue
            dense = dense_unitary(qubit_count, gates)
            discrepancy = float(np.max(np.abs(dense - fast)))
            if discrepancy > 1e-12:
                raise RuntimeError("independent dense and row-update kernels disagree")
            phase_angle = float(generator.uniform(-math.pi, math.pi))
            target = dense * np.exp(1j * phase_angle)
            statistics = spectral_statistics(target, qubit_count)
            if not qualifies(statistics):
                raise RuntimeError("independent kernel changed spectral qualification")
            identifier = f"n{qubit_count}_m{cnot_count}_{len(family_entries) + 1:02d}"
            specification = suite_for(target, qubit_count, cnot_count)
            witness = {specification["targets"][0]["id"]: gates}
            report = score_payload(specification, witness)
            if not report["target_met"]:
                raise RuntimeError("private witness does not satisfy public constraints")
            statistics["edge_cnot_counts"] = edge_counts
            statistics["witness_u3_count"] = 2 * cnot_count + qubit_count
            entry = {"id": identifier, "suite": specification, "witness": witness, "statistics": statistics}
            input_path = Path("inputs") / (identifier + ".json")
            witness_path = Path("witnesses") / (identifier + ".json")
            case_path = Path("cases") / (identifier + ".json")
            input_digest = write_json(DESTINATION / input_path, specification)
            witness_digest = write_json(DESTINATION / witness_path, witness)
            write_json(DESTINATION / case_path, entry)
            certificates.append({
                "id": identifier, "input": str(input_path), "witness": str(witness_path),
                "case": str(case_path), "input_sha256": input_digest,
                "witness_sha256": witness_digest,
                "core_score": report["core_score"], "target_met": report["target_met"],
                "max_entry_independent_kernel_error": discrepancy,
                "metrics": unitary_metrics(target, fast),
                "unitarity_frobenius_defect": float(np.linalg.norm(target.conj().T @ target - np.eye(len(target)))),
                "private_target_phase": phase_angle,
            })
            entries.append(entry)
            family_entries.append(entry)
            print(json.dumps({"id": identifier, "ranks": statistics["ranks"],
                              "min_interior_effective_fraction": statistics["minimum_interior_effective_rank_fraction"],
                              "min_interior_normalized_sv": statistics["minimum_interior_normalized_singular_value"],
                              "score": report["core_score"]}), flush=True)
        families.append({
            "n_qubits": qubit_count, "max_cnot": cnot_count,
            "max_u3": 2 * cnot_count + qubit_count + 20,
            "case_count": len(family_entries), "candidates_examined": attempts,
            "ranks": family_entries[0]["statistics"]["ranks"],
            "min_interior_effective_rank_fraction": min(entry["statistics"]["minimum_interior_effective_rank_fraction"] for entry in family_entries),
            "min_interior_normalized_singular_value": min(entry["statistics"]["minimum_interior_normalized_singular_value"] for entry in family_entries),
            "min_interior_tail_weight_beyond_rank_4": min(entry["statistics"]["minimum_interior_tail_weight_beyond_rank_4"] for entry in family_entries),
        })
    cases_digest = write_json(DESTINATION / "cases.json", entries)
    metadata = {
        "generation": 1, "private": True, "created_utc": datetime.now(timezone.utc).isoformat(),
        "case_count": len(entries), "families": families,
        "private_master_seed": seed_hex,
        "motivation": "Increase interleaved interior-cut coupling and robust operator-Schmidt content, not merely qubit count or nominal floating-point rank.",
        "construction": "Nearest-neighbor random nonperiodic multiset permutations; every cut visited in both halves; interior-weighted crossing counts; generic conditioned Haar-polar U3 rotations with independent azimuthal phases.",
        "operator_schmidt_convention": "Realign U[(out_upper,out_lower),(in_upper,in_lower)] to [(out_lower,in_lower),(out_upper,in_upper)]; divide singular values by sqrt(2**n) for squared weights summing to one.",
        "qualification": {"absolute_rank_tolerance": RANK_TOLERANCE,
                          "relative_rank_tolerance": 1e-6, "require_maximum_rank_every_cut": True,
                          "min_interior_normalized_singular_value": MIN_NORMALIZED_SINGULAR_VALUE,
                          "min_effective_fraction_for_rank_16_cuts": 0.35,
                          "min_effective_fraction_for_rank_64_cuts": 0.20,
                          "min_interior_tail_weight_beyond_rank_4": 0.12},
        "certificates": certificates, "cases_sha256": cases_digest,
        "all_private_witnesses_score": 1.0,
        "max_independent_kernel_error": max(certificate["max_entry_independent_kernel_error"] for certificate in certificates),
        "elapsed_seconds": time.monotonic() - started,
        "champion_search_run": False, "fresh_agents_launched": 0,
        "hardness_claim": "None: spectral qualification and achievability only; main must test the recovered champion method.",
        "release_warning": "All pool files are private. A selected inputs file alone is public-style; never release cases, witnesses, metadata, or generator source.",
    }
    write_json(DESTINATION / "metadata.json", metadata)
    write_json(DESTINATION / "pool.json", {
        "generation": 1, "private": True, "case_count": len(entries),
        "cases": entries,
    })
    print(json.dumps({"ready": True, "case_count": len(entries), "families": families,
                      "elapsed_seconds": metadata["elapsed_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
