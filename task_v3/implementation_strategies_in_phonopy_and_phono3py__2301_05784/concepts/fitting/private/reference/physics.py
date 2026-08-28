"""Tensor contractions and geometric invariance diagnostics."""

import numpy as np


def load_npz(path):
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


def fold_harmonic(fc2, input_data):
    atom_count = len(input_data["numbers3"])
    result = np.zeros((len(fc2), atom_count, 3, 3), dtype=np.float64)
    for representative in range(len(fc2)):
        np.add.at(result[representative], input_data["fold2to3"][representative], fc2[representative])
    return result


def harmonic_forces(fc2, displacements, row_map, compact_map):
    if len(displacements) == 0:
        return np.empty_like(displacements)
    expanded = fc2[row_map[:, None], compact_map]
    matrix = expanded.transpose(0, 2, 1, 3).reshape(3 * len(row_map), -1)
    return -(displacements.reshape(len(displacements), -1) @ matrix.T).reshape(displacements.shape)


def cubic_forces(fc3, displacements, row_map, compact_map):
    result = np.zeros_like(displacements)
    inverse_maps = np.argsort(compact_map, axis=1)
    for representative, tensor in enumerate(fc3):
        active = np.any(tensor != 0.0, axis=(1, 2, 3, 4)) | np.any(tensor != 0.0, axis=(0, 2, 3, 4))
        neighbors = np.flatnonzero(active)
        if not len(neighbors):
            continue
        leading_atoms = np.flatnonzero(row_map == representative)
        indices = inverse_maps[leading_atoms][:, neighbors]
        shifted = displacements[:, indices, :].reshape(-1, 3 * len(neighbors))
        block = tensor[neighbors][:, neighbors].transpose(2, 0, 3, 1, 4).reshape(3, 3 * len(neighbors), 3 * len(neighbors))
        values = np.stack([-0.5 * np.sum((shifted @ matrix) * shifted, axis=1) for matrix in block], axis=1)
        result[:, leading_atoms, :] = values.reshape(len(displacements), len(leading_atoms), 3)
    return result


def mixed_forces(output, displacements, input_data):
    harmonic = fold_harmonic(output["fc2"], input_data)
    return harmonic_forces(harmonic, displacements, input_data["s2p3"], input_data["compact_map3"]) + cubic_forces(output["fc3"], displacements, input_data["s2p3"], input_data["compact_map3"])


def normalized_norm(values, denominator):
    return float(np.linalg.norm(values.ravel()) / max(float(denominator), 1e-30))


def invariant_errors(output, input_data):
    fc2 = output["fc2"]
    fc3 = output["fc3"]
    norm2 = max(float(np.linalg.norm(fc2.ravel())), 1e-30)
    norm3 = max(float(np.linalg.norm(fc3.ravel())), 1e-30)
    map2 = input_data["compact_map2"]
    map3 = input_data["compact_map3"]
    rows2 = input_data["s2p2"]
    rows3 = input_data["s2p3"]
    acoustic2 = [normalized_norm(fc2.sum(axis=1), norm2)]
    acoustic3 = [normalized_norm(fc3.sum(axis=1), norm3), normalized_norm(fc3.sum(axis=2), norm3)]
    leading2 = []
    leading3 = []
    permutation2 = 0.0
    permutation3 = float(np.sum((fc3 - fc3.transpose(0, 2, 1, 3, 5, 4)) ** 2))
    for representative, leading_atom in enumerate(input_data["p2s2"]):
        reverse = fc2[rows2, map2[:, leading_atom]].transpose(0, 2, 1)
        permutation2 += float(np.sum((fc2[representative] - reverse) ** 2))
        leading2.append(fc2[rows2, map2[:, leading_atom]].sum(axis=0))
    for representative, leading_atom in enumerate(input_data["p2s3"]):
        first_sum = np.zeros_like(fc3[representative, 0])
        for displaced_atom in range(len(rows3)):
            reverse = fc3[rows3[displaced_atom], map3[displaced_atom, leading_atom], map3[displaced_atom]].transpose(0, 2, 1, 3)
            permutation3 += float(np.sum((fc3[representative, displaced_atom] - reverse) ** 2))
            first_sum += fc3[rows3[displaced_atom], map3[displaced_atom, leading_atom], map3[displaced_atom]]
        leading3.append(first_sum)
    acoustic2.append(normalized_norm(np.asarray(leading2), norm2))
    acoustic3.append(normalized_norm(np.asarray(leading3), norm3))
    crystal2 = 0.0
    crystal3 = 0.0
    for rotation, permutation in zip(input_data["cart_rotations2"], input_data["permutations2"]):
        for representative, leading_atom in enumerate(input_data["p2s2"]):
            transformed_atom = permutation[leading_atom]
            actual = fc2[rows2[transformed_atom], map2[transformed_atom, permutation]]
            expected = np.einsum("ad,be,jde->jab", rotation, rotation, fc2[representative], optimize=True)
            crystal2 += float(np.sum((actual - expected) ** 2))
    for rotation, permutation in zip(input_data["cart_rotations3"], input_data["permutations3"]):
        for representative, leading_atom in enumerate(input_data["p2s3"]):
            transformed_atom = permutation[leading_atom]
            indices = map3[transformed_atom, permutation]
            actual = fc3[rows3[transformed_atom]][indices][:, indices]
            expected = np.einsum("ad,be,cf,jkdef->jkabc", rotation, rotation, rotation, fc3[representative], optimize=True)
            crystal3 += float(np.sum((actual - expected) ** 2))
    return {
        "acoustic_fc2": float(np.sqrt(np.mean(np.square(acoustic2)))),
        "acoustic_fc3": float(np.sqrt(np.mean(np.square(acoustic3)))),
        "permutation_fc2": float(np.sqrt(permutation2) / norm2),
        "permutation_fc3": float(np.sqrt(permutation3 / 2.0) / norm3),
        "spacegroup_fc2": float(np.sqrt(crystal2 / len(input_data["permutations2"])) / norm2),
        "spacegroup_fc3": float(np.sqrt(crystal3 / len(input_data["permutations3"])) / norm3),
        "support_fc3": normalized_norm(fc3[~input_data["triplet_mask3"]], norm3),
    }


def tensor_shapes(input_data):
    primitive_count = len(input_data["p2s2"])
    return {
        "fc2": (primitive_count, len(input_data["numbers2"]), 3, 3),
        "fc3": (primitive_count, len(input_data["numbers3"]), len(input_data["numbers3"]), 3, 3, 3),
    }


def validate_output(output, input_data):
    for key, shape in tensor_shapes(input_data).items():
        if key not in output:
            raise ValueError(f"missing output key {key}")
        if output[key].shape != shape:
            raise ValueError(f"{key} shape {output[key].shape} != {shape}")
        if output[key].dtype != np.dtype("float64"):
            raise ValueError(f"{key} must be float64, got {output[key].dtype}")
        if not np.all(np.isfinite(output[key])):
            raise ValueError(f"{key} contains non-finite values")


def error_metrics(output, reference, input_data):
    validate_output(output, input_data)
    metrics = {
        key + "_relative_error": normalized_norm(output[key] - reference[key], np.linalg.norm(reference[key].ravel()))
        for key in ("fc2", "fc3")
    }
    metrics.update(invariant_errors(output, input_data))
    prediction3 = mixed_forces(output, reference["heldout_u3"], input_data)
    metrics["heldout_force3_rmse"] = float(np.sqrt(np.mean((prediction3 - reference["heldout_f3"]) ** 2)))
    if len(reference["heldout_u2"]):
        prediction2 = harmonic_forces(output["fc2"], reference["heldout_u2"], input_data["s2p2"], input_data["compact_map2"])
        metrics["heldout_force2_rmse"] = float(np.sqrt(np.mean((prediction2 - reference["heldout_f2"]) ** 2)))
    else:
        metrics["heldout_force2_rmse"] = 0.0
    return metrics
