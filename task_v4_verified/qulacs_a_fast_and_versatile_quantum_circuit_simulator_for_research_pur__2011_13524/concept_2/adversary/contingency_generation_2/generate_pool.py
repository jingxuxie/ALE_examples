import os
import sys


sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import resource
import secrets
import time

import numpy as np


PRIVATE_ROOT = Path(__file__).resolve().parent
CONCEPT_ROOT = PRIVATE_ROOT.parents[1]
sys.path.insert(0, str(CONCEPT_ROOT / "evaluator"))
sys.path.insert(0, str(CONCEPT_ROOT / "authoring"))
from dense_reference import dense_unitary
import kernel


CANDIDATES = [(8, count, index) for index in range(1, 4) for count in (80, 72)] + [
    (7, 60, index) for index in range(1, 3)
]
EDGE_COUNTS = {
    (7, 60): [8, 10, 12, 12, 10, 8],
    (8, 72): [8, 10, 12, 12, 12, 10, 8],
    (8, 80): [9, 11, 13, 14, 13, 11, 9],
}
THRESHOLDS = {
    "rank_absolute_tolerance": 1e-10,
    "rank_relative_tolerance": 1e-6,
    "minimum_normalized_singular_value": 1e-5,
    "minimum_effective_fraction_by_maximum_rank": {"4": 0.75, "16": 0.50, "64": 0.35, "256": 0.25},
    "minimum_pauli_squared_commutator": 0.08,
    "minimum_axis_gram_eigenvalue": 0.04,
    "maximum_temporal_saturation_fraction": 0.80,
    "maximum_independent_entry_error": 1e-12,
}
PAULIS = (
    np.array([[0, 1], [1, 0]], dtype=complex),
    np.array([[0, -1j], [1j, 0]], dtype=complex),
    np.diag([1, -1]).astype(complex),
)


def digest_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    contents = json.dumps(payload, separators=(",", ":"), allow_nan=False) + "\n"
    path.write_text(contents, encoding="utf-8")
    return hashlib.sha256(contents.encode("utf-8")).hexdigest()


def candidate_seed(master_seed, identifier):
    return hashlib.sha256((master_seed + ":" + identifier).encode("ascii")).hexdigest()


def temporal_cones(edges, qubit_count):
    directions = {}
    for name, sequence in (("forward", edges), ("reverse", list(reversed(edges)))):
        supports = [1 << qubit for qubit in range(qubit_count)]
        reached = [None] * qubit_count
        all_qubits = (1 << qubit_count) - 1
        for position, edge in enumerate(sequence, 1):
            edge_mask = (1 << edge) | (1 << (edge + 1))
            for source in range(qubit_count):
                if supports[source] & edge_mask:
                    supports[source] |= edge_mask
                if supports[source] == all_qubits and reached[source] is None:
                    reached[source] = position
        directions[name] = {
            "final_support_masks": supports,
            "full_support_cnot_indices": reached,
            "all_sources_full_support": all(value == all_qubits for value in supports),
        }
    return directions


def make_schedule(generator, qubit_count, cnot_count):
    counts = EDGE_COUNTS[(qubit_count, cnot_count)]
    round_count = min(counts)
    extra_edges = np.repeat(np.arange(qubit_count - 1), np.array(counts) - round_count)
    for proposal in range(1, 10001):
        extra_groups = np.array_split(generator.permutation(extra_edges), round_count)
        sequence = []
        round_lengths = []
        for extras in extra_groups:
            entries = np.concatenate((np.arange(qubit_count - 1), extras))
            for ordering_attempt in range(100):
                ordered = generator.permutation(entries).tolist()
                if sequence and sequence[-1] == ordered[0]:
                    continue
                if any(left == right for left, right in zip(ordered, ordered[1:])):
                    continue
                break
            else:
                break
            sequence.extend(ordered)
            round_lengths.append(len(ordered))
        if len(sequence) != cnot_count:
            continue
        quarter_coverage = [sorted(set(part.tolist())) for part in np.array_split(sequence, 4)]
        if any(len(part) != qubit_count - 1 for part in quarter_coverage):
            continue
        if any(all(sequence[index] == sequence[index % period] for index in range(cnot_count))
               for period in range(1, cnot_count // 2 + 1)):
            continue
        cones = temporal_cones(sequence, qubit_count)
        if any(not direction["all_sources_full_support"] or
               max(direction["full_support_cnot_indices"]) > 0.8 * cnot_count
               for direction in cones.values()):
            continue
        orientations = {}
        for edge, count in enumerate(counts):
            orientations[edge] = generator.permutation(np.arange(count) % 2).tolist()
        directed = []
        for edge in sequence:
            direction = orientations[edge].pop()
            directed.append((edge, edge + 1) if direction else (edge + 1, edge))
        return directed, {
            "edge_sequence": sequence,
            "edge_cnot_counts": counts,
            "connected_round_lengths": round_lengths,
            "quarter_edge_coverage": quarter_coverage,
            "topology_proposals": proposal,
            "temporal_cones": cones,
            "maximum_edge_idle_gap": max(
                max(np.diff([-1] + [index for index, value in enumerate(sequence) if value == edge] + [cnot_count])) - 1
                for edge in range(qubit_count - 1)
            ).item(),
            "nonperiodic": True,
            "consecutive_same_edge": False,
            "direction_counts_by_edge": [
                [sum(control == edge and target == edge + 1 for control, target in directed),
                 sum(control == edge + 1 and target == edge for control, target in directed)]
                for edge in range(qubit_count - 1)
            ],
        }
    raise RuntimeError("bounded topology-only sampling exhausted; no dense candidate generated")


def random_rotation(generator, qubit):
    return {
        "gate": "U3", "qubit": qubit,
        "theta": float(2 * math.acos(math.sqrt(generator.uniform(0.10, 0.90)))),
        "phi": float(generator.choice([-1, 1]) * generator.uniform(0.25, math.pi - 0.25)),
        "lambda": float(generator.choice([-1, 1]) * generator.uniform(0.25, math.pi - 0.25)),
    }


def make_circuit(seed_hex, qubit_count, cnot_count):
    generator = np.random.Generator(np.random.PCG64(int(seed_hex, 16)))
    directed, schedule = make_schedule(generator, qubit_count, cnot_count)
    gates = [random_rotation(generator, qubit) for qubit in range(qubit_count)]
    for control, target in directed:
        gates.append({"gate": "CNOT", "control": control, "target": target})
        endpoints = generator.permutation([control, target])
        gates.extend(random_rotation(generator, int(qubit)) for qubit in endpoints)
    return gates, schedule, float(generator.uniform(-math.pi, math.pi))


def all_schmidt_statistics(matrix, qubit_count):
    dimension = 1 << qubit_count
    tensor = matrix.reshape([2] * (2 * qubit_count))
    cuts = []
    for mask in range(1, (1 << (qubit_count - 1))):
        left = [qubit for qubit in range(qubit_count) if mask & (1 << qubit)]
        right = [qubit for qubit in range(qubit_count) if qubit not in left]
        left_axes = [qubit_count - 1 - qubit for qubit in reversed(left)]
        right_axes = [qubit_count - 1 - qubit for qubit in reversed(right)]
        axes = left_axes + [axis + qubit_count for axis in left_axes]
        axes += right_axes + [axis + qubit_count for axis in right_axes]
        realigned = tensor.transpose(axes).reshape(4 ** len(left), 4 ** len(right))
        normalized = np.linalg.svd(realigned, compute_uv=False) / math.sqrt(dimension)
        weights = normalized ** 2
        weights /= weights.sum()
        entropy = float(-np.sum(weights * np.log2(np.maximum(weights, 1e-300))))
        maximum_rank = len(normalized)
        effective_rank = 2 ** entropy
        chain_cut = left == list(range(len(left)))
        cut = {
            "left_qubits": left, "right_qubits": right, "chain_cut": chain_cut,
            "maximum_rank": maximum_rank,
            "rank_absolute_1e_10": int(np.count_nonzero(normalized * math.sqrt(dimension) > 1e-10)),
            "rank_relative_1e_6": int(np.count_nonzero(normalized > normalized[0] * 1e-6)),
            "minimum_normalized_singular_value": float(normalized[-1]),
            "condition_number": float(normalized[0] / max(normalized[-1], 1e-300)),
            "entropy_bits": entropy, "effective_rank": effective_rank,
            "effective_rank_fraction": effective_rank / maximum_rank,
            "participation_rank": float(1 / np.sum(weights ** 2)),
            "rank_for_99_percent_weight": int(np.searchsorted(np.cumsum(weights), 0.99) + 1),
            "tail_weight_beyond_rank_4": float(weights[4:].sum()),
            "tail_weight_beyond_rank_16": float(weights[16:].sum()),
            "tail_weight_beyond_rank_64": float(weights[64:].sum()),
            "tail_weight_beyond_half_maximum_rank": float(weights[maximum_rank // 2:].sum()),
        }
        if chain_cut:
            cut["normalized_singular_values"] = normalized.tolist()
        cuts.append(cut)
    return {
        "bipartition_count": len(cuts),
        "all_cuts_full_absolute_and_relative_rank": all(
            cut["rank_absolute_1e_10"] == cut["rank_relative_1e_6"] == cut["maximum_rank"] for cut in cuts),
        "minimum_effective_rank_fraction": min(cut["effective_rank_fraction"] for cut in cuts),
        "minimum_normalized_singular_value": min(cut["minimum_normalized_singular_value"] for cut in cuts),
        "chain_ranks": [cut["rank_absolute_1e_10"] for cut in cuts if cut["chain_cut"]],
        "chain_effective_ranks": [cut["effective_rank"] for cut in cuts if cut["chain_cut"]],
        "chain_effective_rank_fractions": [cut["effective_rank_fraction"] for cut in cuts if cut["chain_cut"]],
        "cuts": cuts,
    }


def pauli_actions(qubit_count):
    indices = np.arange(1 << qubit_count)
    actions = []
    for qubit in range(qubit_count):
        flipped = indices ^ (1 << qubit)
        signs = (1 - 2 * ((indices >> qubit) & 1)).astype(complex)
        actions.append(((flipped, np.ones(len(indices), dtype=complex)),
                        (flipped, -1j * signs), (indices, signs)))
    return actions


def commutator_rows(evolved, actions):
    rows = []
    for operator in evolved:
        for permutation, factors in actions:
            left = factors[:, None] * operator[permutation, :]
            right = operator[:, permutation] * factors[permutation][None, :]
            rows.append((right - left).reshape(-1))
    return np.asarray(rows)


def causal_statistics(matrix, qubit_count):
    dimension = len(matrix)
    actions = pauli_actions(qubit_count)
    result = {}
    basis_values = []
    for name, left, right in (("forward_U_P_Udag", matrix, matrix.conj().T),
                              ("backward_Udag_P_U", matrix.conj().T, matrix)):
        values = np.empty((qubit_count, qubit_count, 3, 3))
        eigenvalues = np.empty((qubit_count, qubit_count, 9))
        for source in range(qubit_count):
            evolved = [left @ (factors[:, None] * right[permutation, :])
                       for permutation, factors in actions[source]]
            for destination in range(qubit_count):
                rows = commutator_rows(evolved, actions[destination])
                gram = (rows.conj() @ rows.T).real / (2 * dimension)
                gram = (gram + gram.T) / 2
                values[source, destination] = np.diag(gram).reshape(3, 3)
                eigenvalues[source, destination] = np.linalg.eigvalsh(gram)
        result[name] = {
            "squared_commutators": values.tolist(),
            "axis_gram_eigenvalues": eigenvalues.tolist(),
            "pair_minimum_squared_commutator": values.min(axis=(2, 3)).tolist(),
            "pair_axis_gram_lower_bound": eigenvalues[:, :, 0].tolist(),
            "minimum_squared_commutator": float(values.min()),
            "mean_squared_commutator": float(values.mean()),
            "minimum_axis_gram_eigenvalue": float(eigenvalues.min()),
            "vanishing_pauli_count_at_1e_10": int(np.count_nonzero(values <= 1e-10)),
            "checked_pauli_commutator_count": int(values.size),
        }
        basis_values.append(values)
    result["bidirectional_transpose_maximum_error"] = float(
        np.max(np.abs(basis_values[0] - basis_values[1].transpose(1, 0, 3, 2))))
    result["minimum_squared_commutator"] = min(result[name]["minimum_squared_commutator"]
        for name in ("forward_U_P_Udag", "backward_Udag_P_U"))
    result["minimum_axis_gram_eigenvalue"] = min(result[name]["minimum_axis_gram_eigenvalue"]
        for name in ("forward_U_P_Udag", "backward_Udag_P_U"))
    return result


def angle_statistics(gates):
    rotations = [gate for gate in gates if gate["gate"] == "U3"]
    distances = [math.sqrt(max(0, 2 - abs(np.trace(kernel.u3_matrix(
        gate["theta"], gate["phi"], gate["lambda"]))))) for gate in rotations]
    return {
        "u3_count": len(rotations),
        "theta_range": [min(gate["theta"] for gate in rotations), max(gate["theta"] for gate in rotations)],
        "minimum_absolute_phi_or_lambda": min(abs(gate[name]) for gate in rotations for name in ("phi", "lambda")),
        "minimum_phase_invariant_normalized_distance_to_identity": min(distances),
    }


def qualification_failures(spectral, causal):
    failures = []
    if not spectral["all_cuts_full_absolute_and_relative_rank"]:
        failures.append("not all bipartitions have full robust numerical rank")
    for cut in spectral["cuts"]:
        threshold = THRESHOLDS["minimum_effective_fraction_by_maximum_rank"][str(cut["maximum_rank"])]
        if cut["effective_rank_fraction"] < threshold:
            failures.append(f"effective-rank fraction below {threshold} at {cut['left_qubits']}")
        if cut["minimum_normalized_singular_value"] < THRESHOLDS["minimum_normalized_singular_value"]:
            failures.append(f"weak smallest Schmidt coefficient at {cut['left_qubits']}")
    for field, threshold in (("minimum_squared_commutator", THRESHOLDS["minimum_pauli_squared_commutator"]),
                             ("minimum_axis_gram_eigenvalue", THRESHOLDS["minimum_axis_gram_eigenvalue"])):
        if causal[field] < threshold:
            failures.append(f"{field} below {threshold}")
    return failures


def specification_for(matrix, qubit_count, cnot_count):
    return {
        "schema_version": 1,
        "conventions": {"qubit_order": "little_endian", "gate_order": "first_listed_first_applied"},
        "tolerances": {"infidelity": 1e-8, "normalized_frobenius": 2e-4},
        "targets": [{
            "id": f"unitary_{qubit_count}q", "n_qubits": qubit_count,
            "connectivity": [[qubit, qubit + 1] for qubit in range(qubit_count - 1)],
            "max_cnot": cnot_count, "max_u3": 2 * cnot_count + qubit_count,
            "unitary_real": matrix.real.tolist(), "unitary_imag": matrix.imag.tolist(),
        }],
    }


def generate_candidate(job):
    output, master_seed, qubit_count, cnot_count, index = job
    started = time.monotonic()
    identifier = f"n{qubit_count}_m{cnot_count}_{index:02d}"
    seed_hex = candidate_seed(master_seed, identifier)
    gates, schedule, phase = make_circuit(seed_hex, qubit_count, cnot_count)
    fast = kernel.circuit_unitary(qubit_count, gates)
    independent = dense_unitary(qubit_count, gates)
    maximum_error = float(np.max(np.abs(fast - independent)))
    if maximum_error > THRESHOLDS["maximum_independent_entry_error"]:
        raise RuntimeError(f"independent witness reconstruction failed: {identifier}")
    matrix = independent * np.exp(1j * phase)
    spectral = all_schmidt_statistics(matrix, qubit_count)
    causal = causal_statistics(matrix, qubit_count)
    failures = qualification_failures(spectral, causal)
    specification = specification_for(matrix, qubit_count, cnot_count)
    witness = {f"unitary_{qubit_count}q": gates}
    counts = kernel.validate_gates(gates, specification["targets"][0])
    if counts != {"U3": 2 * cnot_count + qubit_count, "CNOT": cnot_count}:
        raise RuntimeError("witness does not exactly saturate its declared finite budgets")
    input_path = Path("inputs") / f"{identifier}.json"
    witness_path = Path("witnesses") / f"{identifier}.json"
    statistics_path = Path("statistics") / f"{identifier}.json"
    input_digest = write_json(output / input_path, specification)
    witness_digest = write_json(output / witness_path, witness)
    roundtrip_specification = kernel.parse_json((output / input_path).read_bytes())
    roundtrip_witness = kernel.read_json(str(output / witness_path))
    scored = kernel.score_payload(roundtrip_specification, roundtrip_witness)
    if not scored["target_met"]:
        raise RuntimeError(f"serialized source-native witness does not pass: {identifier}")
    statistics = {"id": identifier, "schedule": schedule, "angles": angle_statistics(gates),
                  "operator_schmidt": spectral, "heisenberg_causal_mixing": causal,
                  "qualified": not failures, "qualification_failures": failures}
    statistics_digest = write_json(output / statistics_path, statistics)
    certificate = {
        "id": identifier, "n_qubits": qubit_count, "max_cnot": cnot_count,
        "max_u3": 2 * cnot_count + qubit_count, "private_seed": seed_hex,
        "private_target_phase": phase, "qualified": not failures, "qualification_failures": failures,
        "input": str(input_path), "input_sha256": input_digest,
        "witness": str(witness_path), "witness_sha256": witness_digest,
        "statistics": str(statistics_path), "statistics_sha256": statistics_digest,
        "input_bytes": (output / input_path).stat().st_size,
        "witness_bytes": (output / witness_path).stat().st_size,
        "input_exceeds_kernel_read_json_limit": (output / input_path).stat().st_size > kernel.MAX_JSON_BYTES,
        "kernel_score_after_json_roundtrip": scored,
        "maximum_independent_entry_error": maximum_error,
        "unitarity_frobenius_defect": float(np.linalg.norm(matrix.conj().T @ matrix - np.eye(len(matrix)))),
        "phase_invariant_normalized_distance_to_identity": math.sqrt(max(0, 2 - 2 * abs(np.trace(matrix)) / len(matrix))),
        "bipartition_count": spectral["bipartition_count"],
        "chain_ranks": spectral["chain_ranks"],
        "chain_effective_ranks": spectral["chain_effective_ranks"],
        "minimum_all_cut_effective_fraction": spectral["minimum_effective_rank_fraction"],
        "minimum_all_cut_normalized_singular_value": spectral["minimum_normalized_singular_value"],
        "minimum_squared_commutator": causal["minimum_squared_commutator"],
        "minimum_axis_gram_eigenvalue": causal["minimum_axis_gram_eigenvalue"],
        "bidirectional_transpose_error": causal["bidirectional_transpose_maximum_error"],
        "elapsed_seconds": time.monotonic() - started,
        "worker_peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
    }
    print(json.dumps({key: certificate[key] for key in (
        "id", "qualified", "chain_effective_ranks", "minimum_all_cut_effective_fraction",
        "minimum_squared_commutator", "minimum_axis_gram_eigenvalue", "elapsed_seconds")}), flush=True)
    return certificate


def main():
    parser = argparse.ArgumentParser(description="Private bounded contingency search; never installs a task.")
    parser.add_argument("--output", type=Path, default=PRIVATE_ROOT / "pool")
    parser.add_argument("--seed", default=None)
    parser.add_argument("--workers", type=int, choices=(1, 2), default=2)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    if not output.is_relative_to(PRIVATE_ROOT) or output == PRIVATE_ROOT:
        raise SystemExit("all generated files must stay strictly under contingency_generation_2")
    if output.exists():
        raise SystemExit("refusing to overwrite an existing private output directory")
    os.umask(0o077)
    output.mkdir(parents=True, mode=0o700)
    started = time.monotonic()
    master_seed = arguments.seed or secrets.token_hex(32)
    if len(master_seed) != 64 or any(character not in "0123456789abcdef" for character in master_seed):
        raise SystemExit("seed must contain exactly 64 lowercase hexadecimal characters")
    jobs = [(output, master_seed, *candidate) for candidate in CANDIDATES]
    with ProcessPoolExecutor(max_workers=arguments.workers) as executor:
        certificates = list(executor.map(generate_candidate, jobs))
    metadata = {
        "private": True, "contingency_only": True, "installed": False,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "master_seed": master_seed, "rng": "NumPy PCG64, independent SHA256-derived seed per candidate",
        "candidate_count": len(certificates), "dense_candidates_examined": len(certificates),
        "qualified_count": sum(certificate["qualified"] for certificate in certificates),
        "qualification_thresholds": THRESHOLDS, "certificates": certificates,
        "operator_schmidt_convention": "All nonempty subsets excluding the highest-index qubit represent all complementary-equivalence bipartitions; realign (out_A,in_A)|(out_B,in_B); normalized singular values are s/sqrt(2**n). Effective rank = exp2(Shannon entropy of normalized squared singular values).",
        "commutator_convention": "For both U P_i Udag and Udag P_i U, C[i,j,a,b] = ||[evolved(P_i^a),P_j^b]||_F**2/(2*2**n), a,b in X,Y,Z. Arrays index source,destination,source_axis,destination_axis.",
        "axis_gram_convention": "Real 9x9 Gram of all nine commutators for a site pair, normalized by 2*2**n. Its smallest eigenvalue lower-bounds C for every pair of unit real Bloch axes, since ||a tensor b||=1. Identity operators are necessarily excluded.",
        "numpy_version": np.__version__, "python_version": sys.version.split()[0],
        "worker_count": arguments.workers, "blas_threads_per_worker": 1,
        "elapsed_seconds": time.monotonic() - started,
        "source_sha256": {"generate_pool.py": digest_file(Path(__file__)),
                          "evaluator/kernel.py": digest_file(CONCEPT_ROOT / "evaluator/kernel.py"),
                          "authoring/dense_reference.py": digest_file(CONCEPT_ROOT / "authoring/dense_reference.py")},
        "fresh_agents_launched": 0, "participant_or_champion_search_run": False,
        "activation_gate": "No installation or new task generation. Main must first confirm active generation1 fresh v2 is solved and explicitly authorize promotion.",
        "hardness_claim": "Structural hardness is hypothesized, not empirically proven until a fresh attempt. Witness feasibility and structural certificates are not compact-circuit lower bounds.",
        "input_size_caveat": "8q full-precision dense inputs exceed kernel.read_json's 1-MiB cap. Inputs are checked with kernel.parse_json; every witness is checked with capped kernel.read_json. A future input loader/package audit is required before any promotion; no evaluator is changed.",
        "privacy_warning": "Entire directory is PRIVATE. Never publish generator, seeds, witnesses, statistics, logs, or metadata. Only a selected inputs JSON is public-style, and only after explicit promotion authorization.",
    }
    write_json(output / "metadata.json", metadata)
    print(json.dumps({"ready_private_only": True, "candidate_count": len(certificates),
                      "qualified_count": metadata["qualified_count"], "elapsed_seconds": metadata["elapsed_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
