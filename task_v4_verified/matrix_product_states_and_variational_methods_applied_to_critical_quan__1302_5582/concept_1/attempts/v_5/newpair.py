import numpy as np
from optimizer import factor, qr_factor
from fast import diagonalize, physical_action, left_step, right_step
from native import lowest_site

step_limit = 24


def update(tensors, charges, site, left_environment, right_environment,
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
    left_values, left_vectors = diagonalize(left_energy, left_charge)
    right_values, right_vectors = diagonalize(right_energy, right_charge)
    left_basis = left_basis @ left_vectors
    right_basis = right_basis @ right_vectors
    left_position = left_vectors.T @ left_position @ left_vectors
    right_position = right_vectors.T @ right_position @ right_vectors
    initial = (left_basis.T @ first_matrix) @ (second_matrix @ right_basis)
    diagonal = (left_values[:, None]+right_values[None, :]).ravel()
    vector, energy = lowest_site(diagonal, initial[:, :, None], left_position,
        right_position, np.zeros((1, 1)), couplings[site], 0.0, tolerance, min(max_steps, step_limit))
    left_vectors, values, right_vectors, new_charge = factor(vector.reshape(initial.shape), left_charge, right_charge, cap)
    values /= np.linalg.norm(values)
    if direction == 1:
        tensors[site] = (left_basis @ left_vectors).reshape(left, dimension, len(values))
        tensors[site+1] = ((values[:, None]*right_vectors) @ right_basis.T).reshape(len(values), dimension, right)
    else:
        tensors[site] = (left_basis @ (left_vectors*values)).reshape(left, dimension, len(values))
        tensors[site+1] = (right_vectors @ right_basis.T).reshape(len(values), dimension, right)
    charges[site+1] = new_charge
    return energy
