import numpy as np
from optimizer import factor, qr_factor
from fast import diagonalize, physical_action
from native import lowest_site


def site_update(tensors, charges, site, left_environment, right_environment,
                onsite, positions, couplings, direction, cap, noise, tolerance,
                max_steps, clock):
    tensor = tensors[site]
    left, dimension, right = tensor.shape
    left_energy, left_position = left_environment
    right_energy, right_position = right_environment
    left_coupling = couplings[site-1] if site else 0.0
    right_coupling = couplings[site] if site+1 < len(tensors) else 0.0
    position = positions[site]
    left_values, left_vectors = diagonalize(left_energy, charges[site])
    right_values, right_vectors = diagonalize(right_energy, charges[site+1])
    tensor = (left_vectors.T @ tensor.reshape(left, dimension*right)).reshape(left*dimension, right)
    tensor = (tensor @ right_vectors).reshape(left, dimension, right)
    left_position = left_vectors.T @ left_position @ left_vectors
    right_position = right_vectors.T @ right_position @ right_vectors
    diagonal = (left_values[:, None, None] + np.diag(onsite[site])[None, :, None]
                + right_values[None, None, :]).ravel()
    vector, energy = lowest_site(diagonal, tensor, left_position, position,
        right_position, left_coupling, right_coupling, tolerance, max_steps)
    tensor = (left_vectors @ vector.reshape(left, dimension*right)).reshape(left*dimension, right)
    tensor = (tensor @ right_vectors.T).reshape(left, dimension, right)
    physical = np.arange(dimension) % 2
    if direction == 1 and site+1 < len(tensors):
        matrix = tensor.reshape(left*dimension, right)
        row_charge = (charges[site][:, None] ^ physical[None, :]).ravel()
        if noise:
            extension = physical_action(position, tensor).reshape(left*dimension, right)
            expanded = np.concatenate((matrix, noise*extension), axis=1)
            column_charge = np.r_[charges[site+1], charges[site+1] ^ 1]
            orthogonal, _, _, new_charge = factor(expanded, row_charge, column_charge, cap)
            transport = orthogonal.T @ matrix
        else:
            orthogonal, transport, new_charge = qr_factor(matrix, row_charge, charges[site+1])
        following = np.tensordot(transport, tensors[site+1], axes=(1, 0))
        following /= np.linalg.norm(following)
        tensors[site] = orthogonal.reshape(left, dimension, orthogonal.shape[1])
        tensors[site+1] = following
        charges[site+1] = new_charge
    elif direction == -1 and site > 0:
        matrix = tensor.reshape(left, dimension*right)
        column_charge = (physical[:, None] ^ charges[site+1][None, :]).ravel()
        if noise:
            extension = physical_action(position, tensor).reshape(left, dimension*right)
            expanded = np.concatenate((matrix, noise*extension), axis=0)
            row_charge = np.r_[charges[site], charges[site] ^ 1]
            _, _, orthogonal, new_charge = factor(expanded, row_charge, column_charge, cap)
            transport = matrix @ orthogonal.T
        else:
            orthogonal, transport, new_charge = qr_factor(matrix.T, column_charge, charges[site])
            orthogonal, transport = orthogonal.T, transport.T
        previous = np.tensordot(tensors[site-1], transport, axes=(2, 0))
        previous /= np.linalg.norm(previous)
        tensors[site] = orthogonal.reshape(orthogonal.shape[0], dimension, right)
        tensors[site-1] = previous
        charges[site] = new_charge
    else:
        tensors[site] = tensor
    return energy
