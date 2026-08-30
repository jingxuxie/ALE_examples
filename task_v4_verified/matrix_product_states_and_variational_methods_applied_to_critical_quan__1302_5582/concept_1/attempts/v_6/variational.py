import numpy as np

from fast import (lowest, diagonalize, physical_action, left_step, right_step,
                  site_update, center_energy)
from optimizer import factor, qr_factor
from window import optimize_window


def matrix_ground(matrix, left_matrix, right_matrix, left_position, right_position,
                  coupling, row_charge, column_charge, clock):
    left_values, left_vectors = diagonalize(left_matrix, row_charge)
    right_values, right_vectors = diagonalize(right_matrix, column_charge)
    position_left = left_vectors.T @ left_position @ left_vectors
    position_right = right_vectors.T @ right_position @ right_vectors
    rows = [np.flatnonzero(row_charge == charge) for charge in (0, 1)]
    columns = [np.flatnonzero(column_charge == charge) for charge in (0, 1)]
    selectors = [np.ix_(rows[charge], columns[charge]) for charge in (0, 1)]
    shapes = [(len(rows[charge]), len(columns[charge])) for charge in (0, 1)]
    split = shapes[0][0] * shapes[0][1]
    diagonal_blocks = [left_values[rows[charge], None] + right_values[None, columns[charge]]
                       for charge in (0, 1)]
    left_cross = [position_left[np.ix_(rows[charge], rows[1 - charge])] for charge in (0, 1)]
    right_cross = [position_right[np.ix_(columns[1 - charge], columns[charge])]
                   for charge in (0, 1)]

    def action(vector):
        blocks = [vector[:split].reshape(shapes[0]), vector[split:].reshape(shapes[1])]
        return np.concatenate([(diagonal_blocks[charge] * blocks[charge]
            - coupling * (left_cross[charge] @ blocks[1 - charge] @ right_cross[charge])).ravel()
            for charge in (0, 1)])

    transformed = left_vectors.T @ matrix @ right_vectors
    start = np.concatenate([transformed[selector].ravel() for selector in selectors])
    diagonal = np.concatenate([block.ravel() for block in diagonal_blocks])
    vector, energy = lowest(action, diagonal, start, 1e-9, 30, clock)
    transformed = np.zeros_like(transformed)
    transformed[selectors[0]] = vector[:split].reshape(shapes[0])
    transformed[selectors[1]] = vector[split:].reshape(shapes[1])
    return left_vectors @ transformed @ right_vectors.T, energy


def allocate_pair(tensors, charges, site, left_environment, right_environment,
                  onsite, positions, couplings, cap, clock, context=None):
    first, second = tensors[site:site + 2]
    left, dimension, middle = first.shape
    right = second.shape[2]
    first_matrix = first.reshape(left * dimension, middle)
    second_matrix = second.reshape(middle, dimension * right)
    left_extension = physical_action(positions[site], first).reshape(left * dimension, middle)
    right_extension = physical_action(positions[site + 1], second).reshape(middle, dimension * right)
    physical = np.arange(dimension) % 2
    row_charge = (charges[site][:, None] ^ physical[None, :]).ravel()
    column_charge = (physical[:, None] ^ charges[site + 2][None, :]).ravel()
    expanded_charge = np.concatenate((charges[site + 1], charges[site + 1] ^ 1))
    left_basis, _, _, left_charge = factor(np.concatenate((first_matrix, left_extension), axis=1),
        row_charge, expanded_charge, 2 * middle)
    _, _, right_basis, right_charge = factor(np.concatenate((second_matrix, right_extension), axis=0),
        expanded_charge, column_charge, 2 * middle)
    left_matrix, left_position = left_step(left_environment,
        left_basis.reshape(left, dimension, left_basis.shape[1]), onsite[site], positions[site],
        couplings[site - 1] if site else 0.0)
    right_matrix, right_position = right_step(right_environment,
        right_basis.reshape(right_basis.shape[0], dimension, right), onsite[site + 1], positions[site + 1],
        couplings[site + 1] if site + 2 < len(tensors) else 0.0)
    coupling = couplings[site]
    initial = (left_basis.T @ first_matrix) @ (second_matrix @ right_basis.T)
    image = left_matrix @ initial + initial @ right_matrix - coupling * left_position @ initial @ right_position
    best_energy = np.sum(initial * image) / np.sum(initial * initial)
    optimized, expanded_energy = matrix_ground(initial, left_matrix, right_matrix,
        left_position, right_position, coupling, left_charge, right_charge, clock)
    first_vectors, values, second_vectors, singular_charge = factor(optimized, left_charge, right_charge, 2 * cap)
    groups = [np.flatnonzero(singular_charge == charge) for charge in (0, 1)]
    odd_count = int(np.sum(charges[site + 1]))
    best = None
    best_window = None
    candidate_counts = (odd_count, odd_count - 1, odd_count + 1) if context is not None else (odd_count - 1, odd_count + 1)
    for candidate_odd in candidate_counts:
        if (not 0 <= candidate_odd <= cap or candidate_odd > len(groups[1])
                or cap - candidate_odd > len(groups[0]) or clock.remaining() < 0.08):
            continue
        selected = np.concatenate((groups[0][:cap - candidate_odd], groups[1][:candidate_odd]))
        first_candidate = first_vectors[:, selected]
        second_candidate = values[selected, None] * second_vectors[selected]
        second_candidate /= np.linalg.norm(second_candidate)
        candidate_charge = singular_charge[selected]
        trial_tensors = tensors.copy()
        trial_charges = charges.copy()
        trial_tensors[site] = (left_basis @ first_candidate).reshape(left, dimension, len(candidate_charge))
        trial_tensors[site + 1] = (second_candidate @ right_basis).reshape(len(candidate_charge), dimension, right)
        trial_charges[site + 1] = candidate_charge
        previous_energy = float('inf')
        for iteration in range(4):
            if clock.remaining() < 0.06:
                break
            middle_left = left_step(left_environment, trial_tensors[site], onsite[site], positions[site],
                couplings[site - 1] if site else 0.0)
            site_update(trial_tensors, trial_charges, site + 1, middle_left, right_environment,
                onsite, positions, couplings, -1, cap, 0.0, 1e-9, 8, clock)
            middle_right = right_step(right_environment, trial_tensors[site + 1], onsite[site + 1], positions[site + 1],
                couplings[site + 1] if site + 2 < len(tensors) else 0.0)
            energy = site_update(trial_tensors, trial_charges, site, left_environment, middle_right,
                onsite, positions, couplings, 1, cap, 0.0, 1e-9, 8, clock)
            if abs(previous_energy - energy) < 1e-11:
                break
            if iteration >= 1 and energy - best_energy > 3 * (previous_energy - energy):
                break
            previous_energy = energy
        middle_left = left_step(left_environment, trial_tensors[site], onsite[site], positions[site],
            couplings[site - 1] if site else 0.0)
        candidate_energy = center_energy(trial_tensors[site + 1], middle_left, right_environment,
            onsite[site + 1], positions[site + 1], couplings[site],
            couplings[site + 1] if site + 2 < len(tensors) else 0.0)
        window_used = False
        if (context is not None and clock.remaining() > 0.20 and candidate_odd != odd_count
                and candidate_energy - best_energy < max(2e-8, 0.5 * (best_energy - expanded_energy))):
            candidate_energy = optimize_window(trial_tensors, trial_charges, site, context,
                onsite, positions, couplings, cap, clock)
            window_used = True
        if candidate_energy < best_energy - 1e-12:
            best_energy = candidate_energy
            best = (trial_tensors[site].reshape(left * dimension, -1),
                    trial_tensors[site + 1].reshape(-1, dimension * right), trial_charges[site + 1])
            best_window = (trial_tensors, trial_charges) if window_used else None
    if best is not None:
        if best_window is not None:
            trial_tensors, trial_charges = best_window
            for current in range(max(0, site - 1), min(len(tensors), site + 3)):
                tensors[current] = trial_tensors[current]
                charges[current] = trial_charges[current]
            if site:
                context[0][site] = left_step(context[0][site - 1], tensors[site - 1],
                    onsite[site - 1], positions[site - 1], couplings[site - 2] if site > 1 else 0.0)
            if site + 2 < len(tensors):
                context[1][site + 2] = right_step(context[1][site + 3], tensors[site + 2],
                    onsite[site + 2], positions[site + 2], couplings[site + 2] if site + 3 < len(tensors) else 0.0)
        first_matrix, second_matrix, charges[site + 1] = best
    orthogonal, transport, new_charge = qr_factor(first_matrix, row_charge, charges[site + 1])
    first_matrix = orthogonal
    second_matrix = transport @ second_matrix
    second_matrix /= np.linalg.norm(second_matrix)
    charges[site + 1] = new_charge
    tensors[site] = first_matrix.reshape(left, dimension, len(new_charge))
    tensors[site + 1] = second_matrix.reshape(len(new_charge), dimension, right)
    return best_energy
