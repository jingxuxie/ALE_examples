import itertools
import math

import numpy as np


IDENTITY = np.eye(2, dtype=complex)
PAULI_X = np.array([[0, 1], [1, 0]], dtype=complex)
PAULI_Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
PAULI_Z = np.diag([1.0, -1.0]).astype(complex)
SPIN_ORDERS = [(order, cross) for order in range(1, 4) for cross in range(4) if (order, cross) != (1, 0)]
EVEN_ORDERS = [(order, cross) for order in range(1, 4) for cross in range(order + 1)]


def trig_expansion(order, sine):
    if sine:
        return [(order, -0.5j), (-order, 0.5j)]
    return [(order, 0.5), (-order, 0.5)]


def add_product(hoppings, amplitude, matrix, horizontal, vertical, sine_x=False, sine_y=False):
    for (first, weight_x), (second, weight_y) in itertools.product(trig_expansion(horizontal, sine_x), trig_expansion(vertical, sine_y)):
        key = (first, second)
        if key not in hoppings:
            hoppings[key] = np.zeros((2, 2), dtype=complex)
        hoppings[key] += amplitude * weight_x * weight_y * matrix


def fourier_hoppings(witness):
    hoppings = {(0, 0): witness["mass"] * PAULI_Z.copy()}
    add_product(hoppings, 1.0, PAULI_X, 1, 0, sine_x=True)
    add_product(hoppings, 1.0, PAULI_Y, 0, 1, sine_y=True)
    for coefficient, (order, cross) in zip(witness["spin_orbit"], SPIN_ORDERS):
        add_product(hoppings, coefficient, PAULI_X, order, cross, sine_x=True)
        add_product(hoppings, coefficient, PAULI_Y, cross, order, sine_y=True)
    for channel, matrix in (("orbital_mass", PAULI_Z), ("scalar", IDENTITY)):
        for coefficient, (order, cross) in zip(witness[channel], EVEN_ORDERS):
            add_product(hoppings, coefficient, matrix, order, cross)
            if order != cross:
                add_product(hoppings, coefficient, matrix, cross, order)
    return {key: value for key, value in hoppings.items() if np.any(value != 0.0)}


def matrix_values(hoppings, horizontal, vertical):
    horizontal, vertical = np.broadcast_arrays(horizontal, vertical)
    result = np.zeros(horizontal.shape + (2, 2), dtype=complex)
    for (first, second), matrix in hoppings.items():
        phase = np.exp(1j * (first * horizontal + second * vertical))
        result += phase[..., None, None] * matrix
    return result


def upper_norm(matrix):
    return float(np.linalg.norm(matrix, ord=2)) * (1.0 + 1e-12) + 1e-14


def derivative_bounds(hoppings, strain_radius):
    first = np.zeros(2)
    second = np.zeros(2)
    norm_sum = 0.0
    for displacement, matrix in hoppings.items():
        norm = upper_norm(matrix)
        norm_sum += norm
        first += np.abs(displacement) * norm
        second += np.square(displacement) * norm
    return first + strain_radius, second + strain_radius, float(norm_sum)


def coefficient_error(witness, relative_radius):
    total = math.sqrt(2.0) * sum(abs(value) for value in witness["spin_orbit"])
    for channel in ("orbital_mass", "scalar"):
        total += sum(abs(value) * (1 if order == cross else 2) for value, (order, cross) in zip(witness[channel], EVEN_ORDERS))
    return relative_radius * total * (1.0 + 1e-12) + 1e-13


def spectral_certificate(witness, config, mesh=None, shift=(0.0, 0.0), dense_solver=True):
    mesh = config["spectral_mesh"] if mesh is None else mesh
    count = config["uncertainty_grid"]
    mass_radius = config["mass_error_radius"]
    strain_radius = config["anisotropy_radius"]
    hoppings = fourier_hoppings(witness)
    axis = 2.0 * np.pi * np.arange(mesh) / mesh - np.pi
    horizontal, vertical = np.meshgrid(axis + shift[0] * 2.0 * np.pi / mesh, axis + shift[1] * 2.0 * np.pi / mesh, indexing="ij")
    nominal = matrix_values(hoppings, horizontal, vertical)
    strain = np.sin(horizontal)[..., None, None] * PAULI_X - np.sin(vertical)[..., None, None] * PAULI_Y
    hermiticity = float(np.max(np.abs(nominal - np.swapaxes(nominal.conj(), -1, -2))))
    if hermiticity > 2e-10:
        raise ValueError("internal_fourier_hermiticity_failure")
    worst_width = 0.0
    minimum_direct = float("inf")
    minimum_indirect = float("inf")
    scenarios = []
    for mass_error in np.linspace(-mass_radius, mass_radius, count):
        for anisotropy in np.linspace(-strain_radius, strain_radius, count):
            matrix = nominal + mass_error * PAULI_Z + anisotropy * strain
            if dense_solver:
                eigenvalues = np.linalg.eigvalsh(matrix)
                lower, upper = eigenvalues[..., 0], eigenvalues[..., 1]
            else:
                center = 0.5 * (matrix[..., 0, 0].real + matrix[..., 1, 1].real)
                radius = np.sqrt(0.25 * np.square((matrix[..., 0, 0] - matrix[..., 1, 1]).real) + np.square(np.abs(matrix[..., 0, 1])))
                lower, upper = center - radius, center + radius
            width = float(np.max(lower) - np.min(lower))
            direct = float(np.min(upper - lower))
            indirect = float(np.min(upper) - np.max(lower))
            worst_width = max(worst_width, width)
            minimum_direct = min(minimum_direct, direct)
            minimum_indirect = min(minimum_indirect, indirect)
            scenarios.append({"mass_error": float(mass_error), "anisotropy": float(anisotropy), "width": width, "direct": direct, "indirect": indirect})
    first, second, norm_sum = derivative_bounds(hoppings, strain_radius)
    lengths = np.array([2.0 * np.pi / mesh, 2.0 * np.pi / mesh, 2.0 * mass_radius / (count - 1), 2.0 * strain_radius / (count - 1)])
    lipschitz = np.array([first[0], first[1], 1.0, np.sqrt(2.0)])
    padding = 2e-10 * (1.0 + norm_sum)
    preliminary_gap = minimum_direct - float(lipschitz @ lengths) - padding
    if preliminary_gap <= 0.0:
        return {"certified": False, "reason": "first_order_gap_certificate_failed", "preliminary_gap": preliminary_gap, "sampled_direct_gap": minimum_direct}
    hessian = np.array([second[0], second[1], 0.0, 0.0]) + 2.0 * lipschitz**2 / preliminary_gap
    interpolation_error = float(hessian @ lengths**2 / 8.0) + padding
    tail = coefficient_error(witness, config["relative_coefficient_radius"])
    margin = 2.0 * (interpolation_error + tail)
    return {
        "certified": True,
        "certificate_kind": "analytic_uniform_bounds_float64_with_safety_padding",
        "mesh": mesh,
        "uncertainty_grid": count,
        "grid_shift": list(shift),
        "sampled_worst_bandwidth": worst_width,
        "sampled_direct_gap": minimum_direct,
        "sampled_indirect_gap": minimum_indirect,
        "preliminary_gap": preliminary_gap,
        "hamiltonian_lipschitz": lipschitz.tolist(),
        "eigenvalue_second_derivative_bound": hessian.tolist(),
        "continuum_energy_error": interpolation_error,
        "coefficient_error_radius": tail,
        "fourier_norm_sum": norm_sum,
        "certified_bandwidth": worst_width + margin,
        "certified_direct_gap": minimum_direct - margin,
        "certified_indirect_gap": minimum_indirect - margin,
        "scenarios": scenarios,
    }


def spherical_area(first, second, third):
    numerator = np.einsum("...i,...i->...", first, np.cross(second, third))
    denominator = 1.0 + np.einsum("...i,...i->...", first, second) + np.einsum("...i,...i->...", second, third) + np.einsum("...i,...i->...", third, first)
    return 2.0 * np.arctan2(numerator, denominator)


def topology_certificate(witness, mesh=128, shift=(0.0, 0.0), gauge_seed=None):
    hoppings = fourier_hoppings(witness)
    axis = 2.0 * np.pi * np.arange(mesh) / mesh - np.pi
    horizontal, vertical = np.meshgrid(axis + shift[0] * 2.0 * np.pi / mesh, axis + shift[1] * 2.0 * np.pi / mesh, indexing="ij")
    matrix = matrix_values(hoppings, horizontal, vertical)
    eigenvalues, eigenvectors = np.linalg.eigh(matrix)
    states = eigenvectors[..., :, 0]
    if gauge_seed is not None:
        generator = np.random.default_rng(gauge_seed)
        states = states * np.exp(1j * generator.uniform(-np.pi, np.pi, (mesh, mesh)))[..., None]
    link_x = np.einsum("...i,...i->...", states.conj(), np.roll(states, -1, axis=0))
    link_y = np.einsum("...i,...i->...", states.conj(), np.roll(states, -1, axis=1))
    minimum_overlap = float(min(np.min(np.abs(link_x)), np.min(np.abs(link_y))))
    if minimum_overlap < 1e-8:
        return {"certified": False, "reason": "singular_link"}
    link_x /= np.abs(link_x)
    link_y /= np.abs(link_y)
    flux = np.angle(link_x * np.roll(link_y, -1, axis=0) * np.conj(np.roll(link_x, -1, axis=1)) * np.conj(link_y))
    chern = float(np.sum(flux) / (2.0 * np.pi))
    vector = np.stack((matrix[..., 0, 1].real, -matrix[..., 0, 1].imag, 0.5 * (matrix[..., 0, 0] - matrix[..., 1, 1]).real), axis=-1)
    radius = np.linalg.norm(vector, axis=-1)
    first, _, _ = derivative_bounds(hoppings, 0.0)
    cell_radius_bound = float(np.sum(first) * 2.0 * np.pi / mesh + 1e-10)
    minimum_radius = float(np.min(radius))
    if cell_radius_bound >= minimum_radius:
        return {"certified": False, "reason": "continuum_topology_homotopy_not_certified", "cell_radius_bound": cell_radius_bound, "minimum_radius": minimum_radius}
    sphere = vector / radius[..., None]
    next_x = np.roll(sphere, -1, axis=0)
    next_y = np.roll(sphere, -1, axis=1)
    next_xy = np.roll(next_x, -1, axis=1)
    degree = float(np.sum(spherical_area(sphere, next_x, next_xy) + spherical_area(sphere, next_xy, next_y)) / (4.0 * np.pi))
    integer = int(round(chern))
    agreement = abs(chern - integer) < 2e-8 and abs(degree + integer) < 2e-8 and np.max(np.abs(flux)) < np.pi / 2.0
    return {
        "certified": bool(agreement),
        "chern": integer,
        "fhs_chern": chern,
        "sphere_degree": degree,
        "minimum_link_overlap": minimum_overlap,
        "maximum_plaquette_flux": float(np.max(np.abs(flux))),
        "cell_radius_bound": cell_radius_bound,
        "minimum_radius": minimum_radius,
        "homotopy_margin": minimum_radius - cell_radius_bound,
        "mesh": mesh,
        "grid_shift": list(shift),
        "reason": "certified" if agreement else "independent_topology_checks_disagree",
    }
