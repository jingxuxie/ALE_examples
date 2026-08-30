"""BUILDER ONLY: deterministic planted instances. Never distribute this directory."""

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SPECIFICATIONS = [
    ("ladder_14", "ladder", 14, 7, 30, 9, 32, 10, 73019413),
    ("ladder_16", "ladder", 16, 8, 34, 10, 36, 11, 81473029),
    ("irregular_16", "irregular", 16, 8, 38, 11, 40, 12, 92615107),
    ("irregular_18", "irregular", 18, 9, 42, 12, 44, 13, 105827341),
]


def graph(size, family, rng):
    columns = size // 2
    if family == "ladder":
        edges = [(rail * columns + column, rail * columns + column + 1)
                 for rail in (0, 1) for column in range(columns - 1)]
        edges += [(column, columns + column) for column in range(columns)]
    else:
        edges = [(mode, (mode + 1) % size) for mode in range(size)]
        for first, second in ((0, 4), (2, 7), (5, 10), (8, 13), (11, size - 1)):
            edges.append((first, second))
    labels = rng.permutation(size)
    return sorted({tuple(sorted((int(labels[first]), int(labels[second])))) for first, second in edges})


def block_gate(size, gate):
    matrix = np.eye(size, dtype=complex)
    first, second = gate["u"], gate["v"]
    angle, phase = gate["theta"], gate["phi"]
    matrix[np.ix_([first, second], [first, second])] = [
        [math.cos(angle), -np.exp(-1j * phase) * math.sin(angle)],
        [np.exp(1j * phase) * math.sin(angle), math.cos(angle)]]
    return matrix


def connected(size, edges):
    seen = {0}
    while True:
        expanded = seen | {second for first, second in edges if first in seen} | {first for first, second in edges if second in seen}
        if expanded == seen:
            return len(seen) == size
        seen = expanded


def make_instance(specification):
    identifier, family, size, particles, count, depth, gate_budget, depth_budget, seed = specification
    rng = np.random.default_rng(seed)
    hardware = graph(size, family, rng)
    for trial in range(10000):
        occupied = sorted(int(mode) for mode in rng.choice(size, particles, replace=False))
        density = np.diag([float(mode in occupied) for mode in range(size)]).astype(complex)
        layers, support, changes = [], [], []
        last_partner = [-1] * size
        feasible = True
        for layer_index in range(depth):
            wanted = count // depth + int(layer_index < count % depth)
            for retry in range(100):
                chosen, used = [], set()
                for edge_index in rng.permutation(len(hardware)):
                    first, second = hardware[edge_index]
                    if first in used or second in used or (last_partner[first] == second and last_partner[second] == first):
                        continue
                    probe = {"u": first, "v": second, "theta": 0.61, "phi": 0.43}
                    rotation = block_gate(size, probe)
                    if np.linalg.norm(rotation @ density @ rotation.conj().T - density) < 0.15:
                        continue
                    chosen.append((first, second))
                    used.update((first, second))
                    if len(chosen) == wanted:
                        break
                if len(chosen) == wanted:
                    break
            if len(chosen) != wanted:
                feasible = False
                break
            layer = []
            for first, second in chosen:
                angle = float(rng.uniform(0.30, 1.12) * rng.choice([-1, 1]))
                gate = {"u": first, "v": second, "theta": angle, "phi": float(rng.uniform(-math.pi, math.pi))}
                rotation = block_gate(size, gate)
                updated = rotation @ density @ rotation.conj().T
                changes.append(float(np.linalg.norm(updated - density)))
                density = updated
                layer.append(gate)
                support.append((first, second))
                last_partner[first], last_partner[second] = second, first
            layers.append(layer)
        if not feasible or not connected(size, support):
            continue
        diagonal = np.diag(density).real
        nonzero_fraction = float(np.mean(np.abs(density) > 1e-9))
        if diagonal.min() < 0.035 or diagonal.max() > 0.965 or nonzero_fraction < 0.85 or min(changes) < 0.06:
            continue
        density = (density + density.conj().T) / 2
        instance = {"id": identifier, "family": family, "n_modes": size, "n_particles": particles,
                    "initial_occupied": occupied, "edges": [list(edge) for edge in hardware],
                    "target_projector": {"real": density.real.tolist(), "imag": density.imag.tolist()},
                    "budgets": {"max_gates": gate_budget, "max_depth": depth_budget},
                    "tolerances": {"projector_frobenius": 1e-8, "slater_infidelity": 1e-8}}
        diagnostic = {"id": identifier, "seed": seed, "accepted_trial": trial,
                      "planted_gates": count, "planted_depth": depth,
                      "gate_budget": gate_budget, "depth_budget": depth_budget,
                      "minimum_single_gate_deletion_error": min(changes),
                      "target_nonzero_fraction_at_1e-9": nonzero_fraction,
                      "minimum_occupation": float(diagonal.min()), "maximum_occupation": float(diagonal.max()),
                      "projector_integrity": float(np.linalg.norm(density @ density - density)),
                      "occupied_unoccupied_gap": float(np.diff(np.linalg.eigvalsh(density))[size - particles - 1]),
                      "generic_dense_state_givens_slots": particles * (size - particles)}
        return instance, {"id": identifier, "layers": layers}, diagnostic
    raise RuntimeError("generation rejection limit exceeded: " + identifier)


def encoded(value):
    return json.dumps(value, indent=2, allow_nan=False) + "\n"


def main():
    if (ROOT / "evaluator/hidden/freeze.json").exists():
        raise SystemExit("targets already frozen; generator refuses to overwrite")
    generated = [make_instance(specification) for specification in SPECIFICATIONS]
    targets = encoded({"version": 1, "task": "local_slater_v1", "instances": [item[0] for item in generated]})
    witness = encoded({"version": 1, "circuits": [item[1] for item in generated]})
    manifest = {"version": 1, "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
                "target_sha256": hashlib.sha256(targets.encode()).hexdigest(),
                "witness_sha256": hashlib.sha256(witness.encode()).hexdigest(),
                "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "policy": "Do not change targets or budgets after any participant attempt."}
    files = {"participant/input/instances.json": targets, "evaluator/hidden/targets.json": targets,
             "evaluator/hidden/witness/solution.json": witness, "evaluator/hidden/freeze.json": encoded(manifest),
             "evaluator/hidden/generation_diagnostics.json": encoded([item[2] for item in generated])}
    patch = "*** Begin Patch\n"
    for relative, content in files.items():
        if (ROOT / relative).exists():
            raise RuntimeError("refusing to overwrite " + relative)
        patch += "*** Add File: " + relative + "\n" + "".join("+" + line + "\n" for line in content.splitlines())
    patch += "*** End Patch\n"
    subprocess.run(["apply_patch"], input=patch, text=True, check=True, cwd=ROOT)
    print(encoded({"manifest": manifest, "diagnostics": [item[2] for item in generated]}), end="")


if __name__ == "__main__":
    main()
