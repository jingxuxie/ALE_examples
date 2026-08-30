import numpy as np
from scipy.sparse.linalg import eigsh


def signed_frequency_eigenvalue(modes, weights, energies, temperature, count, boltzmann):
    thermal = boltzmann * temperature
    patches = len(weights)
    indices = np.arange(-count, count)
    signed_omega = np.pi * thermal * (2 * indices + 1)
    row_sums = np.array([[np.dot(matrix[patch], weights) for patch in range(patches)] for matrix in modes])
    normal_count = 4 * count + 64
    normal_indices = np.arange(-normal_count, normal_count)
    normal_omega = np.pi * thermal * (2 * normal_indices + 1)
    signs = np.sign(normal_omega)
    positive_z = np.ones((patches, count))
    for positive_index in range(count):
        omega = np.pi * thermal * (2 * positive_index + 1)
        tail_indices = np.arange(normal_count - positive_index, normal_count + positive_index + 1)
        tail_transfer = 2 * np.pi * thermal * tail_indices
        for mode, energy in enumerate(energies):
            finite_sum = np.dot(energy ** 2 / ((omega - normal_omega) ** 2 + energy ** 2), signs)
            exact_tail = np.sum(energy ** 2 / (tail_transfer ** 2 + energy ** 2))
            positive_z[:, positive_index] += row_sums[mode] * (finite_sum + exact_tail) / (2 * positive_index + 1)
    normal_z = np.concatenate((positive_z[:, ::-1], positive_z), axis=1)
    differences = signed_omega[:, None] - signed_omega[None]
    dimension = patches * 2 * count
    interaction = np.zeros((patches, 2 * count, patches, 2 * count))
    for mode, energy in enumerate(energies):
        frequency = energy ** 2 / (differences ** 2 + energy ** 2)
        interaction += modes[mode, :, None, :, None] * frequency[None, :, None, :]
    scale = np.sqrt(weights[:, None] / (np.abs(signed_omega)[None] * normal_z)).ravel()
    matrix = np.pi * thermal * interaction.reshape(dimension, dimension) * np.outer(scale, scale)
    asymmetry = float(np.max(np.abs(matrix - matrix.T)))
    eigenvalues, eigenvectors = eigsh(matrix, k=1, which="LA", tol=1e-12, v0=np.ones(dimension), maxiter=2000)
    residual = float(np.linalg.norm(matrix @ eigenvectors[:, 0] - eigenvalues[0] * eigenvectors[:, 0]))
    return {
        "eigenvalue": float(eigenvalues[0]), "residual": residual,
        "matrix_symmetry_error": asymmetry, "positive_z": positive_z,
    }


def independent_audit(kernels, instance, physics, solver_class):
    config = instance["config"]
    comparisons = []
    for family in physics["families"]:
        energies = np.asarray(family["energies_mev"])
        grid = family["grids"][0]
        count = grid["positive_count"]
        public_solver = solver_class(instance["weights"], instance["row_sums"], energies, config)
        for index, modes in enumerate(kernels):
            transition = grid["transitions"][index]
            temperature = transition["tc_kelvin"]
            signed = signed_frequency_eigenvalue(
                modes, instance["weights"], energies, temperature, count,
                config["boltzmann_mev_per_kelvin"],
            )
            public_z = public_solver.components(temperature, count)[2]
            normal_error = float(np.max(np.abs(signed.pop("positive_z") - public_z)))
            difference = abs(signed["eigenvalue"] - transition["eigenvalue"])
            comparisons.append({
                "family": family["name"], "kernel_index": index, "positive_count": count,
                "temperature_kelvin": temperature, **signed,
                "folded_signed_difference": difference, "normal_z_difference": normal_error,
                "passed": difference <= config["signed_audit_atol"] and normal_error <= 1e-8
                and signed["residual"] <= 1e-8 and signed["matrix_symmetry_error"] <= 1e-10,
            })
    regular = regular_row_control(instance, solver_class)
    return {
        "signed_frequency_comparisons": comparisons, "regular_row_control": regular,
        "passed": regular["passed"] and all(comparison["passed"] for comparison in comparisons),
    }


def regular_row_control(instance, solver_class):
    patches = 8
    weights = np.full(patches, 1 / patches)
    cycle = np.zeros((patches, patches))
    squares = np.zeros_like(cycle)
    for patch in range(patches):
        neighbor = (patch + 1) % patches
        cycle[patch, neighbor] = cycle[neighbor, patch] = 1
    for offset in (0, 4):
        for patch in range(4):
            neighbor = (patch + 1) % 4
            squares[offset + patch, offset + neighbor] = squares[offset + neighbor, offset + patch] = 1
    first = np.array([0.15 + 0.7 * np.roll(np.roll(cycle, mode, axis=0), mode, axis=1) for mode in range(3)])
    second = np.array([0.15 + 0.7 * np.roll(np.roll(squares, mode, axis=0), mode, axis=1) for mode in range(3)])
    rows = first @ weights
    solver = solver_class(weights, rows, instance["energies_mev"], instance["config"])
    count = 32
    first_tc = solver.critical_temperature(first, count)["tc_kelvin"]
    second_tc = solver.critical_temperature(second, count)["tc_kelvin"]
    isotropic = solver_class(np.ones(1), rows[:, :1], instance["energies_mev"], instance["config"])
    isotropic_tc = isotropic.critical_temperature(rows[:, :1, None], count)["tc_kelvin"]
    signed_values = [signed_frequency_eigenvalue(
        modes, weights, instance["energies_mev"], isotropic_tc, count,
        instance["config"]["boltzmann_mev_per_kelvin"],
    )["eigenvalue"] for modes in (first, second)]
    spread = max(first_tc, second_tc, isotropic_tc) - min(first_tc, second_tc, isotropic_tc)
    passed = spread <= 1e-6 and max(abs(value - 1) for value in signed_values) <= 2e-6
    return {
        "passed": passed, "positive_count": count,
        "temperatures_kelvin": [first_tc, second_tc, isotropic_tc],
        "temperature_spread_kelvin": spread, "signed_eigenvalues": signed_values,
        "row_error": float(np.max(np.abs(first @ weights - second @ weights))),
    }
