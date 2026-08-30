import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import sys

sys.dont_write_bytecode = True
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.linalg import expm

ROOT = Path(__file__).resolve().parents[1]


def assemble_bits(model):
    sites = model["sites"]
    basis = [bits for bits in range(2 ** sites) if bin(bits).count("1") == model["up_spins"]]
    positions = {bits: position for position, bits in enumerate(basis)}
    size = len(basis)
    fields = np.zeros((sites, size, size), dtype=complex)
    nearest_xy = np.zeros_like(fields)
    nearest_zz = np.zeros_like(fields)
    next_xy = np.zeros_like(fields)
    next_zz = np.zeros_like(fields)
    currents = np.zeros_like(fields)
    for column, bits in enumerate(basis):
        for site in range(sites):
            first = (bits >> site) & 1
            fields[site, column, column] = first - 0.5
            for distance, exchange, diagonal in ((1, nearest_xy, nearest_zz), (2, next_xy, next_zz)):
                neighbor = (site + distance) % sites
                second = (bits >> neighbor) & 1
                diagonal[site, column, column] = (first - 0.5) * (second - 0.5)
                if first != second:
                    row = positions[bits ^ (1 << site) ^ (1 << neighbor)]
                    exchange[site, row, column] = 0.5
                    if distance == 1:
                        currents[site, row, column] = 0.5j * (second - first)
    drifts = []
    for member in model["calibrations"]:
        drift = model["nearest_exchange"] * (nearest_xy + (model["nearest_anisotropy"] + member["anisotropy_shift"]) * nearest_zz).sum(axis=0)
        drift += model["next_exchange"] * (1 + member["next_exchange_fraction"]) * (next_xy + model["next_anisotropy"] * next_zz).sum(axis=0)
        for site in range(sites):
            drift += (model["static_field"][site] + member["field_offset"] * model["field_error_profile"][site]) * fields[site]
        drifts.append(drift)
    controls = np.array([
        sum(coefficient * operator for coefficient, operator in zip(model["staggered_profile"], fields)),
        sum(coefficient * operator for coefficient, operator in zip(model["bond_profile"], nearest_xy + model["bond_control_anisotropy"] * nearest_zz)),
        sum(coefficient * operator for coefficient, operator in zip(model["current_profile"], currents)),
    ])
    initial = np.zeros((size, len(model["initial_bitstrings"])), dtype=complex)
    for column, bits in enumerate(model["initial_bitstrings"]):
        initial[positions[bits], column] = 1
    return np.array(basis), np.array(drifts), controls, initial


def main():
    public = ROOT / "participant" / "input"
    hidden = ROOT / "evaluator" / "hidden"
    hidden.mkdir(parents=True, exist_ok=True)
    if (public / "targets.npz").exists() or (hidden / "witness.json").exists():
        raise RuntimeError("Instance already generated; refusing to change fixed targets")
    specification = json.loads((public / "spec.json").read_text())
    model = json.loads((public / "model.json").read_text())
    seed = secrets.randbits(128)
    generator = np.random.default_rng(seed)
    limits = np.array(specification["amplitude_limits"])
    jump_limits = np.array(specification["adjacent_jump_limits"])
    pulse = np.zeros((specification["slices"], specification["channels"]))
    previous = np.zeros(3)
    for slice_index in range(specification["slices"]):
        lower = np.maximum(-0.94 * limits, previous - 0.9 * jump_limits)
        upper = np.minimum(0.94 * limits, previous + 0.9 * jump_limits)
        if slice_index == specification["slices"] - 1:
            lower = np.maximum(lower, -0.9 * jump_limits)
            upper = np.minimum(upper, 0.9 * jump_limits)
        pulse[slice_index] = generator.uniform(lower, upper)
        previous = pulse[slice_index]
    exposure = specification["slice_duration"] * np.sum((pulse / limits) ** 2)
    pulse *= min(1.0, np.sqrt(0.9 * specification["normalized_control_exposure_limit"] / exposure))
    basis, drifts, controls, initial = assemble_bits(model)
    targets = []
    for drift in drifts:
        states = initial.copy()
        for row in pulse:
            hamiltonian = drift + np.einsum("c,cij->ij", row, controls)
            states = expm(-1j * specification["slice_duration"] * hamiltonian) @ states
        targets.append(states)
    np.savez_compressed(public / "hamiltonians.npz", basis=basis, drifts=drifts, controls=controls, initial=initial)
    np.savez_compressed(public / "targets.npz", targets=np.array(targets))
    for filename in ("model.json", "spec.json", "targets.npz"):
        shutil.copyfile(public / filename, hidden / filename)
    (hidden / "witness.json").write_text(json.dumps({"schema_version": 1, "amplitudes": pulse.tolist()}, indent=2) + "\n")
    (hidden / "generation.json").write_text(json.dumps({"private_seed": str(seed), "target_propagator": "scipy.linalg.expm; direct bit-basis assembly", "shared_sequence": True, "public_target_members": 4, "register_dimension": 6, "private_witness_not_disclosed": True}, indent=2) + "\n")
    integrity = {filename: hashlib.sha256((hidden / filename).read_bytes()).hexdigest() for filename in ("model.json", "spec.json", "targets.npz")}
    (hidden / "integrity.json").write_text(json.dumps(integrity, indent=2) + "\n")
    print(json.dumps({"dimension": len(basis), "public_target_shape": list(np.array(targets).shape), "witness_exposure": float(specification["slice_duration"] * np.sum((pulse / limits) ** 2)), "targets_frozen": True}))


if __name__ == "__main__":
    main()
