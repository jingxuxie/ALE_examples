import os
import sys


sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
import math
from pathlib import Path
import resource
import time

import numpy as np

import generate_pool as generation
from dense_reference import dense_unitary, embed
import kernel


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def independent_gate_audit(gates, target):
    counts = {"U3": 0, "CNOT": 0}
    for gate in gates:
        require(gate["gate"] in counts, "non-source-native gate")
        counts[gate["gate"]] += 1
        if gate["gate"] == "CNOT":
            require(abs(gate["control"] - gate["target"]) == 1, "non-nearest-neighbor gate")
            require(0 <= min(gate["control"], gate["target"]) < max(gate["control"], gate["target"]) < target["n_qubits"], "bad CNOT endpoint")
        else:
            require(0 <= gate["qubit"] < target["n_qubits"], "bad U3 endpoint")
            require(all(math.isfinite(gate[parameter]) for parameter in ("theta", "phi", "lambda")), "nonfinite U3")
            require(0.64 < gate["theta"] < 2.50, "small or nearly pi polar angle")
            require(all(0.25 <= abs(gate[parameter]) <= math.pi - 0.25 for parameter in ("phi", "lambda")), "nonmoderate azimuthal angle")
    require(counts == {"U3": target["max_u3"], "CNOT": target["max_cnot"]}, "budgets not exact")
    require(target["max_u3"] == 2 * target["max_cnot"] + target["n_qubits"], "wrong finite U3 budget")
    require(target["connectivity"] == [[qubit, qubit + 1] for qubit in range(target["n_qubits"] - 1)], "wrong linear connectivity")
    return counts


def direct_commutator_audit(matrix, qubit_count, stored):
    dimension = len(matrix)
    pairs = [(0, qubit_count - 1), (qubit_count - 1, 0), (qubit_count // 2, qubit_count // 2)]
    maximum_error = 0.0
    maximum_gram_error = 0.0
    for name, propagator in (("forward_U_P_Udag", matrix), ("backward_Udag_P_U", matrix.conj().T)):
        for source, destination in pairs:
            commutators = []
            for source_axis, source_pauli in enumerate(generation.PAULIS):
                evolved = propagator @ embed(source_pauli, source, qubit_count) @ propagator.conj().T
                for destination_axis, destination_pauli in enumerate(generation.PAULIS):
                    local = embed(destination_pauli, destination, qubit_count)
                    commutator = evolved @ local - local @ evolved
                    measured = float(np.linalg.norm(commutator) ** 2 / (2 * dimension))
                    expected = stored[name]["squared_commutators"][source][destination][source_axis][destination_axis]
                    maximum_error = max(maximum_error, abs(measured - expected))
                    commutators.append(commutator)
            gram = np.array([[np.vdot(first, second).real / (2 * dimension) for second in commutators] for first in commutators])
            eigenvalues = np.linalg.eigvalsh(gram)
            expected = np.array(stored[name]["axis_gram_eigenvalues"][source][destination])
            maximum_gram_error = max(maximum_gram_error, float(np.max(np.abs(eigenvalues - expected))))
    require(maximum_error < 2e-12 and maximum_gram_error < 2e-12, "independent direct commutator audit disagrees")
    return {"site_pairs_per_direction": len(pairs), "pauli_commutators_checked": 54,
            "maximum_direct_commutator_error": maximum_error, "maximum_direct_gram_eigenvalue_error": maximum_gram_error}


def analytic_self_checks():
    identity = np.eye(4, dtype=complex)
    controlled = [{"gate": "CNOT", "control": 0, "target": 1}]
    swap = controlled + [{"gate": "CNOT", "control": 1, "target": 0}] + controlled
    for gates, expected_rank in (([], 1), (controlled, 2), (swap, 4)):
        matrix = dense_unitary(2, gates)
        rank = generation.all_schmidt_statistics(matrix, 2)["chain_ranks"]
        require(rank == [expected_rank], "analytic operator-Schmidt self-check failed")
    causal = generation.causal_statistics(identity, 2)
    values = np.array(causal["forward_U_P_Udag"]["squared_commutators"])
    require(np.max(np.abs(values[0, 1])) < 1e-14, "identity incorrectly causally mixes sites")
    require(np.max(np.abs(values[0, 0] - 2 * (np.ones((3, 3)) - np.eye(3)))) < 1e-14, "Pauli squared commutator normalization failed")
    require(causal["minimum_axis_gram_eigenvalue"] == 0, "identity wrongly certifies arbitrary-axis mixing")
    for qubit in range(2):
        for pauli, (permutation, factors) in zip(generation.PAULIS, generation.pauli_actions(2)[qubit]):
            actual = factors[:, None] * identity[permutation]
            require(np.max(np.abs(actual - embed(pauli, qubit, 2))) < 1e-14, "Pauli action or endianness check failed")
    return {"passed": True, "cases": ["identity rank 1", "CNOT rank 2", "SWAP rank 4", "identity causal zeros", "Pauli norm and Y sign", "little endian embeddings"]}


def main():
    parser = argparse.ArgumentParser(description="Read-only independent verification; report stays in private scope.")
    parser.add_argument("--pool", type=Path, default=generation.PRIVATE_ROOT / "pool")
    parser.add_argument("--report", type=Path, default=generation.PRIVATE_ROOT / "verification.json")
    arguments = parser.parse_args()
    pool = arguments.pool.resolve()
    report_path = arguments.report.resolve()
    require(pool.is_relative_to(generation.PRIVATE_ROOT) and report_path.is_relative_to(generation.PRIVATE_ROOT), "out-of-scope path")
    os.umask(0o077)
    started = time.monotonic()
    kernel_path = generation.CONCEPT_ROOT / "evaluator/kernel.py"
    kernel_hash_at_start = generation.digest_file(kernel_path)
    self_checks = analytic_self_checks()
    metadata = kernel.parse_json((pool / "metadata.json").read_bytes())
    certificates = []
    require(6 <= metadata["candidate_count"] <= 10, "candidate count outside bounded request")
    for certificate in metadata["certificates"]:
        for kind in ("input", "witness", "statistics"):
            path = pool / certificate[kind]
            require(path.resolve().is_relative_to(pool), "certificate path escapes private pool")
            require(generation.digest_file(path) == certificate[kind + "_sha256"], "artifact hash mismatch")
        specification = kernel.parse_json((pool / certificate["input"]).read_bytes())
        witness = kernel.read_json(str(pool / certificate["witness"]))
        target = specification["targets"][0]
        gates = witness[target["id"]]
        counts = independent_gate_audit(gates, target)
        replay, schedule, phase = generation.make_circuit(certificate["private_seed"], target["n_qubits"], target["max_cnot"])
        require(replay == gates and phase == certificate["private_target_phase"], "seed replay mismatch")
        matrix = kernel.target_matrix(target)
        independent = dense_unitary(target["n_qubits"], gates)
        phase_aligned = independent * np.exp(1j * phase)
        error = float(np.max(np.abs(phase_aligned - matrix)))
        require(error < 1e-12, "independent full dense reconstruction failed")
        scored = kernel.score_payload(specification, witness)
        require(scored["target_met"] and scored["valid"], "saved witness fails current evaluator kernel")
        stored = kernel.parse_json((pool / certificate["statistics"]).read_bytes())
        recomputed = generation.all_schmidt_statistics(matrix, target["n_qubits"])
        require(recomputed["all_cuts_full_absolute_and_relative_rank"], "saved target has deficient rank")
        require(len(recomputed["cuts"]) == 2 ** (target["n_qubits"] - 1) - 1, "missing bipartitions")
        spectral_error = max(abs(first["effective_rank"] - second["effective_rank"])
                             for first, second in zip(recomputed["cuts"], stored["operator_schmidt"]["cuts"]))
        require(spectral_error < 1e-10, "stored Schmidt statistics disagree")
        direct_audit = direct_commutator_audit(matrix, target["n_qubits"], stored["heisenberg_causal_mixing"])
        causal = generation.causal_statistics(matrix, target["n_qubits"])
        require(causal["bidirectional_transpose_maximum_error"] < 2e-12, "bidirectional commutator relation failed")
        failures = generation.qualification_failures(recomputed, causal)
        require((not failures) == certificate["qualified"] and failures == certificate["qualification_failures"], "qualification replay mismatch")
        size_limit_rejects_input = False
        try:
            kernel.read_json(str(pool / certificate["input"]))
        except kernel.WitnessError:
            require((pool / certificate["input"]).stat().st_size > kernel.MAX_JSON_BYTES, "unexpected input parser error")
            size_limit_rejects_input = True
        require(size_limit_rejects_input == certificate["input_exceeds_kernel_read_json_limit"], "input size audit mismatch")
        updated_input_reader_passed = None
        if hasattr(kernel, "MAX_INPUT_JSON_BYTES"):
            capped_specification = kernel.read_json(str(pool / certificate["input"]), max_bytes=kernel.MAX_INPUT_JSON_BYTES)
            require(capped_specification == specification, "updated input reader disagrees with strict JSON parser")
            updated_input_reader_passed = True
        result = {"id": certificate["id"], "verified": True, "qualified": not failures,
                  "counts": counts, "seed_replay_exact": True,
                  "independent_target_maximum_entry_error": error, "evaluator": scored,
                  "recomputed_bipartitions": recomputed["bipartition_count"],
                  "recomputed_commutators": 18 * target["n_qubits"] ** 2,
                  "spectral_effective_rank_replay_error": spectral_error,
                  "direct_commutator_audit": direct_audit,
                  "kernel_default_witness_cap_rejects_input_size": size_limit_rejects_input,
                  "kernel_updated_input_cap_passed": updated_input_reader_passed}
        certificates.append(result)
        print(json.dumps({"id": result["id"], "verified": True, "qualified": result["qualified"]}), flush=True)
    report = {"private": True, "all_verified": True, "candidate_count": len(certificates),
              "qualified_count": sum(certificate["qualified"] for certificate in certificates),
              "analytic_self_checks": self_checks, "certificates": certificates,
              "manifest_sha256": generation.digest_file(pool / "metadata.json"),
              "validator_sha256": generation.digest_file(Path(__file__)),
              "kernel_sha256_at_start": kernel_hash_at_start,
              "kernel_sha256_at_finish": generation.digest_file(kernel_path),
              "generation_kernel_sha256": metadata["source_sha256"]["evaluator/kernel.py"],
              "kernel_matches_generation_snapshot": kernel_hash_at_start == metadata["source_sha256"]["evaluator/kernel.py"],
              "elapsed_seconds": time.monotonic() - started,
              "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
              "no_installation_or_participant_execution": True}
    generation.write_json(report_path, report)
    print(json.dumps({"all_verified": True, "count": len(certificates), "elapsed_seconds": report["elapsed_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
