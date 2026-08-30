import os
import time

import numpy as np
from scipy.linalg import eigh, svd

from contractor import hamiltonian_terms


class Clock:
    def __init__(self, request, start_cpu, start_wall):
        self.cpu = start_cpu + request["budget_seconds"] - 0.30
        self.wall = start_wall + request.get("wall_seconds", 120.0) - 0.5

    def remaining(self):
        return min(self.cpu - time.process_time(), self.wall - time.monotonic())


def ground(matrix):
    return eigh(matrix, subset_by_index=(0, 0), check_finite=False)[1][:, 0]


def hartree(onsite, positions, couplings, request, sign):
    length = len(onsite)
    seeds = np.broadcast_to(sign, (length,))
    means = seeds * np.sqrt(np.maximum(0.0, -6 * np.array(request["mass2"])
                                      / np.array(request["lambda4"])))
    vectors = [None] * length
    for iteration in range(50):
        previous = means.copy()
        for site in range(length):
            force = 0.0
            if site:
                force += couplings[site - 1] * means[site - 1]
            if site + 1 < length:
                force += couplings[site] * means[site + 1]
            vectors[site] = ground(onsite[site] - force * positions[site])
            mean = vectors[site] @ positions[site] @ vectors[site]
            means[site] = 0.25 * means[site] + 0.75 * mean
        if np.max(np.abs(means - previous)) < 1e-8:
            break
    for site in range(length):
        force = 0.0
        if site:
            force += couplings[site - 1] * means[site - 1]
        if site + 1 < length:
            force += couplings[site] * means[site + 1]
        if abs(force) < 0.025:
            force += seeds[site] * 0.025
        vectors[site] = ground(onsite[site] - force * positions[site])
    return vectors


def product_energy(vectors, onsite, positions, couplings):
    means = [vector @ position @ vector for vector, position in zip(vectors, positions)]
    energy = sum(vector @ local @ vector for vector, local in zip(vectors, onsite))
    return energy - sum(coupling * means[site] * means[site + 1]
                        for site, coupling in enumerate(couplings))


def domain_seed(candidates, onsite, positions, couplings):
    length = len(onsite)
    means = np.array([[candidate[site] @ positions[site] @ candidate[site]
                       for candidate in candidates] for site in range(length)])
    local = np.array([[candidate[site] @ onsite[site] @ candidate[site]
                       for candidate in candidates] for site in range(length)])
    costs = local[0].copy()
    history = []
    for site in range(1, length):
        paths = costs[:, None] - couplings[site - 1] * means[site - 1][:, None] * means[site][None, :]
        parents = paths.argmin(axis=0)
        costs = local[site] + paths[parents, np.arange(2)]
        history.append(parents)
    labels = [int(costs.argmin())]
    for parents in reversed(history):
        labels.append(int(parents[labels[-1]]))
    return 1 - 2 * np.array(labels[::-1])


def initial_state(onsite, positions, couplings, request):
    vectors = hartree(onsite, positions, couplings, request, 1)
    length = len(vectors)
    dimension = len(vectors[0])
    physical_charge = np.arange(dimension) % 2
    constrained = request["sector"] != "any"
    if constrained:
        charges = [np.array([0])] + [np.array([0, 1]) for site in range(length - 1)]
        charges.append(np.array([int(request["sector"] == "odd")]))
        tensors = []
        for site, vector in enumerate(vectors):
            allowed = (charges[site][:, None, None] ^ physical_charge[None, :, None]
                       ^ charges[site + 1][None, None, :]) == 0
            tensors.append(allowed * vector[None, :, None])
    else:
        reflected = hartree(onsite, positions, couplings, request, -1)
        candidates = [vectors, reflected]
        signs = domain_seed(candidates, onsite, positions, couplings)
        if np.any(signs != signs[0]):
            domain = hartree(onsite, positions, couplings, request, signs)
            overlaps = [np.prod([abs(first @ second) for first, second in zip(domain, candidate)])
                        for candidate in candidates]
            if max(overlaps) < 1 - 1e-8:
                candidates.append(domain)
        for candidate in candidates[1:]:
            for site in range(length):
                if candidate[site] @ vectors[site] < 0:
                    candidate[site] *= -1
        energies = [product_energy(candidate, onsite, positions, couplings) for candidate in candidates]
        weights = np.full(len(candidates), 0.25)
        weights[int(np.argmin(energies))] = 1.0
        tensors = []
        charges = None
        for site in range(length):
            tensor = np.zeros((len(candidates), dimension, len(candidates)))
            for branch, candidate in enumerate(candidates):
                tensor[branch, :, branch] = candidate[site]
            if site == 0:
                tensor *= weights[:, None, None]
                tensor = tensor.sum(axis=0, keepdims=True)
            if site == length - 1:
                tensor = tensor.sum(axis=2, keepdims=True)
            tensors.append(tensor)
    return tensors, charges


def factor(matrix, row_charge, column_charge, cap, balanced=False):
    if row_charge is None:
        left, values, right = svd(matrix, full_matrices=False, check_finite=False)
        rank = min(cap, len(values))
        return left[:, :rank], values[:rank], right[:rank], None
    blocks = []
    candidates = []
    for charge in (0, 1):
        rows = np.flatnonzero(row_charge == charge)
        columns = np.flatnonzero(column_charge == charge)
        if not len(rows) or not len(columns):
            continue
        left, values, right = svd(matrix[np.ix_(rows, columns)], full_matrices=False,
                                  check_finite=False)
        blocks.append((charge, rows, columns, left, values, right))
        candidates.extend((value, charge, index) for index, value in enumerate(values))
    candidates.sort(reverse=True)
    selected = candidates[:cap]
    if balanced:
        selected = []
        for charge in (0, 1):
            selected.extend([entry for entry in candidates if entry[1] == charge][:cap // 2])
        selected.extend([entry for entry in candidates if entry not in selected][:cap-len(selected)])
    selected.sort(key=lambda item: (item[1], item[2]))
    rank = len(selected)
    left_result = np.zeros((matrix.shape[0], rank))
    right_result = np.zeros((rank, matrix.shape[1]))
    values_result = np.zeros(rank)
    charges = np.zeros(rank, dtype=int)
    for output, (value, charge, index) in enumerate(selected):
        block = next(block for block in blocks if block[0] == charge)
        left_result[block[1], output] = block[3][:, index]
        right_result[output, block[2]] = block[5][index]
        values_result[output] = value
        charges[output] = charge
    return left_result, values_result, right_result, charges


def right_canonical(tensors, charges):
    for site in range(len(tensors) - 1, 0, -1):
        left, dimension, right = tensors[site].shape
        row_charge = None if charges is None else charges[site]
        column_charge = None if charges is None else (np.arange(dimension)[:, None] % 2
                                                     ^ charges[site + 1][None, :]).ravel()
        orthogonal, values, right_vectors, new_charge = factor(
            tensors[site].reshape(left, dimension * right), row_charge, column_charge, left)
        tensors[site] = right_vectors.reshape(len(values), dimension, right)
        tensors[site - 1] = np.tensordot(tensors[site - 1], orthogonal * values, axes=(2, 0))
        if charges is not None:
            charges[site] = new_charge
    tensors[0] /= np.linalg.norm(tensors[0])


def compress(tensors, charges, cap):
    right_canonical(tensors, charges)
    for site in range(len(tensors)-1):
        left, dimension, right = tensors[site].shape
        row_charge = None if charges is None else (charges[site][:, None] ^ (np.arange(dimension)[None, :] % 2)).ravel()
        column_charge = None if charges is None else charges[site+1]
        orthogonal, values, following, new_charge = factor(tensors[site].reshape(left*dimension, right), row_charge, column_charge, cap)
        tensors[site] = orthogonal.reshape(left, dimension, len(values))
        tensors[site+1] = np.tensordot(values[:, None]*following, tensors[site+1], axes=(1, 0))
        if charges is not None:
            charges[site+1] = new_charge
    right_canonical(tensors, charges)


def left_block(environment, onsite, position, coupling):
    energy, edge = environment
    return (np.kron(energy, np.eye(len(onsite)))
            + np.kron(np.eye(len(energy)), onsite) - coupling * np.kron(edge, position))


def right_block(environment, onsite, position, coupling):
    energy, edge = environment
    return (np.kron(onsite, np.eye(len(energy)))
            + np.kron(np.eye(len(onsite)), energy) - coupling * np.kron(position, edge))


def left_step(environment, tensor, onsite, position, coupling):
    left, dimension, right = tensor.shape
    matrix = tensor.reshape(left * dimension, right)
    positioned = (position @ tensor.transpose(1, 0, 2).reshape(dimension, -1)).reshape(dimension, left, right).transpose(1, 0, 2)
    acted = (environment[0] @ tensor.reshape(left, -1)).reshape(tensor.shape)
    acted += np.diag(onsite)[None, :, None] * tensor
    if coupling:
        acted -= coupling * (environment[1] @ positioned.reshape(left, -1)).reshape(tensor.shape)
    energy = matrix.T @ acted.reshape(left * dimension, right)
    edge = matrix.T @ positioned.reshape(left * dimension, right)
    return (energy + energy.T) * 0.5, (edge + edge.T) * 0.5


def right_step(environment, tensor, onsite, position, coupling):
    left, dimension, right = tensor.shape
    matrix = tensor.reshape(left, dimension * right)
    positioned = (position @ tensor.transpose(1, 0, 2).reshape(dimension, -1)).reshape(dimension, left, right).transpose(1, 0, 2)
    acted = (tensor.reshape(-1, right) @ environment[0]).reshape(tensor.shape)
    acted += np.diag(onsite)[None, :, None] * tensor
    if coupling:
        acted -= coupling * (positioned.reshape(-1, right) @ environment[1]).reshape(tensor.shape)
    energy = acted.reshape(left, dimension * right) @ matrix.T
    edge = positioned.reshape(left, dimension * right) @ matrix.T
    return (energy + energy.T) * 0.5, (edge + edge.T) * 0.5


def davidson(matvec, diagonal, start, tolerance, max_steps, clock):
    vector = start / np.linalg.norm(start)
    image = matvec(vector)
    basis = np.empty((len(vector), min(max_steps + 1, 24)), order="F")
    images = np.empty_like(basis)
    projected = np.empty((basis.shape[1], basis.shape[1]))
    basis[:, 0] = vector
    images[:, 0] = image
    count = 1
    value = float(vector @ image)
    projected[0, 0] = value
    for iteration in range(max_steps):
        values, coefficients = eigh(projected[:count, :count], subset_by_index=(0, 0),
                                    check_finite=False)
        weights = coefficients[:, 0]
        value = values[0]
        vector = basis[:, :count] @ weights
        image = images[:, :count] @ weights
        residual = image - value * vector
        if (np.linalg.norm(residual) < tolerance or clock.remaining() < 0.03
                or iteration + 1 == max_steps):
            break
        denominator = diagonal - value
        denominator = np.maximum(denominator, 1e-3)
        direction = residual / denominator
        if count == basis.shape[1]:
            basis[:, 0] = vector
            images[:, 0] = image
            count = 1
            projected[0, 0] = float(vector @ image)
        for repeat in range(2):
            direction -= basis[:, :count] @ (basis[:, :count].T @ direction)
        norm = np.linalg.norm(direction)
        if norm < 1e-13:
            break
        direction /= norm
        basis[:, count] = direction
        new_image = matvec(direction)
        images[:, count] = new_image
        couplings = basis[:, :count].T @ new_image
        projected[:count, count] = couplings
        projected[count, :count] = couplings
        projected[count, count] = float(direction @ new_image)
        count += 1
    return vector, value


def lowest(matvec, diagonal, start, tolerance, max_steps, clock):
    if not os.environ.get('MPS_LOBPCG'):
        return davidson(matvec, diagonal, start, tolerance, max_steps, clock)
    vector = start / np.linalg.norm(start)
    image = matvec(vector)
    previous = previous_image = None
    for iteration in range(max_steps):
        value = float(vector @ image)
        residual = image-value*vector
        if np.linalg.norm(residual) < tolerance or clock.remaining() < .03:
            break
        direction = residual / np.maximum(diagonal-value, 1e-3)
        direction -= vector * (vector @ direction)
        if previous is not None:
            direction -= previous * (previous @ direction)
        norm = np.linalg.norm(direction)
        if norm < 1e-13:
            break
        direction /= norm
        direction_image = matvec(direction)
        if previous is None:
            basis = np.column_stack((vector, direction))
            images = np.column_stack((image, direction_image))
        else:
            basis = np.column_stack((vector, direction, previous))
            images = np.column_stack((image, direction_image, previous_image))
        projected = basis.T @ images
        values, coefficients = np.linalg.eigh((projected + projected.T)*.5)
        weights = coefficients[:, 0]
        previous = basis[:, 1:] @ weights[1:]
        previous_image = images[:, 1:] @ weights[1:]
        vector = basis @ weights
        image = images @ weights
        overlap = vector @ previous
        previous -= overlap*vector
        previous_image -= overlap*image
        norm = np.linalg.norm(previous)
        if norm < 1e-13:
            previous = previous_image = None
        else:
            previous /= norm
            previous_image /= norm
    return vector, float(vector @ image)


def effective_action(left_matrix, right_matrix, left_position, right_position,
                     coupling, row_charge, column_charge):
    shape = (len(left_matrix), len(right_matrix))
    if row_charge is None:
        def matvec(vector):
            matrix = vector.reshape(shape)
            return (left_matrix @ matrix + matrix @ right_matrix
                    - coupling * (left_position @ matrix @ right_position)).ravel()

        def pack(matrix):
            return matrix.ravel()

        def unpack(vector):
            return vector.reshape(shape)

        diagonal = (np.diag(left_matrix)[:, None] + np.diag(right_matrix)[None, :]
                    - coupling * np.diag(left_position)[:, None]
                    * np.diag(right_position)[None, :]).ravel()
        return matvec, diagonal, pack, unpack
    rows = [np.flatnonzero(row_charge == charge) for charge in (0, 1)]
    columns = [np.flatnonzero(column_charge == charge) for charge in (0, 1)]
    selectors = [np.ix_(rows[charge], columns[charge]) for charge in (0, 1)]
    shapes = [(len(rows[charge]), len(columns[charge])) for charge in (0, 1)]
    split = shapes[0][0] * shapes[0][1]
    left_blocks = [left_matrix[np.ix_(rows[charge], rows[charge])] for charge in (0, 1)]
    right_blocks = [right_matrix[np.ix_(columns[charge], columns[charge])] for charge in (0, 1)]
    left_cross = [left_position[np.ix_(rows[charge], rows[1 - charge])] for charge in (0, 1)]
    right_cross = [right_position[np.ix_(columns[1 - charge], columns[charge])] for charge in (0, 1)]

    def matvec(vector):
        blocks = [vector[:split].reshape(shapes[0]), vector[split:].reshape(shapes[1])]
        return np.concatenate([(left_blocks[charge] @ blocks[charge]
                                + blocks[charge] @ right_blocks[charge]
                                - coupling * (left_cross[charge] @ blocks[1 - charge]
                                              @ right_cross[charge])).ravel()
                               for charge in (0, 1)])

    def pack(matrix):
        return np.concatenate([matrix[selector].ravel() for selector in selectors])

    def unpack(vector):
        matrix = np.zeros(shape)
        matrix[selectors[0]] = vector[:split].reshape(shapes[0])
        matrix[selectors[1]] = vector[split:].reshape(shapes[1])
        return matrix

    diagonal = np.concatenate([(np.diag(left_blocks[charge])[:, None]
                                + np.diag(right_blocks[charge])[None, :]).ravel()
                               for charge in (0, 1)])
    return matvec, diagonal, pack, unpack


def pair_update(tensors, charges, site, left_environment, right_environment,
                onsite, positions, couplings, cap, direction, tolerance, max_steps, clock):
    first, second = tensors[site:site + 2]
    left, dimension, middle = first.shape
    right = second.shape[2]
    theta = (first.reshape(left * dimension, middle)
             @ second.reshape(middle, dimension * right))
    left_matrix = left_block(left_environment, onsite[site], positions[site],
                             couplings[site - 1] if site else 0.0)
    right_matrix = right_block(right_environment, onsite[site + 1], positions[site + 1],
                               couplings[site + 1] if site + 2 < len(tensors) else 0.0)
    left_position = np.kron(np.eye(left), positions[site])
    right_position = np.kron(positions[site + 1], np.eye(right))
    row_charge = column_charge = None
    if charges is not None:
        physical = np.arange(dimension) % 2
        row_charge = (charges[site][:, None] ^ physical[None, :]).ravel()
        column_charge = (physical[:, None] ^ charges[site + 2][None, :]).ravel()
    matvec, diagonal, pack, unpack = effective_action(
        left_matrix, right_matrix, left_position, right_position,
        couplings[site], row_charge, column_charge)
    vector, energy = lowest(matvec, diagonal, pack(theta), tolerance, max_steps, clock)
    matrix = unpack(vector)
    left_vectors, values, right_vectors, new_charge = factor(matrix, row_charge, column_charge, cap)
    norm = np.linalg.norm(values)
    discarded = max(0.0, 1.0 - norm * norm)
    values /= norm
    rank = len(values)
    if direction == 1:
        tensors[site] = left_vectors.reshape(left, dimension, rank)
        tensors[site + 1] = (values[:, None] * right_vectors).reshape(rank, dimension, right)
    else:
        tensors[site] = (left_vectors * values).reshape(left, dimension, rank)
        tensors[site + 1] = right_vectors.reshape(rank, dimension, right)
    if charges is not None:
        charges[site + 1] = new_charge
    return energy, discarded


def site_update(tensors, charges, site, left_environment, right_environment,
                onsite, positions, couplings, direction, tolerance, clock,
                cap=None, noise=0.0, max_steps=24, balanced=True):
    left, dimension, right = tensors[site].shape
    left_energy, left_position = left_environment
    right_energy, right_position = right_environment
    def diagonalize(matrix, charge):
        if charge is None:
            return eigh(matrix, check_finite=False)
        values = np.zeros(len(matrix))
        vectors = np.zeros_like(matrix)
        for parity in (0, 1):
            indices = np.flatnonzero(charge == parity)
            if len(indices):
                energies, rotation = eigh(matrix[np.ix_(indices, indices)], check_finite=False)
                values[indices] = energies
                vectors[np.ix_(indices, indices)] = rotation
        return values, vectors
    left_values, left_rotation = diagonalize(left_energy, None if charges is None else charges[site])
    right_values, right_rotation = diagonalize(right_energy, None if charges is None else charges[site+1])
    left_position = left_rotation.T @ left_position @ left_rotation
    right_position = right_rotation.T @ right_position @ right_rotation
    coupling = couplings[site] if site + 1 < len(tensors) else 0.0
    row_charge = column_charge = None
    if charges is not None:
        row_charge = (charges[site][:, None] ^ (np.arange(dimension)[None, :] % 2)).ravel()
        column_charge = charges[site + 1]
    shape = (left, dimension, right)
    allowed = None if charges is None else np.flatnonzero((row_charge[:, None] == column_charge[None, :]).ravel())
    def pack(matrix):
        return matrix.ravel() if allowed is None else matrix.ravel()[allowed]
    def unpack(vector):
        if allowed is None:
            return vector.reshape(left * dimension, right)
        result = np.zeros(left * dimension * right)
        result[allowed] = vector
        return result.reshape(left * dimension, right)
    local_diagonal = np.diag(onsite[site])[None, :, None]
    full_diagonal = left_values[:, None, None] + local_diagonal + right_values[None, None, :]
    left_coupling = couplings[site - 1] if site else 0.0
    def matvec(vector):
        tensor = unpack(vector).reshape(shape)
        positioned = (positions[site] @ tensor.transpose(1, 0, 2).reshape(dimension, -1)).reshape(dimension, left, right).transpose(1, 0, 2)
        result = full_diagonal * tensor
        if left_coupling:
            result -= left_coupling * (left_position @ positioned.reshape(left, -1)).reshape(shape)
        if coupling:
            result -= coupling * (positioned.reshape(-1, right) @ right_position).reshape(shape)
        return pack(result)
    diagonal = full_diagonal.copy()
    diagonal -= left_coupling * np.diag(left_position)[:, None, None] * np.diag(positions[site])[None, :, None]
    diagonal -= coupling * np.diag(positions[site])[None, :, None] * np.diag(right_position)[None, None, :]
    diagonal = pack(diagonal)
    rotated = (left_rotation.T @ tensors[site].reshape(left, -1)).reshape(left*dimension, right) @ right_rotation
    start = pack(rotated)
    if os.environ.get('MPS_NATIVE'):
        from native import lowest as native_lowest
        vector, energy = native_lowest(left, dimension, right, full_diagonal,
            positions[site], left_position, right_position, left_coupling, coupling,
            allowed, diagonal, start, tolerance, max_steps, clock)
    else:
        vector, energy = lowest(matvec, diagonal, start, tolerance, max_steps, clock)
    tensor = (left_rotation @ unpack(vector).reshape(left, -1)).reshape(left*dimension, right) @ right_rotation.T
    tensor = tensor.reshape(left, dimension, right)
    if direction == 1 and site + 1 < len(tensors):
        matrix = tensor.reshape(left * dimension, right)
        if noise:
            expansion = (positions[site] @ tensor.transpose(1, 0, 2).reshape(dimension, -1)).reshape(dimension, left, right).transpose(1, 0, 2).reshape(left * dimension, right)
            expansion *= np.sqrt(noise) / max(np.linalg.norm(expansion), 1e-15)
            expanded = np.concatenate((matrix, expansion), axis=1)
            expanded_charge = None if charges is None else np.concatenate((column_charge, 1-column_charge))
            left_vectors, values, right_vectors, new_charge = factor(
                expanded, row_charge, expanded_charge, cap, balanced)
            rank = len(values)
            tensors[site] = left_vectors.reshape(left, dimension, rank)
            tensors[site + 1] = np.tensordot(left_vectors.T @ matrix,
                                            tensors[site + 1], axes=(1, 0))
            tensors[site + 1] /= np.linalg.norm(tensors[site + 1])
            if charges is not None:
                charges[site + 1] = new_charge
            return energy
        left_vectors, values, right_vectors, new_charge = factor(
            tensor.reshape(left * dimension, right), row_charge, column_charge, right)
        rank = len(values)
        tensors[site] = left_vectors.reshape(left, dimension, rank)
        tensors[site + 1] = np.tensordot(values[:, None] * right_vectors,
                                        tensors[site + 1], axes=(1, 0))
        if charges is not None:
            charges[site + 1] = new_charge
    elif direction == -1 and site > 0:
        row_charge = None if charges is None else charges[site]
        column_charge = None if charges is None else ((np.arange(dimension)[:, None] % 2)
                                                     ^ charges[site + 1][None, :]).ravel()
        matrix = tensor.reshape(left, dimension * right)
        if noise:
            expansion = np.einsum('pq,aqb->apb', positions[site], tensor).reshape(left, dimension * right)
            expansion *= np.sqrt(noise) / max(np.linalg.norm(expansion), 1e-15)
            expanded = np.concatenate((matrix, expansion), axis=0)
            expanded_charge = None if charges is None else np.concatenate((row_charge, 1-row_charge))
            left_vectors, values, right_vectors, new_charge = factor(
                expanded, expanded_charge, column_charge, cap, balanced)
            rank = len(values)
            tensors[site] = right_vectors.reshape(rank, dimension, right)
            tensors[site - 1] = np.tensordot(tensors[site - 1], matrix @ right_vectors.T, axes=(2, 0))
            tensors[site - 1] /= np.linalg.norm(tensors[site - 1])
            if charges is not None:
                charges[site] = new_charge
            return energy
        left_vectors, values, right_vectors, new_charge = factor(
            tensor.reshape(left, dimension * right), row_charge, column_charge, left)
        rank = len(values)
        tensors[site] = right_vectors.reshape(rank, dimension, right)
        tensors[site - 1] = np.tensordot(tensors[site - 1], left_vectors * values, axes=(2, 0))
        if charges is not None:
            charges[site] = new_charge
    else:
        tensors[site] = tensor
    return energy


def local_basis(onsite, positions, constrained):
    transforms = []
    for site in range(len(onsite)):
        dimension = len(onsite[site])
        if constrained:
            transform = np.zeros((dimension, dimension))
            for charge in (0, 1):
                indices = np.arange(charge, dimension, 2)
                transform[np.ix_(indices, indices)] = eigh(
                    onsite[site][np.ix_(indices, indices)], check_finite=False)[1]
        else:
            transform = eigh(onsite[site], check_finite=False)[1]
        onsite[site] = transform.T @ onsite[site] @ transform
        positions[site] = transform.T @ positions[site] @ transform
        transforms.append(transform)
    return transforms


def restore_basis(tensors, transforms):
    return [np.einsum("ps,asb->apb", transform, tensor, optimize=True)
            for tensor, transform in zip(tensors, transforms)]


def optimize(request, start_cpu=None, start_wall=None, pair_sweeps=0):
    start_cpu = time.process_time() if start_cpu is None else start_cpu
    start_wall = time.monotonic() if start_wall is None else start_wall
    clock = Clock(request, start_cpu, start_wall)
    if request['sector'] == 'any' and not np.any(request['field']):
        request = dict(request, sector='even')
    onsite, positions = hamiltonian_terms(request)
    transforms = local_basis(onsite, positions, request["sector"] != "any")
    def finish(tensors, charges):
        if max(tensor.shape[2] for tensor in tensors) > request['bond_cap']:
            compress(tensors, charges, request['bond_cap'])
        return restore_basis(tensors, transforms)
    couplings = request["coupling"]
    tensors, charges = initial_state(onsite, positions, couplings, request)
    right_canonical(tensors, charges)
    length = len(tensors)
    empty = (np.zeros((1, 1)), np.zeros((1, 1)))
    right_environments = [None] * (length + 1)
    right_environments[length] = empty
    for site in range(length - 1, -1, -1):
        right_environments[site] = right_step(
            right_environments[site + 1], tensors[site], onsite[site], positions[site],
            couplings[site] if site + 1 < length else 0.0)
    previous_energy = float("inf")
    for sweep in range(pair_sweeps):
        cap = min(request["bond_cap"], 4 if sweep == 0 else request["bond_cap"])
        tolerance = 1e-5 if sweep == 0 else (1e-7 if sweep < 3 else 1e-9)
        max_steps = 36 if sweep == 0 else 20
        left_environments = [empty]
        energy = previous_energy
        discarded = 0.0
        for site in range(length - 1):
            if clock.remaining() < 0.06:
                return finish(tensors, charges)
            energy, loss = pair_update(tensors, charges, site, left_environments[site],
                                       right_environments[site + 2], onsite, positions,
                                       couplings, cap, 1, tolerance, max_steps, clock)
            discarded = max(discarded, loss)
            left_environments.append(left_step(left_environments[site], tensors[site],
                                                onsite[site], positions[site],
                                                couplings[site - 1] if site else 0.0))
        right_environments[length] = empty
        for site in range(length - 2, -1, -1):
            if clock.remaining() < 0.06:
                return finish(tensors, charges)
            energy, loss = pair_update(tensors, charges, site, left_environments[site],
                                       right_environments[site + 2], onsite, positions,
                                       couplings, cap, -1, tolerance, max_steps, clock)
            discarded = max(discarded, loss)
            right_environments[site + 1] = right_step(
                right_environments[site + 2], tensors[site + 1], onsite[site + 1],
                positions[site + 1], couplings[site + 1] if site + 2 < length else 0.0)
        if os.environ.get("MPS_DEBUG"):
            print(sweep, cap, energy, discarded, clock.remaining(), flush=True)
        if sweep >= 2 and abs(previous_energy - energy) < 1e-8:
            break
        previous_energy = energy
    previous_energy = float("inf")
    extra = int(os.environ.get('MPS_EXTRA', '0'))
    for sweep in range(100):
        previous_tensors = [tensor.copy() for tensor in tensors]
        previous_charges = None if charges is None else [charge.copy() for charge in charges]
        cap = min(request['bond_cap'], [4, 8, 12, request['bond_cap']][min(sweep, 3)])
        if os.environ.get('MPS_GROW'):
            cap = min(request['bond_cap'], 8 if sweep == 0 else request['bond_cap'])
        if extra and 3 <= sweep < 10:
            cap += extra
        if extra and sweep == 10:
            compress(tensors, charges, request['bond_cap'])
            for site in range(length - 1, -1, -1):
                right_environments[site] = right_step(
                    right_environments[site + 1], tensors[site], onsite[site], positions[site],
                    couplings[site] if site + 1 < length else 0.0)
        noise = max(1e-12, 1e-3 * 0.1**max(0, sweep-2))
        if os.environ.get('MPS_NOISE') and sweep >= 4:
            noise = float(os.environ['MPS_NOISE'])
        tolerance = 1e-4 if sweep < 4 else (1e-6 if sweep < 8 else 1e-8)
        left_environments = [empty]
        for site in range(length):
            if clock.remaining() < 0.05:
                return finish(tensors, charges)
            edge_update = os.environ.get('MPS_EDGES') and charges is not None and sweep == 5 and site in (0, 1, length-3, length-2)
            if edge_update:
                energy, loss = pair_update(tensors, charges, site, left_environments[site],
                                          right_environments[site+2], onsite, positions,
                                          couplings, cap, 1, 1e-7, 20, clock)
            else:
                energy = site_update(tensors, charges, site, left_environments[site],
                                  right_environments[site + 1], onsite, positions,
                                  couplings, 1, tolerance, clock, cap, noise, 16,
                                  (not extra or sweep < 10) and (not os.environ.get('MPS_EDGES') or sweep < 5))
            left_environments.append(left_step(left_environments[site], tensors[site],
                                                onsite[site], positions[site],
                                                couplings[site - 1] if site else 0.0))
        for site in range(length - 1, -1, -1):
            if clock.remaining() < 0.05:
                return finish(tensors, charges)
            energy = site_update(tensors, charges, site, left_environments[site],
                                  right_environments[site + 1], onsite, positions,
                                  couplings, -1, tolerance, clock, cap, noise, 16,
                                  (not extra or sweep < 10) and (not os.environ.get('MPS_EDGES') or sweep < 5))
            right_environments[site] = right_step(
                right_environments[site + 1], tensors[site], onsite[site], positions[site],
                couplings[site] if site + 1 < length else 0.0)
        if os.environ.get("MPS_DEBUG"):
            print("single", sweep, energy, clock.remaining(), flush=True)
        if os.environ.get('MPS_ACCELERATE') and sweep >= 4 and clock.remaining() > 0.5:
            from acceleration import extrapolate
            accelerated = extrapolate(tensors, previous_tensors, charges, previous_charges,
                                      energy, previous_energy, onsite, positions, couplings, cap)
            if accelerated is not None:
                tensors, charges, energy = accelerated
                for site in range(length - 1, -1, -1):
                    right_environments[site] = right_step(
                        right_environments[site + 1], tensors[site], onsite[site], positions[site],
                        couplings[site] if site + 1 < length else 0.0)
                if os.environ.get('MPS_DEBUG'):
                    print('accelerated', sweep, energy, clock.remaining(), flush=True)
        if sweep >= 13 and abs(previous_energy - energy) < 2e-11:
            break
        previous_energy = energy
    return finish(tensors, charges)
