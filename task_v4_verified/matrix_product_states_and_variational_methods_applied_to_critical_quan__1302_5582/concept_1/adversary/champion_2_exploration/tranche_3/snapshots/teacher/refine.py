import sys

sys.dont_write_bytecode = True

import time

import numpy as np

import optimizer
import teacher_engine
from contractor import hamiltonian_terms, measure


def project_parity(tensors, request, sector):
    if any(request["field"]) or sector not in ("even", "odd"):
        raise ValueError("Parity projection probe requires a zero-field Hamiltonian")
    projected = []
    charges = [np.array([0])]
    for site, tensor in enumerate(tensors):
        left, dimension, right = tensor.shape
        left_count = 1 if site == 0 else 2
        right_count = 1 if site == len(tensors) - 1 else 2
        expanded = np.zeros((left, left_count, dimension, right, right_count))
        for left_label in range(left_count):
            left_charge = 0 if site == 0 else left_label
            for right_label in range(right_count):
                right_charge = int(sector == "odd") if site == len(tensors) - 1 else right_label
                allowed = np.arange(dimension) % 2 == (left_charge ^ right_charge)
                expanded[:, left_label, :, :, right_label] = tensor * allowed[None, :, None]
        projected.append(expanded.reshape(left * left_count, dimension, right * right_count))
        charges.append(np.array([int(sector == "odd")]) if site == len(tensors) - 1
                       else np.tile(np.arange(2), right))
    optimizer.right_canonical(projected, charges)
    for site in range(len(projected) - 1):
        left, dimension, right = projected[site].shape
        row_charge = (charges[site][:, None] ^ (np.arange(dimension)[None, :] % 2)).ravel()
        vectors, values, basis, new_charge = optimizer.factor(
            projected[site].reshape(left * dimension, right), row_charge, charges[site + 1], request["bond_cap"])
        projected[site] = vectors.reshape(left, dimension, len(values))
        projected[site + 1] = np.tensordot(values[:, None] * basis, projected[site + 1], axes=(1, 0))
        charges[site + 1] = new_charge
    projected[-1] /= np.linalg.norm(projected[-1])
    measure(projected, dict(request, sector=sector))
    return projected


def infer_charges(tensors, request):
    if request["sector"] == "any":
        return None
    charges = [np.array([0])]
    for tensor in tensors:
        incoming = charges[-1][:, None] ^ (np.arange(tensor.shape[1])[None, :] % 2)
        weights = np.abs(tensor) ** 2
        populations = np.array([np.sum(weights * (incoming == charge)[:, :, None], axis=(0, 1))
                                for charge in (0, 1)])
        outgoing = populations.argmax(axis=0)
        wrong = populations[1 - outgoing, np.arange(tensor.shape[2])]
        if np.sum(wrong) > 1e-16 * max(1.0, np.sum(populations)):
            raise ValueError("Warm state is not in a block parity gauge")
        charges.append(outgoing)
    if charges[-1].item() != int(request["sector"] == "odd"):
        raise ValueError("Wrong boundary parity")
    return charges


def refine(tensors, request, budget_seconds=60.0, max_sweeps=8, callback=None):
    started = time.process_time()
    wall_started = time.monotonic()
    tensors = [tensor.copy() for tensor in tensors]
    charges = infer_charges(tensors, request)
    best = [tensor.copy() for tensor in tensors]
    best_energy = measure(best, request)["energy"]
    trajectory = []

    def checkpoint(label):
        nonlocal best, best_energy
        measured = measure(tensors, request)
        trajectory.append({"phase": label, "energy": measured["energy"],
                           "cpu_seconds": time.process_time() - started,
                           "wall_seconds": time.monotonic() - wall_started})
        if measured["energy"] < best_energy:
            best_energy = measured["energy"]
            best = [tensor.copy() for tensor in tensors]
            if callback is not None:
                callback(best, trajectory)

    mpo = teacher_engine.make_mpo(request)
    pair_deadline = started + 0.72 * budget_seconds
    for sweep in range(max_sweeps):
        if time.process_time() >= pair_deadline:
            break
        tensors, charges, complete = teacher_engine.sweep(
            tensors, charges, mpo, request["bond_cap"], 2e-11, pair_deadline)
        checkpoint("two_site_%d%s" % (sweep, "" if complete else "_partial"))
        if not complete:
            break
        if sweep >= 3 and abs(trajectory[-1]["energy"] - trajectory[-2]["energy"]) < 1e-11:
            break

    tensors = [tensor.copy() for tensor in best]
    charges = infer_charges(tensors, request)
    onsite, positions = hamiltonian_terms(request)
    couplings = request["coupling"]
    optimizer.right_canonical(tensors, charges)
    clock = optimizer.Clock(dict(request, budget_seconds=budget_seconds, wall_seconds=1200.0),
                            started, wall_started)
    length = len(tensors)
    empty = (np.zeros((1, 1)), np.zeros((1, 1)))
    rights = [None] * (length + 1)
    rights[length] = empty
    for site in range(length - 1, -1, -1):
        rights[site] = optimizer.right_step(rights[site + 1], tensors[site], onsite[site],
                                            positions[site], couplings[site] if site + 1 < length else 0.0)
    for sweep in range(12):
        lefts = [empty]
        for site in range(length):
            if clock.remaining() < 0.1:
                checkpoint("one_site_%d_partial" % sweep)
                return best, trajectory
            optimizer.site_update(tensors, charges, site, lefts[site], rights[site + 1], onsite,
                                  positions, couplings, 1, 2e-11, clock)
            lefts.append(optimizer.left_step(lefts[site], tensors[site], onsite[site], positions[site],
                                             couplings[site - 1] if site else 0.0))
        for site in range(length - 1, -1, -1):
            if clock.remaining() < 0.1:
                checkpoint("one_site_%d_partial" % sweep)
                return best, trajectory
            optimizer.site_update(tensors, charges, site, lefts[site], rights[site + 1], onsite,
                                  positions, couplings, -1, 2e-11, clock)
            rights[site] = optimizer.right_step(rights[site + 1], tensors[site], onsite[site],
                                                positions[site], couplings[site] if site + 1 < length else 0.0)
        checkpoint("one_site_%d" % sweep)
        if sweep >= 2 and abs(trajectory[-1]["energy"] - trajectory[-2]["energy"]) < 2e-12:
            break
    return best, trajectory
