import numpy as np
from scipy.linalg import svd
from optimizer import qr_factor
from fast import diagonalize, physical_action, left_step, right_step
from native import lowest_site


def minimize(matrix, left_energy, right_energy, left_position, right_position,
             coupling, row_charge, column_charge, clock, steps=6):
    left_values, left_basis = diagonalize(left_energy, row_charge)
    right_values, right_basis = diagonalize(right_energy, column_charge)
    left_position = left_basis.T @ left_position @ left_basis
    right_position = right_basis.T @ right_position @ right_basis
    initial = left_basis.T @ matrix @ right_basis
    diagonal = (left_values[:, None]+right_values[None, :]).ravel()
    vector, energy = lowest_site(diagonal, initial[:, :, None], left_position,
        right_position, np.zeros((1, 1)), coupling, 0.0, 1e-8, steps)
    return left_basis @ vector.reshape(initial.shape) @ right_basis.T, energy


def refine(left, right, middle_charge, row_charge, column_charge, left_energy,
           right_energy, left_position, right_position, coupling, clock, iterations):
    energy = float('inf')
    for iteration in range(iterations):
        previous_energy = energy
        left, energy = minimize(left, left_energy, right @ right_energy @ right.T,
            left_position, right @ right_position @ right.T, coupling,
            row_charge, middle_charge, clock)
        orthogonal, transport, middle_charge = qr_factor(left, row_charge, middle_charge)
        right = transport @ right
        left = orthogonal
        right, energy = minimize(right, left.T @ left_energy @ left, right_energy,
            left.T @ left_position @ left, right_position, coupling,
            middle_charge, column_charge, clock)
        orthogonal, transport, middle_charge = qr_factor(right.T, column_charge, middle_charge)
        left = left @ transport.T
        right = orthogonal.T
        if clock.remaining() < 0.1 or (iteration >= 2 and previous_energy-energy < 5e-12):
            break
    return left, right, middle_charge, energy


def search(tensors, charges, site, left_environment, right_environment,
           onsite, positions, couplings, direction, cap, tolerance, max_steps, clock):
    first, second = tensors[site:site+2]
    left, dimension, middle = first.shape
    right = second.shape[2]
    first_matrix = first.reshape(left*dimension, middle)
    second_matrix = second.reshape(middle, dimension*right)
    physical = np.arange(dimension) % 2
    row_charge = (charges[site][:, None] ^ physical[None, :]).ravel()
    column_charge = (physical[:, None] ^ charges[site+2][None, :]).ravel()
    expanded_charge = np.r_[charges[site+1], charges[site+1] ^ 1]
    left_extension = physical_action(positions[site], first).reshape(left*dimension, middle)
    right_extension = physical_action(positions[site+1], second).reshape(middle, dimension*right)
    left_basis, _, left_charge = qr_factor(np.concatenate((first_matrix, left_extension), axis=1), row_charge, expanded_charge)
    right_basis, _, right_charge = qr_factor(np.concatenate((second_matrix, right_extension), axis=0).T, column_charge, expanded_charge)
    left_rank, right_rank = left_basis.shape[1], right_basis.shape[1]
    left_energy, left_position = left_step(left_environment,
        left_basis.reshape(left, dimension, left_rank), onsite[site], positions[site],
        couplings[site-1] if site else 0.0)
    right_energy, right_position = right_step(right_environment,
        right_basis.T.reshape(right_rank, dimension, right), onsite[site+1], positions[site+1],
        couplings[site+1] if site+2 < len(tensors) else 0.0)
    current_left = left_basis.T @ first_matrix
    current_right = second_matrix @ right_basis
    initial = current_left @ current_right
    image = left_energy @ initial + initial @ right_energy - couplings[site]*left_position @ initial @ right_position
    best_energy = np.sum(initial*image) / np.sum(initial**2)
    best_left, best_right, best_charge = current_left, current_right, charges[site+1]
    optimized, energy = minimize(initial, left_energy, right_energy, left_position,
        right_position, couplings[site], left_charge, right_charge, clock, steps=12)
    blocks = []
    for charge in (0, 1):
        rows = np.flatnonzero(left_charge == charge)
        columns = np.flatnonzero(right_charge == charge)
        vectors, values, covectors = svd(optimized[np.ix_(rows, columns)],
                                        full_matrices=False, check_finite=False)
        blocks.append((rows, columns, vectors, values, covectors))
    even_count = int(np.sum(charges[site+1] == 0))
    for delta in (-1, 1):
        counts = [even_count+delta, middle-even_count-delta]
        if any(count < 0 or count > len(block[3]) for count, block in zip(counts, blocks)):
            continue
        trial_left = np.zeros((left_rank, middle))
        trial_right = np.zeros((middle, right_rank))
        trial_charge = np.repeat([0, 1], counts)
        cursor = 0
        for count, block in zip(counts, blocks):
            indices = np.arange(cursor, cursor+count)
            trial_left[np.ix_(block[0], indices)] = block[2][:, :count]*block[3][:count]
            trial_right[np.ix_(indices, block[1])] = block[4][:count]
            cursor += count
        trial_matrix = trial_left @ trial_right
        trial_image = left_energy @ trial_matrix + trial_matrix @ right_energy - couplings[site]*left_position @ trial_matrix @ right_position
        trial_energy = np.sum(trial_matrix*trial_image) / np.sum(trial_matrix**2)
        if trial_energy-energy > 3.0*max(best_energy-energy, 1e-12):
            continue
        trial_left, trial_right, trial_charge, value = refine(trial_left, trial_right,
            trial_charge, left_charge, right_charge, left_energy, right_energy,
            left_position, right_position, couplings[site], clock, iterations=6)
        if value < best_energy-1e-12:
            if __import__('os').environ.get('MPS_DEBUG'):
                print('swap', site, delta, best_energy-value, flush=True)
            best_energy = value
            best_left, best_right, best_charge = trial_left, trial_right, trial_charge
        if clock.remaining() < 0.15:
            break
    if direction == 1:
        orthogonal, transport, best_charge = qr_factor(best_left, left_charge, best_charge)
        best_left, best_right = orthogonal, transport @ best_right
    else:
        orthogonal, transport, best_charge = qr_factor(best_right.T, right_charge, best_charge)
        best_left, best_right = best_left @ transport.T, orthogonal.T
    tensors[site] = (left_basis @ best_left).reshape(left, dimension, middle)
    tensors[site+1] = (best_right @ right_basis.T).reshape(middle, dimension, right)
    charges[site+1] = best_charge
    return best_energy
