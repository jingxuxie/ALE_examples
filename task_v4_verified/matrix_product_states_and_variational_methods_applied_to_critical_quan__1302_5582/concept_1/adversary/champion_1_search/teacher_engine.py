"""General finite-MPS optimizer with exact Z2 charges and bounded pair solves."""

import time

import numpy as np
from scipy.sparse.linalg import ArpackNoConvergence, LinearOperator, eigsh

from contractor import hamiltonian_terms, measure


class DeadlineReached(Exception):
    pass


def make_mpo(request):
    onsite, positions = hamiltonian_terms(request)
    identity = np.eye(request["local_dim"])
    result = []
    for site, local in enumerate(onsite):
        tensor = np.zeros((3, 3, len(local), len(local)))
        tensor[0, 0] = identity
        tensor[0, 2] = local
        tensor[1, 2] = positions[site]
        tensor[2, 2] = identity
        if site < len(onsite) - 1:
            tensor[0, 1] = -request["coupling"][site] * positions[site]
        if site == 0:
            tensor = tensor[:1]
        if site == len(onsite) - 1:
            tensor = tensor[:, 2:3]
        result.append(tensor)
    return result


def mean_field_starts(request, deadline):
    onsite, positions = hamiltonian_terms(request)
    length = request["n_sites"]
    wells = np.sqrt(np.maximum(0, -6 * np.asarray(request["mass2"]) / np.asarray(request["lambda4"])))
    fields = np.asarray(request["field"])
    seeds = [wells + 0.05, -wells - 0.05]
    if np.any(fields) and np.min(fields) < 0 < np.max(fields):
        seeds.append(np.where(fields >= 0, wells + 0.05, -wells - 0.05))
    candidates = []
    for initial in seeds:
        means = initial.copy()
        vectors = []
        for iteration in range(36):
            previous = means.copy()
            vectors = []
            for site in range(length):
                neighbor = 0.0
                if site:
                    neighbor += request["coupling"][site - 1] * means[site - 1]
                if site + 1 < length:
                    neighbor += request["coupling"][site] * means[site + 1]
                _, eigenvectors = np.linalg.eigh(onsite[site] - neighbor * positions[site])
                vector = eigenvectors[:, 0]
                means[site] = float(vector @ positions[site] @ vector)
                vectors.append(vector)
            if np.max(np.abs(means - previous)) < 2e-8 or time.process_time() > deadline:
                break
        energy = sum(float(vector @ local @ vector) for vector, local in zip(vectors, onsite))
        energy -= sum(coupling * means[site] * means[site + 1]
                      for site, coupling in enumerate(request["coupling"]))
        if not any(np.max(np.abs(means - old[2])) < 1e-4 for old in candidates):
            candidates.append((energy, vectors, means.copy()))
    candidates.sort(key=lambda entry: entry[0])
    return candidates


def initial_state(vectors, request):
    if request["sector"] == "any":
        return [vector.reshape(1, -1, 1).copy() for vector in vectors], None
    target = int(request["sector"] == "odd")
    physical = np.arange(request["local_dim"]) % 2
    if max(np.linalg.norm(vector[1::2]) for vector in vectors) < 1e-9:
        vectors = [vector.copy() for vector in vectors]
        if target:
            onsite, _ = hamiltonian_terms(request)
            odd_levels = [np.linalg.eigh(local[1::2, 1::2]) for local in onsite]
            site = int(np.argmin([values[0] - float(vector @ local @ vector)
                                  for (values, _), vector, local in zip(odd_levels, vectors, onsite)]))
            vectors[site][:] = 0
            vectors[site][1::2] = odd_levels[site][1][:, 0]
    charges = [np.array([0])] + [np.array([0, 1]) for _ in vectors[1:]] + [np.array([target])]
    tensors = []
    for site, vector in enumerate(vectors):
        allowed = (charges[site][:, None, None] ^ physical[None, :, None]
                   ^ charges[site + 1][None, None, :]) == 0
        tensors.append(allowed * vector[None, :, None])
    return right_canonical(tensors, charges)


def right_canonical(tensors, charges):
    tensors = [tensor.copy() for tensor in tensors]
    charges = None if charges is None else [charge.copy() for charge in charges]
    for site in range(len(tensors) - 1, 0, -1):
        left, physical, right = tensors[site].shape
        matrix = tensors[site].reshape(left, physical * right)
        if charges is None:
            orthogonal, triangular = np.linalg.qr(matrix.T)
            tensors[site] = orthogonal.T.reshape(orthogonal.shape[1], physical, right)
            tensors[site - 1] = np.tensordot(tensors[site - 1], triangular.T, axes=(2, 0))
            continue
        column_charges = (np.arange(physical)[:, None] % 2 ^ charges[site + 1][None, :]).ravel()
        blocks = []
        for charge in (0, 1):
            rows = np.flatnonzero(charges[site] == charge)
            columns = np.flatnonzero(column_charges == charge)
            if not len(rows) or not len(columns):
                continue
            left_vectors, values, right_vectors = np.linalg.svd(matrix[np.ix_(rows, columns)], full_matrices=False)
            rank = int(np.count_nonzero(values > 1e-14 * max(1.0, values[0])))
            if rank:
                blocks.append((charge, rows, columns, left_vectors[:, :rank] * values[:rank], right_vectors[:rank]))
        rank = sum(block[4].shape[0] for block in blocks)
        if rank == 0:
            raise ValueError("zero projected initialization")
        rotation = np.zeros((left, rank), dtype=matrix.dtype)
        canonical = np.zeros((rank, physical * right), dtype=matrix.dtype)
        new_charges = np.empty(rank, dtype=int)
        offset = 0
        for charge, rows, columns, transform, vectors in blocks:
            block_rank = vectors.shape[0]
            indices = np.arange(offset, offset + block_rank)
            rotation[np.ix_(rows, indices)] = transform
            canonical[np.ix_(indices, columns)] = vectors
            new_charges[indices] = charge
            offset += block_rank
        tensors[site] = canonical.reshape(rank, physical, right)
        tensors[site - 1] = np.tensordot(tensors[site - 1], rotation, axes=(2, 0))
        charges[site] = new_charges
    norm = np.linalg.norm(tensors[0])
    if norm == 0:
        raise ValueError("zero initial state")
    tensors[0] /= norm
    return tensors, charges


def left_step(environment, tensor, operator):
    temporary = np.tensordot(environment, tensor.conj(), axes=(0, 0))
    temporary = np.tensordot(temporary, operator, axes=([0, 2], [0, 2]))
    return np.tensordot(temporary, tensor, axes=([0, 3], [0, 1]))


def right_step(environment, tensor, operator):
    temporary = np.tensordot(tensor.conj(), environment, axes=(2, 0))
    temporary = np.tensordot(temporary, operator, axes=([1, 2], [2, 1]))
    return np.tensordot(temporary, tensor, axes=([1, 3], [2, 1]))


def apply_pair(left, left_mpo, right_mpo, right, theta):
    temporary = np.einsum("awb,bqsf->awqsf", left, theta, optimize=True)
    temporary = np.einsum("awqsf,wxpq->axpsf", temporary, left_mpo, optimize=True)
    temporary = np.einsum("axpsf,xyrs->ayprf", temporary, right_mpo, optimize=True)
    return np.einsum("ayprf,cyf->aprc", temporary, right, optimize=True)


def split_pair(vector, shape, cap, direction, left_charges, right_charges):
    matrix = vector.reshape(shape[0] * shape[1], shape[2] * shape[3])
    if left_charges is None:
        left_vectors, values, right_vectors = np.linalg.svd(matrix, full_matrices=False)
        rank = min(cap, len(values))
        left_vectors, values, right_vectors = left_vectors[:, :rank], values[:rank], right_vectors[:rank]
        new_charges = None
    else:
        row_charge = (left_charges[:, None] ^ (np.arange(shape[1])[None, :] % 2)).ravel()
        column_charge = ((np.arange(shape[2])[:, None] % 2) ^ right_charges[None, :]).ravel()
        blocks = []
        candidates = []
        for charge in (0, 1):
            rows = np.flatnonzero(row_charge == charge)
            columns = np.flatnonzero(column_charge == charge)
            if not len(rows) or not len(columns):
                continue
            block_left, block_values, block_right = np.linalg.svd(matrix[np.ix_(rows, columns)], full_matrices=False)
            block_id = len(blocks)
            blocks.append((charge, rows, columns, block_left, block_right))
            candidates.extend((float(value), block_id, index) for index, value in enumerate(block_values)
                              if value > 1e-14)
        candidates.sort(reverse=True)
        selected = candidates[:cap]
        rank = len(selected)
        left_vectors = np.zeros((matrix.shape[0], rank), dtype=matrix.dtype)
        right_vectors = np.zeros((rank, matrix.shape[1]), dtype=matrix.dtype)
        values = np.empty(rank)
        new_charges = np.empty(rank, dtype=int)
        for output_index, (value, block_id, column) in enumerate(selected):
            charge, rows, columns, block_left, block_right = blocks[block_id]
            left_vectors[rows, output_index] = block_left[:, column]
            right_vectors[output_index, columns] = block_right[column]
            values[output_index] = value
            new_charges[output_index] = charge
    values /= np.linalg.norm(values)
    if direction == "right":
        return (left_vectors.reshape(shape[0], shape[1], rank),
                (values[:, None] * right_vectors).reshape(rank, shape[2], shape[3]), new_charges)
    return ((left_vectors * values).reshape(shape[0], shape[1], rank),
            right_vectors.reshape(rank, shape[2], shape[3]), new_charges)


def optimize_pair(first, second, left, right, first_mpo, second_mpo, cap, direction,
                  left_charges, right_charges, tolerance, deadline):
    theta = np.tensordot(first, second, axes=(2, 0))
    shape = theta.shape
    indices = None
    if left_charges is not None:
        allowed = (left_charges[:, None, None, None] ^ (np.arange(shape[1])[None, :, None, None] % 2)
                   ^ (np.arange(shape[2])[None, None, :, None] % 2) ^ right_charges[None, None, None, :]) == 0
        indices = np.flatnonzero(allowed.ravel())
    starting = theta.ravel() if indices is None else theta.ravel()[indices]
    starting = starting / np.linalg.norm(starting)

    def matvec(vector):
        if time.process_time() >= deadline:
            raise DeadlineReached()
        if indices is None:
            full = vector
        else:
            full = np.zeros(theta.size, dtype=vector.dtype)
            full[indices] = vector
        applied = apply_pair(left, first_mpo, second_mpo, right, full.reshape(shape)).ravel()
        return applied if indices is None else applied[indices]

    operator = LinearOperator((starting.size, starting.size), matvec=matvec, dtype=starting.dtype)
    try:
        _, vectors = eigsh(operator, k=1, which="SA", v0=starting, tol=tolerance,
                           ncv=min(20, starting.size), maxiter=24)
        vector = vectors[:, 0]
    except ArpackNoConvergence as error:
        vector = error.eigenvectors[:, 0] if error.eigenvectors.shape[1] else starting
    if indices is not None:
        full = np.zeros(theta.size, dtype=vector.dtype)
        full[indices] = vector
        vector = full
    return split_pair(vector, shape, cap, direction, left_charges, right_charges)


def sweep(tensors, charges, mpo, cap, tolerance, deadline):
    tensors, charges = right_canonical(tensors, charges)
    length = len(tensors)
    rights = [None] * (length + 1)
    rights[length] = np.ones((1, 1, 1))
    for site in range(length - 1, -1, -1):
        rights[site] = right_step(rights[site + 1], tensors[site], mpo[site])
    lefts = [np.ones((1, 1, 1))]
    try:
        for site in range(length - 1):
            tensors[site], tensors[site + 1], new_charge = optimize_pair(
                tensors[site], tensors[site + 1], lefts[site], rights[site + 2], mpo[site], mpo[site + 1],
                cap, "right", None if charges is None else charges[site],
                None if charges is None else charges[site + 2], tolerance, deadline)
            if charges is not None:
                charges[site + 1] = new_charge
            lefts.append(left_step(lefts[site], tensors[site], mpo[site]))
        environment = np.ones((1, 1, 1))
        for site in range(length - 2, -1, -1):
            tensors[site], tensors[site + 1], new_charge = optimize_pair(
                tensors[site], tensors[site + 1], lefts[site], environment, mpo[site], mpo[site + 1],
                cap, "left", None if charges is None else charges[site],
                None if charges is None else charges[site + 2], tolerance, deadline)
            if charges is not None:
                charges[site + 1] = new_charge
            environment = right_step(environment, tensors[site + 1], mpo[site + 1])
    except DeadlineReached:
        return tensors, charges, False
    return tensors, charges, True


def optimize(request):
    budget = float(request["budget_seconds"])
    deadline = budget - (0.45 if budget < 10 else 0.8)
    starts = mean_field_starts(request, min(deadline * 0.12, time.process_time() + 0.4))
    mpo = make_mpo(request)
    candidates = []
    number_starts = 1 if request["sector"] != "any" or budget < 10 else min(2, len(starts))
    for _, vectors, means in starts[:number_starts]:
        tensors, charges = initial_state(vectors, request)
        measured = measure(tensors, request)
        candidates.append((measured["energy"], tensors, charges))
        if time.process_time() < deadline * 0.55:
            tensors, charges, complete = sweep(tensors, charges, mpo, min(4, request["bond_cap"]),
                                               1e-6, min(deadline, time.process_time() + max(1.0, budget * 0.18)))
            measured = measure(tensors, request)
            candidates.append((measured["energy"], tensors, charges))
    best_energy, tensors, charges = min(candidates, key=lambda candidate: candidate[0])
    best = [tensor.copy() for tensor in tensors]
    history = [{"energy": best_energy, "cpu_seconds": time.process_time(), "phase": "initialization"}]
    previous_energy = best_energy
    for sweep_index in range(20):
        if time.process_time() >= deadline - 0.04:
            break
        cap = request["bond_cap"]
        tolerance = 2e-8 if sweep_index == 0 else 2e-10
        tensors, charges, complete = sweep(tensors, charges, mpo, cap, tolerance, deadline)
        measured = measure(tensors, request)
        energy = measured["energy"]
        history.append({"energy": energy, "cpu_seconds": time.process_time(), "phase": "full_cap",
                        "sweep": sweep_index + 1, "complete": complete})
        if energy < best_energy:
            best_energy = energy
            best = [tensor.copy() for tensor in tensors]
        if not complete:
            break
        if sweep_index >= 1 and abs(energy - previous_energy) < 2e-9 * request["n_sites"]:
            break
        previous_energy = energy
    return best, history
