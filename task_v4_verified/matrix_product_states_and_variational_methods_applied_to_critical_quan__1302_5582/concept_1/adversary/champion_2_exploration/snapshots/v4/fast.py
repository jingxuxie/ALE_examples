import os
import time

import numpy as np
from scipy.linalg.lapack import dsyev

from contractor import hamiltonian_terms
from optimizer import (Clock, effective_action, factor, initial_state, local_basis,
                       qr_factor, restore_basis, right_canonical)


def lowest(matvec, diagonal, start, tolerance, max_steps, clock):
    vector = start / np.sqrt(start @ start)
    image = matvec(vector)
    basis = np.empty((len(vector), min(max_steps, 24)), order='F')
    images = np.empty_like(basis)
    projected = np.empty((basis.shape[1], basis.shape[1]), order='F')
    basis[:, 0] = vector
    images[:, 0] = image
    count = 1
    projected[0, 0] = vector @ image
    for iteration in range(max_steps):
        values, coefficients, _ = dsyev(projected[:count, :count], lower=1)
        weights = coefficients[:, 0]
        value = values[0]
        vector = basis[:, :count] @ weights
        image = images[:, :count] @ weights
        residual = image - value * vector
        if residual @ residual < tolerance * tolerance or iteration + 1 == max_steps:
            break
        if iteration % 4 == 0 and clock.remaining() < 0.03:
            break
        direction = residual / np.maximum(diagonal - value, 1e-3)
        if count == basis.shape[1]:
            basis[:, 0] = vector
            images[:, 0] = image
            count = 1
            projected[0, 0] = value
        for repeat in range(2):
            direction -= basis[:, :count] @ (basis[:, :count].T @ direction)
        norm = np.sqrt(direction @ direction)
        if norm < 1e-13:
            break
        direction /= norm
        basis[:, count] = direction
        new_image = matvec(direction)
        images[:, count] = new_image
        projected[count, :count] = basis[:, :count].T @ new_image
        projected[count, count] = direction @ new_image
        count += 1
    return vector, value


def diagonalize(matrix, charges):
    if charges is None:
        return dsyev(matrix, lower=1)[:2]
    values = np.empty(len(matrix))
    vectors = np.zeros_like(matrix)
    for charge in (0, 1):
        indices = np.flatnonzero(charges == charge)
        if len(indices):
            values[indices], vectors[np.ix_(indices, indices)], _ = dsyev(matrix[np.ix_(indices, indices)], lower=1)
    return values, vectors


def extrapolate(tensors, previous, charges, amount):
    aligned = [tensor.copy() for tensor in tensors]
    for site in range(len(tensors) - 1, 0, -1):
        if aligned[site].shape != previous[site].shape:
            return None, None
        left, dimension, right = aligned[site].shape
        overlap = aligned[site].reshape(left, dimension * right) @ previous[site].reshape(left, dimension * right).T
        charge = None if charges is None else charges[site]
        left_vectors, _, right_vectors, _ = factor(overlap, charge, charge, left)
        rotation = left_vectors @ right_vectors
        aligned[site] = (rotation.T @ aligned[site].reshape(left, dimension * right)).reshape(left, dimension, right)
        aligned[site - 1] = np.tensordot(aligned[site - 1], rotation, axes=(2, 0))
    if np.sum(aligned[0] * previous[0]) < 0:
        aligned[0] *= -1
    trial = [current + amount * (current - old) for current, old in zip(aligned, previous)]
    trial_charges = None if charges is None else [charge.copy() for charge in charges]
    right_canonical(trial, trial_charges)
    return trial, trial_charges


def physical_action(operator, tensor):
    left, dimension, right = tensor.shape
    return (operator @ tensor.transpose(1, 0, 2).reshape(dimension, left * right)).reshape(
        dimension, left, right).transpose(1, 0, 2)


def shift_basis(tensors, onsite, positions, transforms, couplings):
    density = np.ones((1, 1))
    means = []
    for tensor, position in zip(tensors, positions):
        left, dimension, right = tensor.shape
        matrix = tensor.reshape(left, dimension * right)
        image = physical_action(position, tensor).reshape(left, dimension * right)
        means.append(float(np.sum(density * (matrix @ image.T))))
        density = tensor.reshape(left * dimension, right).T @ (density @ matrix).reshape(left * dimension, right)
    for site in range(len(tensors)):
        force = (couplings[site - 1] * means[site - 1] if site else 0.0)
        if site + 1 < len(tensors):
            force += couplings[site] * means[site + 1]
        shifted = onsite[site] - force * positions[site] + 0.5 * force * means[site] * np.eye(len(onsite[site]))
        values, transform = diagonalize(shifted, None)
        onsite[site] = np.diag(values)
        positions[site] = transform.T @ (positions[site] - means[site] * np.eye(len(shifted))) @ transform
        tensors[site] = physical_action(transform.T, tensors[site])
        transforms[site] = transforms[site] @ transform


def left_step(environment, tensor, onsite, position, coupling):
    left, dimension, right = tensor.shape
    energy, edge = environment
    position_tensor = physical_action(position, tensor)
    image = physical_action(onsite, tensor)
    image += (energy @ tensor.reshape(left, dimension * right)).reshape(tensor.shape)
    image -= coupling * (edge @ position_tensor.reshape(left, dimension * right)).reshape(tensor.shape)
    matrix = tensor.reshape(left * dimension, right)
    energy = matrix.T @ image.reshape(left * dimension, right)
    edge = matrix.T @ position_tensor.reshape(left * dimension, right)
    return (energy + energy.T) * 0.5, (edge + edge.T) * 0.5


def right_step(environment, tensor, onsite, position, coupling):
    left, dimension, right = tensor.shape
    energy, edge = environment
    position_tensor = physical_action(position, tensor)
    image = physical_action(onsite, tensor)
    image += (tensor.reshape(left * dimension, right) @ energy).reshape(tensor.shape)
    image -= coupling * (position_tensor.reshape(left * dimension, right) @ edge).reshape(tensor.shape)
    matrix = tensor.reshape(left, dimension * right)
    energy = image.reshape(left, dimension * right) @ matrix.T
    edge = position_tensor.reshape(left, dimension * right) @ matrix.T
    return (energy + energy.T) * 0.5, (edge + edge.T) * 0.5


def center_energy(tensor, left_environment, right_environment, onsite, position,
                  left_coupling, right_coupling):
    left, dimension, right = tensor.shape
    left_energy, left_position = left_environment
    right_energy, right_position = right_environment
    position_tensor = physical_action(position, tensor)
    image = physical_action(onsite, tensor)
    image += (left_energy @ tensor.reshape(left, dimension * right)).reshape(tensor.shape)
    image += (tensor.reshape(left * dimension, right) @ right_energy).reshape(tensor.shape)
    image -= left_coupling * (left_position @ position_tensor.reshape(left, dimension * right)).reshape(tensor.shape)
    image -= right_coupling * (position_tensor.reshape(left * dimension, right) @ right_position).reshape(tensor.shape)
    return float(np.sum(tensor * image) / np.sum(tensor * tensor))


def reduced_pair(tensors, charges, site, left_environment, right_environment,
                 onsite, positions, couplings, direction, cap, tolerance,
                 max_steps, clock):
    first, second = tensors[site:site + 2]
    left, dimension, middle = first.shape
    right = second.shape[2]
    first_matrix = first.reshape(left * dimension, middle)
    second_matrix = second.reshape(middle, dimension * right)
    left_extension = physical_action(positions[site], first).reshape(left * dimension, middle)
    right_extension = physical_action(positions[site + 1], second).reshape(middle, dimension * right)
    physical = np.arange(dimension) % 2
    row_charge = column_charge = expanded_charge = None
    if charges is not None:
        row_charge = (charges[site][:, None] ^ physical[None, :]).ravel()
        column_charge = (physical[:, None] ^ charges[site + 2][None, :]).ravel()
        expanded_charge = np.concatenate((charges[site + 1], charges[site + 1] ^ 1))
    left_basis, _, _, left_charge = factor(np.concatenate((first_matrix, left_extension), axis=1),
        row_charge, expanded_charge, 2 * middle)
    _, _, right_basis, right_charge = factor(np.concatenate((second_matrix, right_extension), axis=0),
        expanded_charge, column_charge, 2 * middle)
    left_rank = left_basis.shape[1]
    right_rank = right_basis.shape[0]
    left_matrix, left_position = left_step(left_environment,
        left_basis.reshape(left, dimension, left_rank), onsite[site], positions[site],
        couplings[site - 1] if site else 0.0)
    right_matrix, right_position = right_step(right_environment,
        right_basis.reshape(right_rank, dimension, right), onsite[site + 1], positions[site + 1],
        couplings[site + 1] if site + 2 < len(tensors) else 0.0)
    matvec, diagonal, pack, unpack = effective_action(left_matrix, right_matrix,
        left_position, right_position, couplings[site], left_charge, right_charge)
    initial = (left_basis.T @ first_matrix) @ (second_matrix @ right_basis.T)
    vector, energy = lowest(matvec, diagonal, pack(initial), tolerance, max_steps, clock)
    optimized = unpack(vector)
    left_vectors, values, right_vectors, new_charge = factor(optimized,
        left_charge, right_charge, cap)
    values /= np.linalg.norm(values)
    if direction == 1:
        tensors[site] = (left_basis @ left_vectors).reshape(left, dimension, len(values))
        tensors[site + 1] = ((values[:, None] * right_vectors) @ right_basis).reshape(len(values), dimension, right)
    else:
        tensors[site] = (left_basis @ (left_vectors * values)).reshape(left, dimension, len(values))
        tensors[site + 1] = (right_vectors @ right_basis).reshape(len(values), dimension, right)
    if charges is not None:
        charges[site + 1] = new_charge
    return energy


def site_update(tensors, charges, site, left_environment, right_environment,
                onsite, positions, couplings, direction, cap, noise, tolerance,
                max_steps, clock):
    tensor = tensors[site]
    left, dimension, right = tensor.shape
    left_energy, left_position = left_environment
    right_energy, right_position = right_environment
    left_coupling = couplings[site - 1] if site else 0.0
    right_coupling = couplings[site] if site + 1 < len(tensors) else 0.0
    onsite_matrix = onsite[site]
    position = positions[site]
    left_values, left_vectors = diagonalize(left_energy, None if charges is None else charges[site])
    right_values, right_vectors = diagonalize(right_energy, None if charges is None else charges[site + 1])
    tensor = (left_vectors.T @ tensor.reshape(left, dimension * right)).reshape(left * dimension, right)
    tensor = (tensor @ right_vectors).reshape(left, dimension, right)
    left_position = left_vectors.T @ left_position @ left_vectors
    right_position = right_vectors.T @ right_position @ right_vectors
    local_diagonal = left_values[:, None, None] + np.diag(onsite_matrix)[None, :, None] + right_values[None, None, :]
    left_energy = np.diag(left_values)
    right_energy = np.diag(right_values)
    diagonal = (np.diag(left_energy)[:, None, None]
                + np.diag(onsite_matrix)[None, :, None]
                + np.diag(right_energy)[None, None, :]
                - left_coupling * np.diag(left_position)[:, None, None] * np.diag(position)[None, :, None]
                - right_coupling * np.diag(position)[None, :, None] * np.diag(right_position)[None, None, :]).ravel()

    def matvec(vector):
        current = vector.reshape(left, dimension, right)
        position_tensor = physical_action(position, current)
        image = local_diagonal * current
        image -= left_coupling * (left_position @ position_tensor.reshape(left, dimension * right)).reshape(current.shape)
        image -= right_coupling * (position_tensor.reshape(left * dimension, right) @ right_position).reshape(current.shape)
        return image.ravel()

    if charges is not None:
        allowed = np.flatnonzero((charges[site][:, None, None] ^ (np.arange(dimension)[None, :, None] % 2)
                                 ^ charges[site + 1][None, None, :]).ravel() == 0)
        def packed_action(vector):
            full = np.zeros(left * dimension * right)
            full[allowed] = vector
            return matvec(full)[allowed]
        packed, energy = lowest(packed_action, diagonal[allowed], tensor.ravel()[allowed], tolerance, max_steps, clock)
        vector = np.zeros(left * dimension * right)
        vector[allowed] = packed
    else:
        vector, energy = lowest(matvec, diagonal, tensor.ravel(), tolerance, max_steps, clock)
    tensor = vector.reshape(left, dimension, right)
    tensor = (left_vectors @ tensor.reshape(left, dimension * right)).reshape(left * dimension, right)
    tensor = (tensor @ right_vectors.T).reshape(left, dimension, right)
    physical = np.arange(dimension) % 2
    if direction == 1 and site + 1 < len(tensors):
        matrix = tensor.reshape(left * dimension, right)
        row_charge = None if charges is None else (charges[site][:, None] ^ physical[None, :]).ravel()
        column_charge = None if charges is None else charges[site + 1]
        expanded = matrix
        if noise:
            extension = physical_action(position, tensor).reshape(left * dimension, right)
            expanded = np.concatenate((matrix, noise * extension), axis=1)
            if charges is not None:
                column_charge = np.concatenate((column_charge, column_charge ^ 1))
        if noise:
            orthogonal, _, _, new_charge = factor(expanded, row_charge, column_charge, cap)
            transport = orthogonal.T @ matrix
        else:
            orthogonal, transport, new_charge = qr_factor(matrix, row_charge, column_charge)
        following = np.tensordot(transport, tensors[site + 1], axes=(1, 0))
        following /= np.linalg.norm(following)
        tensors[site] = orthogonal.reshape(left, dimension, orthogonal.shape[1])
        tensors[site + 1] = following
        if charges is not None:
            charges[site + 1] = new_charge
    elif direction == -1 and site:
        matrix = tensor.reshape(left, dimension * right)
        row_charge = None if charges is None else charges[site]
        column_charge = None if charges is None else (physical[:, None] ^ charges[site + 1][None, :]).ravel()
        expanded = matrix
        if noise:
            extension = physical_action(position, tensor).reshape(left, dimension * right)
            expanded = np.concatenate((matrix, noise * extension), axis=0)
            if charges is not None:
                row_charge = np.concatenate((row_charge, row_charge ^ 1))
        if noise:
            _, _, orthogonal, new_charge = factor(expanded, row_charge, column_charge, cap)
            transport = matrix @ orthogonal.T
        else:
            orthogonal, transport, new_charge = qr_factor(matrix.T, column_charge, row_charge)
            orthogonal, transport = orthogonal.T, transport.T
        previous = np.tensordot(tensors[site - 1], transport, axes=(2, 0))
        previous /= np.linalg.norm(previous)
        tensors[site] = orthogonal.reshape(orthogonal.shape[0], dimension, right)
        tensors[site - 1] = previous
        if charges is not None:
            charges[site] = new_charge
    else:
        tensors[site] = tensor
    return energy


def optimize(request, start_cpu=None, start_wall=None):
    start_cpu = time.process_time() if start_cpu is None else start_cpu
    start_wall = time.monotonic() if start_wall is None else start_wall
    request = dict(request)
    clock = Clock(request, start_cpu, start_wall)
    onsite, positions = hamiltonian_terms(request)
    if request['sector'] == 'any' and max(abs(value) for value in request['field']) == 0:
        even_ground = True
        for site, position in enumerate(positions):
            square = position @ position
            square[-1, -1] += request['local_dim'] / (2 * request['omega'][site])
            spring = request['coupling'][site - 1] if site else 0.0
            if site + 1 < request['n_sites']:
                spring += request['coupling'][site]
            bare = onsite[site] - 0.5 * spring * square
            even_energy = dsyev(bare[::2, ::2], compute_v=0)[0][0]
            odd_energy = dsyev(bare[1::2, 1::2], compute_v=0)[0][0]
            if odd_energy < even_energy:
                even_ground = False
                break
        if even_ground:
            request['sector'] = 'even'
    transforms = local_basis(onsite, positions, request['sector'] != 'any')
    couplings = request['coupling']
    tensors, charges = initial_state(onsite, positions, couplings, request)
    right_canonical(tensors, charges)
    if charges is None:
        shift_basis(tensors, onsite, positions, transforms, couplings)
    length = len(tensors)
    empty = (np.zeros((1, 1)), np.zeros((1, 1)))
    right_environments = [None] * (length + 1)
    right_environments[length] = empty
    for site in range(length - 1, -1, -1):
        right_environments[site] = right_step(right_environments[site + 1], tensors[site],
            onsite[site], positions[site], couplings[site] if site + 1 < length else 0.0)
    previous_energy = float('inf')
    extrapolation = 1.0
    extrapolation_max = 12.0
    best_tensors = None
    best_energy = float('inf')
    stable = 0
    allocation_checks = 0
    allocation_start_energy = float('inf')
    pending_pair = False

    def finish(site, left_environment, right_environment):
        energy = center_energy(tensors[site], left_environment, right_environment,
            onsite[site], positions[site], couplings[site - 1] if site else 0.0,
            couplings[site] if site + 1 < length else 0.0)
        return restore_basis(best_tensors if best_tensors is not None and best_energy < energy else tensors, transforms)

    for sweep in range(1000):
        previous_tensors = [tensor.copy() for tensor in tensors] if sweep >= 8 else None
        cap = min(request['bond_cap'], 4 if sweep == 0 else (8 if sweep == 1 else request['bond_cap']))
        noise = [0.1, 0.03, 0.01, 0.003, 0.001, 0.0001, 0.00001][min(sweep, 6)] if sweep < 8 else 0.0
        tolerance = 1e-5 if sweep < 3 else (1e-7 if sweep < 7 else 1e-10)
        max_steps = 4
        if sweep == 3 or pending_pair:
            checking_allocation = pending_pair
            counts = None if charges is None else [(len(charge), int(np.sum(charge))) for charge in charges]
            pending_pair = False
            left_environments = [empty]
            for site in range(length - 1):
                if clock.remaining() < 0.06:
                    return finish(site, left_environments[site], right_environments[site + 1])
                energy = reduced_pair(tensors, charges, site, left_environments[site],
                    right_environments[site + 2], onsite, positions, couplings, 1,
                    cap, tolerance, 24, clock)
                left_environments.append(left_step(left_environments[site], tensors[site],
                    onsite[site], positions[site], couplings[site - 1] if site else 0.0))
            for site in range(length - 2, -1, -1):
                if clock.remaining() < 0.06:
                    return finish(site + 1, left_environments[site + 1], right_environments[site + 2])
                energy = reduced_pair(tensors, charges, site, left_environments[site],
                    right_environments[site + 2], onsite, positions, couplings, -1,
                    cap, tolerance, 24, clock)
                right_environments[site + 1] = right_step(right_environments[site + 2], tensors[site + 1],
                    onsite[site + 1], positions[site + 1], couplings[site + 1] if site + 2 < length else 0.0)
            if os.environ.get('MPS_DEBUG'):
                print('pair', sweep, cap, energy, clock.remaining(), flush=True)
            energy = center_energy(tensors[0], empty, right_environments[1], onsite[0], positions[0], 0.0, couplings[0])
            if energy < best_energy:
                best_energy = energy
                best_tensors = [tensor.copy() for tensor in tensors]
            stable = 0
            if checking_allocation and counts == [(len(charge), int(np.sum(charge))) for charge in charges]:
                return restore_basis(best_tensors, transforms)
            previous_energy = energy
            continue
        left_environments = [empty]
        for site in range(length):
            if clock.remaining() < 0.06:
                return finish(site, left_environments[site], right_environments[site + 1])
            energy = site_update(tensors, charges, site, left_environments[site],
                right_environments[site + 1], onsite, positions, couplings, 1,
                cap, noise, tolerance, max_steps, clock)
            left_environments.append(left_step(left_environments[site], tensors[site],
                onsite[site], positions[site], couplings[site - 1] if site else 0.0))
        for site in range(length - 1, -1, -1):
            if clock.remaining() < 0.06:
                return finish(site, left_environments[site], right_environments[site + 1])
            energy = site_update(tensors, charges, site, left_environments[site],
                right_environments[site + 1], onsite, positions, couplings, -1,
                cap, noise, tolerance, max_steps, clock)
            right_environments[site] = right_step(right_environments[site + 1], tensors[site],
                onsite[site], positions[site], couplings[site] if site + 1 < length else 0.0)
        if previous_tensors is not None and sweep >= 8 and clock.remaining() > 0.6:
            trial, trial_charges = extrapolate(tensors, previous_tensors, charges, extrapolation)
            if trial is not None:
                trial_environments = [None] * (length + 1)
                trial_environments[length] = empty
                for site in range(length - 1, -1, -1):
                    trial_environments[site] = right_step(trial_environments[site + 1], trial[site],
                        onsite[site], positions[site], couplings[site] if site + 1 < length else 0.0)
                trial_energy = trial_environments[0][0][0, 0]
                next_extrapolation = None
                if np.isfinite(previous_energy):
                    previous_change = previous_energy - energy
                    trial_change = trial_energy - energy
                    curvature = trial_change + extrapolation * previous_change
                    if curvature > 1e-13:
                        optimum = (extrapolation * extrapolation * previous_change - trial_change) / (2 * curvature)
                        next_extrapolation = np.clip(optimum, 0.1, extrapolation_max)
                if trial_energy < energy:
                    tensors, charges, right_environments, energy = trial, trial_charges, trial_environments, trial_energy
                    extrapolation = min(extrapolation * 1.15, extrapolation_max)
                else:
                    extrapolation = max(extrapolation * 0.5, 0.1)
                if next_extrapolation is not None:
                    extrapolation = float(next_extrapolation)
        if os.environ.get('MPS_DEBUG'):
            print(sweep, cap, noise, energy, clock.remaining(), extrapolation, flush=True)
        if energy < best_energy:
            best_energy = energy
            best_tensors = [tensor.copy() for tensor in tensors]
        stable = stable + 1 if abs(previous_energy - energy) < 2e-12 else 0
        if sweep > 10 and stable >= 3:
            allocation_reserve = 0.75 if request['budget_seconds'] <= 8 else 0.3 * request['budget_seconds']
            if (charges is not None and allocation_checks < 4
                    and clock.remaining() > allocation_reserve
                    and (allocation_checks == 0 or best_energy < allocation_start_energy - 1e-10)):
                pending_pair = True
                allocation_checks += 1
                allocation_start_energy = best_energy
                stable = 0
                previous_energy = energy
                continue
            break
        previous_energy = energy
    return restore_basis(best_tensors if best_tensors is not None else tensors, transforms)
