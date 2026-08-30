import numpy as np
from scipy.linalg import eigh


def cross_measure(bra, ket, onsite, positions, couplings):
    overlap = np.ones((1, 1))
    energy = np.zeros((1, 1))
    edge = np.zeros((1, 1))
    for site, (first, second) in enumerate(zip(bra, ket)):
        left_first, dimension, right_first = first.shape
        left_second, _, right_second = second.shape
        first_matrix = first.reshape(left_first * dimension, right_first)
        second_flat = second.reshape(left_second, -1)
        positioned = (positions[site] @ second.transpose(1, 0, 2).reshape(dimension, -1)).reshape(dimension, left_second, right_second).transpose(1, 0, 2).reshape(left_second, -1)
        acted = energy @ second_flat
        acted += overlap @ (np.diag(onsite[site])[None, :, None] * second).reshape(left_second, -1)
        if site:
            acted -= couplings[site-1] * (edge @ positioned)
        energy = first_matrix.T @ acted.reshape(left_first * dimension, right_second)
        edge = first_matrix.T @ (overlap @ positioned).reshape(left_first * dimension, right_second)
        overlap = first_matrix.T @ (overlap @ second_flat).reshape(left_first * dimension, right_second)
    return float(overlap[0, 0]), float(energy[0, 0])


def combine(first, second, weights, first_charges, second_charges, cap):
    from optimizer import factor, right_canonical
    result = []
    charges = None
    if first_charges is not None:
        charges = [first_charges[0].copy()]
        charges += [np.concatenate((first_charge, second_charge)) for first_charge, second_charge in zip(first_charges[1:-1], second_charges[1:-1])]
        charges.append(first_charges[-1].copy())
    for site, (first_tensor, second_tensor) in enumerate(zip(first, second)):
        if site == 0:
            tensor = np.concatenate((weights[0]*first_tensor, weights[1]*second_tensor), axis=2)
        elif site == len(first)-1:
            tensor = np.concatenate((first_tensor, second_tensor), axis=0)
        else:
            first_left, dimension, first_right = first_tensor.shape
            second_left, _, second_right = second_tensor.shape
            tensor = np.zeros((first_left+second_left, dimension, first_right+second_right))
            tensor[:first_left, :, :first_right] = first_tensor
            tensor[first_left:, :, first_right:] = second_tensor
        result.append(tensor)
    right_canonical(result, charges)
    for site in range(len(result)-1):
        left, dimension, right = result[site].shape
        row_charge = None if charges is None else (charges[site][:, None] ^ (np.arange(dimension)[None, :] % 2)).ravel()
        column_charge = None if charges is None else charges[site+1]
        orthogonal, values, following, new_charge = factor(result[site].reshape(left*dimension, right), row_charge, column_charge, cap)
        result[site] = orthogonal.reshape(left, dimension, len(values))
        result[site+1] = np.tensordot(values[:, None]*following, result[site+1], axes=(1, 0))
        if charges is not None:
            charges[site+1] = new_charge
    right_canonical(result, charges)
    return result, charges


def extrapolate(current, previous, charges, previous_charges, energy, previous_energy,
                onsite, positions, couplings, cap):
    overlap, cross = cross_measure(current, previous, onsite, positions, couplings)
    norm_squared = 1-overlap*overlap
    if norm_squared < 1e-11 or abs(overlap) < 0.5:
        return None
    norm = np.sqrt(norm_squared)
    off_diagonal = (cross-overlap*energy)/norm
    difference_energy = (previous_energy-2*overlap*cross+overlap*overlap*energy)/norm_squared
    values, vectors = eigh(np.array([[energy, off_diagonal], [off_diagonal, difference_energy]]), check_finite=False)
    if energy-values[0] < 2e-12:
        return None
    weights = np.array([vectors[0, 0]-overlap*vectors[1, 0]/norm, vectors[1, 0]/norm])
    if abs(weights[1]) > 8:
        weights = np.array([1+8*abs(overlap), -8*np.sign(overlap)])
    result, new_charges = combine(current, previous, weights, charges, previous_charges, cap)
    norm, new_energy = cross_measure(result, result, onsite, positions, couplings)
    new_energy /= norm
    if new_energy >= energy:
        return None
    return result, new_charges, new_energy


def reflection(current, charges, energy, onsite, positions, couplings, cap):
    reflected = [tensor.transpose(2, 1, 0).copy() for tensor in reversed(current)]
    reflected_charges = None if charges is None else [charge ^ int(charges[-1][0]) for charge in reversed(charges)]
    result, new_charges = combine(current, reflected, [1., 1.], charges, reflected_charges, cap)
    norm, new_energy = cross_measure(result, result, onsite, positions, couplings)
    new_energy /= norm
    if new_energy >= energy:
        return None
    return result, new_charges, new_energy
