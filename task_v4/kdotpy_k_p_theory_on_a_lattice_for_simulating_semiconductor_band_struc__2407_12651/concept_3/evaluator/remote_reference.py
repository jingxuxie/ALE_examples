import numpy as np

import reference as core
from remote_model import assemble, coordinate_grid, evaluate_fourier, manufacture, remote_terms


FAMILY = "parity_mixed"
STRENGTH = 1.0
PAULI_X = np.zeros((4, 4), complex)
PAULI_Y = np.zeros((4, 4), complex)
PAULI_Z = np.zeros((4, 4), complex)
PAULI_X[:2, :2] = core.PAULI_X
PAULI_Y[:2, :2] = core.PAULI_Y
PAULI_Z[:2, :2] = core.PAULI_Z


def fourier_hoppings(witness):
    return assemble(witness, FAMILY, STRENGTH)


def matrix_values(hoppings, horizontal, vertical):
    return evaluate_fourier(hoppings, horizontal, vertical)


def spectral_certificate(witness, config, mesh=None, shift=(0.0, 0.0), dense_solver=True):
    mesh = config["spectral_mesh"] if mesh is None else mesh
    count = config["uncertainty_grid"]
    horizontal, vertical = coordinate_grid(mesh, shift)
    hoppings = fourier_hoppings(witness)
    nominal = matrix_values(hoppings, horizontal, vertical)
    first, second, norm_sum = core.derivative_bounds(hoppings, config["anisotropy_radius"])
    lengths = np.array([2*np.pi/mesh, 2*np.pi/mesh, 2*config["mass_error_radius"]/(count-1), 2*config["anisotropy_radius"]/(count-1)])
    lipschitz = np.array([first[0], first[1], 1.0, np.sqrt(2.0)])
    padding = 2e-10 * (1.0 + norm_sum)
    scenarios = []
    for mass_error in np.linspace(-config["mass_error_radius"], config["mass_error_radius"], count):
        for anisotropy in np.linspace(-config["anisotropy_radius"], config["anisotropy_radius"], count):
            spectrum = np.linalg.eigvalsh(manufacture(nominal, horizontal, vertical, mass_error, anisotropy))
            lower, upper = spectrum[..., 0], spectrum[..., 1]
            scenarios.append({"mass_error": float(mass_error), "anisotropy": float(anisotropy), "width": float(np.ptp(lower)), "direct": float(np.min(upper-lower)), "indirect": float(np.min(upper)-np.max(lower)), "gap12": float(np.min(spectrum[..., 2]-upper))})
    width = max(row["width"] for row in scenarios)
    direct = min(row["direct"] for row in scenarios)
    indirect = min(row["indirect"] for row in scenarios)
    gap12 = min(row["gap12"] for row in scenarios)
    gap01_star = direct - float(lipschitz @ lengths) - padding
    gap12_star = gap12 - float(lipschitz @ lengths) - padding
    tail = core.coefficient_error(witness, config["relative_coefficient_radius"])
    if min(gap01_star, gap12_star - 2*tail) <= 0.0:
        return {"certified": False, "reason": "gap01_or_gap12_not_uniformly_certified", "preliminary_gap_01": gap01_star, "preliminary_gap_12": gap12_star}
    hessian0 = np.array([second[0], second[1], 0.0, 0.0]) + 2*lipschitz**2/gap01_star
    hessian1 = np.array([second[0], second[1], 0.0, 0.0]) + 2*lipschitz**2/min(gap01_star, gap12_star)
    epsilon0 = float(hessian0 @ lengths**2 / 8.0) + padding
    epsilon1 = float(hessian1 @ lengths**2 / 8.0) + padding
    margin = epsilon0 + epsilon1 + 2*tail
    return {"certified": True, "dimension": 4, "mesh": mesh, "uncertainty_grid": count, "sampled_worst_bandwidth": width, "sampled_direct_gap": direct, "sampled_indirect_gap": indirect, "sampled_gap12": gap12, "preliminary_gap_01": gap01_star, "preliminary_gap_12": gap12_star, "certified_gap12_lower": gap12_star-2*tail, "hamiltonian_lipschitz": lipschitz.tolist(), "lower_hessian_bound": hessian0.tolist(), "upper_hessian_bound": hessian1.tolist(), "lower_interpolation_error": epsilon0, "upper_interpolation_error": epsilon1, "coefficient_error_radius": tail, "fourier_norm_sum": norm_sum, "certified_bandwidth": width+2*(epsilon0+tail), "certified_direct_gap": direct-margin, "certified_indirect_gap": indirect-margin, "scenarios": scenarios}


def topology_certificate(witness, mesh=128, shift=(0.0, 0.0), gauge_seed=None):
    anchor = core.topology_certificate(witness, mesh, shift, gauge_seed)
    if not anchor["certified"]:
        return {"certified": False, "reason": "core_continuum_topology_not_certified", "core": anchor}
    horizontal, vertical = coordinate_grid(mesh, shift)
    initial_hoppings = assemble(witness, FAMILY, 0.0)
    final_hoppings = fourier_hoppings(witness)
    initial = matrix_values(initial_hoppings, horizontal, vertical)
    final = matrix_values(final_hoppings, horizontal, vertical)
    initial_first, _, _ = core.derivative_bounds(initial_hoppings, 0.0)
    final_first, _, _ = core.derivative_bounds(final_hoppings, 0.0)
    active_spectrum = np.linalg.eigvalsh(initial[..., :2, :2])
    ordering = 5.5-float(np.max(active_spectrum[..., 1]))-float(initial_first.sum())*np.pi/mesh
    difference = {}
    for displacement in set(initial_hoppings) | set(final_hoppings):
        difference[displacement] = final_hoppings.get(displacement, np.zeros((4, 4))) - initial_hoppings.get(displacement, np.zeros((4, 4)))
    coupling_bound = sum(core.upper_norm(matrix) for matrix in difference.values())
    minimum = float("inf")
    for fraction in np.linspace(0.0, 1.0, 9):
        spectrum = np.linalg.eigvalsh(initial + fraction*(final-initial))
        minimum = min(minimum, float(np.min(spectrum[..., 1]-spectrum[..., 0])))
    fill_error = float(np.maximum(initial_first, final_first).sum())*np.pi/mesh + coupling_bound/16.0
    homotopy_gap = minimum-2*fill_error-1e-9
    if ordering <= 0.0 or homotopy_gap <= 0.0:
        return {"certified": False, "reason": "remote_order_or_coupling_homotopy_not_certified", "remote_order_lower": ordering, "homotopy_gap_lower": homotopy_gap}
    _, vectors = np.linalg.eigh(final)
    states = vectors[..., :, 0]
    if gauge_seed is not None:
        generator = np.random.default_rng(gauge_seed)
        states *= np.exp(1j*generator.uniform(-np.pi, np.pi, (mesh, mesh)))[..., None]
    link_x = np.einsum("...i,...i->...", states.conj(), np.roll(states, -1, axis=0))
    link_y = np.einsum("...i,...i->...", states.conj(), np.roll(states, -1, axis=1))
    overlap = float(min(np.abs(link_x).min(), np.abs(link_y).min()))
    flux = np.angle(link_x*np.roll(link_y, -1, axis=0)*np.conj(np.roll(link_x, -1, axis=1))*np.conj(link_y))
    chern = float(flux.sum()/(2*np.pi))
    agreed = overlap > 1e-8 and float(np.abs(flux).max()) < np.pi/2 and abs(chern-anchor["chern"]) < 2e-8
    return {"certified": bool(agreed), "chern": anchor["chern"], "fhs_chern": chern, "core_sphere_degree": anchor["sphere_degree"], "remote_order_lower": ordering, "homotopy_gap_lower": homotopy_gap, "homotopy_sampled_gap": minimum, "homotopy_fill_error": fill_error, "minimum_link_overlap": overlap, "maximum_plaquette_flux": float(np.abs(flux).max()), "core": anchor}
