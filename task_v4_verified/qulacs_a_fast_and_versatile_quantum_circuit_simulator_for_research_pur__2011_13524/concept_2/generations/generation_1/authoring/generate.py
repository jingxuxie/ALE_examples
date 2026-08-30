import hashlib
import json
import math
import random
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from dense_reference import dense_unitary


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from kernel import circuit_unitary, score_payload, unitary_metrics


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def angle(generator):
    primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31]
    expression = (
        math.pi * math.sqrt(generator.choice(primes))
        + generator.randint(1, 10000) * math.sqrt(generator.choice(primes))
        + math.sqrt(generator.randint(10001, 90000) + 0.5)
    )
    return math.remainder(expression, 2.0 * math.pi)


def rotation(generator, qubit):
    return {
        "gate": "U3", "qubit": qubit,
        "theta": angle(generator), "phi": angle(generator), "lambda": angle(generator),
    }


def mixed_topology(generator, qubit_count, count):
    directed = [(left, left + 1) for left in range(qubit_count - 1)]
    directed += [(right + 1, right) for right in range(qubit_count - 1)]
    for attempt_index in range(100000):
        sequence = []
        while len(sequence) < count:
            candidates = [
                edge for edge in directed
                if not sequence or set(edge) != set(sequence[-1])
            ]
            sequence.append(generator.choice(candidates))
        unordered = [tuple(sorted(edge)) for edge in sequence]
        covers_directions = set(sequence) == set(directed)
        covers_cuts = all(unordered.count((left, left + 1)) >= 2 for left in range(qubit_count - 1))
        periodic = any(
            all(unordered[index] == unordered[index % period] for index in range(count))
            for period in range(1, count // 2 + 1)
        )
        if covers_directions and covers_cuts and not periodic:
            return sequence
    raise RuntimeError("could not construct a mixed nonperiodic topology")


def make_circuit(generator, qubit_count, cnot_count):
    gates = [rotation(generator, qubit) for qubit in range(qubit_count)]
    for control, destination in mixed_topology(generator, qubit_count, cnot_count):
        gates.append({"gate": "CNOT", "control": control, "target": destination})
        endpoints = [control, destination]
        generator.shuffle(endpoints)
        gates.extend(rotation(generator, qubit) for qubit in endpoints)
    return gates


def target_record(identifier, qubit_count, cnot_cap, u3_cap, matrix):
    return {
        "id": identifier, "n_qubits": qubit_count,
        "connectivity": [[qubit, qubit + 1] for qubit in range(qubit_count - 1)],
        "max_cnot": cnot_cap, "max_u3": u3_cap,
        "unitary_real": matrix.real.tolist(), "unitary_imag": matrix.imag.tolist(),
    }


def suite(targets):
    return {
        "schema_version": 1,
        "conventions": {"qubit_order": "little_endian", "gate_order": "first_listed_first_applied"},
        "tolerances": {"infidelity": 1e-8, "normalized_frobenius": 2e-4},
        "targets": targets,
    }


def schmidt_ranks(matrix, qubit_count):
    ranks = []
    for cut in range(1, qubit_count):
        lower = 2 ** cut
        upper = 2 ** (qubit_count - cut)
        reshaped = matrix.reshape(upper, lower, upper, lower).transpose(1, 3, 0, 2)
        ranks.append(int(np.linalg.matrix_rank(reshaped.reshape(lower ** 2, upper ** 2), tol=1e-10)))
    return ranks


def main():
    target_path = ROOT / "participant/input/targets.json"
    witness_path = ROOT / "evaluator/hidden/witness.json"
    if target_path.exists() or witness_path.exists():
        raise SystemExit("refusing to replace frozen targets or private witnesses")
    private_seed = secrets.token_hex(32)
    generator = random.Random(int(private_seed, 16))
    targets = []
    witnesses = {}
    audits = []
    for qubit_count, cnot_cap in ((4, 12), (5, 20)):
        identifier = "unitary_" + str(qubit_count) + "q"
        gates = make_circuit(generator, qubit_count, cnot_cap)
        dense = dense_unitary(qubit_count, gates)
        efficient = circuit_unitary(qubit_count, gates)
        crosscheck = float(np.max(np.abs(dense - efficient)))
        if crosscheck > 5e-13:
            raise RuntimeError("independent implementation disagreement")
        phase_angle = angle(generator)
        target = dense * np.exp(1j * phase_angle)
        ranks = schmidt_ranks(target, qubit_count)
        if min(ranks) < 4:
            raise RuntimeError("target lacks entangling operator structure across a cut")
        targets.append(target_record(identifier, qubit_count, cnot_cap, 80, target))
        witnesses[identifier] = gates
        audits.append({
            "id": identifier, "max_entry_crosscheck_error": crosscheck,
            "operator_schmidt_ranks": ranks, "private_target_phase": phase_angle,
            "metrics": unitary_metrics(target, efficient),
        })
    specification = suite(targets)
    achievement = score_payload(specification, witnesses)
    if not achievement["target_met"]:
        raise RuntimeError("constructed witnesses do not satisfy the public conditions")
    demo_gates = [{"gate": "CNOT", "control": 0, "target": 1}]
    demo = suite([target_record("demo_2q", 2, 1, 8, dense_unitary(2, demo_gates))])
    write_json(witness_path, witnesses)
    write_json(ROOT / "evaluator/hidden/generation_metadata.json", {
        "private_seed": private_seed,
        "angle_recipe": "generic irrational expressions involving square roots and pi, rounded to float64",
        "audits": audits,
        "warning": "private authoring material; never include in a participant bundle",
    })
    write_json(target_path, specification)
    write_json(ROOT / "participant/input/demo.json", demo)
    write_json(ROOT / "participant/input/demo_witness.json", {"demo_2q": demo_gates})
    manifest = {
        "schema_version": 1, "frozen_utc": datetime.now(timezone.utc).isoformat(),
        "targets_sha256": hashlib.sha256(target_path.read_bytes()).hexdigest(),
        "demo_sha256": hashlib.sha256((ROOT / "participant/input/demo.json").read_bytes()).hexdigest(),
        "fresh_agent_started": False,
    }
    write_json(ROOT / "evaluator/hidden/manifest.json", manifest)
    write_json(ROOT / "attempts/achievability/construction_report.json", {
        "core_score": achievement["core_score"], "target_met": achievement["target_met"],
        "independent_kernels_agree": True,
        "max_entry_crosscheck_error": max(audit["max_entry_crosscheck_error"] for audit in audits),
        "targets_sha256": manifest["targets_sha256"],
    })
    print(json.dumps({"targets_frozen": True, "private_witness_score": achievement["core_score"],
                      "targets_sha256": manifest["targets_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
