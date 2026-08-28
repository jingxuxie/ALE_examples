import numpy as np
from scipy import sparse
from scipy.linalg import eigh, expm
from scipy.sparse.csgraph import connected_components

import engine


def block_evolve(compiled, initial_density, times, method="commuting_eigh"):
    dissipator = compiled["dissipator"].tocsr()
    adjacency = dissipator.copy()
    adjacency.data = np.ones(len(adjacency.data), dtype=float)
    count, labels = connected_components(adjacency, directed=False)
    sizes = np.bincount(labels, minlength=count)
    order = np.argsort(labels, kind="stable")
    boundaries = np.r_[0, np.cumsum(sizes)]
    coherent = -1j * (compiled["energies"][:, None] - compiled["energies"][None, :]).ravel(order="F")
    times = np.asarray(times, dtype=float)
    trajectory = np.zeros((len(times), len(initial_density)), dtype=complex)
    singleton_indices = np.flatnonzero(sizes[labels] == 1)
    diagonal = dissipator.diagonal() + coherent
    trajectory[:, singleton_indices] = np.exp(np.outer(times, diagonal[singleton_indices])) * initial_density[singleton_indices]
    largest_frequency_spread = 0.0
    largest_decay_eigenvalue = -np.inf
    effective_commutator_squared = 0.0
    refined_blocks = 0
    maximum_slices = 1
    for component in np.flatnonzero(sizes > 1):
        indices = order[boundaries[component]:boundaries[component + 1]]
        block = dissipator[indices][:, indices].toarray()
        frequencies = coherent[indices]
        largest_frequency_spread = max(largest_frequency_spread, float(np.ptp(frequencies.imag)))
        initial = initial_density[indices]
        if method == "commuting_eigh":
            decay, basis = eigh((block + block.conj().T) / 2, check_finite=False)
            largest_decay_eigenvalue = max(largest_decay_eigenvalue, float(decay[-1]))
            block_commutator = float(np.linalg.norm(block * (frequencies[None, :] - frequencies[:, None])))
            slices = max(1, int(np.ceil(0.5 * times[-1]**2 * block_commutator / 1e-10)))
            effective_commutator_squared += (block_commutator / slices)**2
            maximum_slices = max(maximum_slices, slices)
            if slices == 1:
                coefficients = basis.conj().T @ initial
                evolved = (basis @ (np.exp(np.outer(decay, times)) * coefficients[:, None])).T
                trajectory[:, indices] = evolved * np.exp(np.outer(times, frequencies))
            else:
                refined_blocks += 1
                center = np.mean(frequencies)
                for time_index, elapsed in enumerate(times):
                    if elapsed == 0:
                        trajectory[time_index, indices] = initial
                        continue
                    decay_step = (basis * np.exp(decay * elapsed / slices)) @ basis.conj().T
                    half_phase = np.exp((frequencies - center) * elapsed / (2 * slices))
                    step = half_phase[:, None] * decay_step * half_phase[None, :]
                    trajectory[time_index, indices] = np.exp(center * elapsed) * (
                        np.linalg.matrix_power(step, slices) @ initial)
        elif method == "centered_expm":
            center = np.mean(frequencies)
            centered = block + np.diag(frequencies - center)
            for time_index, elapsed in enumerate(times):
                trajectory[time_index, indices] = np.exp(center * elapsed) * (expm(centered * elapsed) @ initial)
        else:
            raise ValueError(method)
    entries = dissipator.tocoo()
    commutator_norm = float(np.linalg.norm(entries.data * (coherent[entries.col] - coherent[entries.row])))
    hermiticity_defect = float(sparse.linalg.norm(dissipator - dissipator.getH()))
    off_block_norm = float(np.linalg.norm(entries.data[labels[entries.row] != labels[entries.col]]))
    denominator = max(float(sparse.linalg.norm(dissipator)) * float(np.linalg.norm(coherent)), 1e-300)
    diagnostics = dict(
        method=method, block_count=int(count), largest_block=int(sizes.max()),
        nonsingleton_blocks=int(np.sum(sizes > 1)), generator_nnz=int(compiled["generator"].nnz),
        discarded_off_block_norm=off_block_norm,
        dissipator_hermiticity_defect=hermiticity_defect,
        commutator_frobenius=commutator_norm,
        commutator_relative=commutator_norm / denominator,
        commutator_time_squared_indicator=0.5 * times[-1]**2 * commutator_norm,
        commutator_splitting_indicator=0.5 * times[-1]**2 * np.sqrt(effective_commutator_squared),
        refined_commuting_blocks=refined_blocks,
        maximum_commuting_slices=maximum_slices,
        dissipator_hermiticity_time_indicator=times[-1] * hermiticity_defect,
        largest_component_frequency_spread=largest_frequency_spread,
        largest_decay_eigenvalue=(largest_decay_eigenvalue if np.isfinite(largest_decay_eigenvalue) else None),
    )
    if off_block_norm != 0:
        raise ArithmeticError("nonzero discarded generator couplings")
    if method == "commuting_eigh" and (diagnostics["commutator_splitting_indicator"] > 1e-7
                                      or diagnostics["dissipator_hermiticity_time_indicator"] > 1e-8):
        raise ArithmeticError("commuting/Hermitian approximation is not numerically justified")
    return trajectory, diagnostics


def predict(case, operators, compiled, method):
    basis = compiled["vectors"]
    dimension = len(basis)
    initial = basis.conj().T @ operators["initial"]
    initial_density = np.outer(initial, initial.conj()).ravel(order="F")
    trajectory, diagnostics = block_evolve(compiled, initial_density, case["times"], method)
    densities = np.array([row.reshape((dimension, dimension), order="F") for row in trajectory])
    energies, ideal_basis = np.linalg.eigh(operators["hzero"])
    coefficients = ideal_basis.conj().T @ operators["initial"]
    ideal = ideal_basis @ (np.exp(-1j * np.outer(energies, case["times"])) * coefficients[:, None])
    ideal_in_basis = (basis.conj().T @ ideal).T

    def expectation(operator):
        return np.einsum("ij,tji->t", basis.conj().T @ operator @ basis, densities).real

    result = dict(
        gauge=expectation(operators["gauge"]).tolist(),
        fidelity=np.einsum("ti,tij,tj->t", ideal_in_basis.conj(), densities, ideal_in_basis).real.tolist(),
        electric=expectation(operators["electric"]).tolist(),
        density=np.array([expectation(operator) for operator in operators["occupancies"]]).T.tolist(),
    )
    diagnostics.update(
        trace_error=float(np.max(np.abs(np.trace(densities, axis1=1, axis2=2) - 1))),
        state_hermiticity_error=float(max(np.linalg.norm(density - density.conj().T) for density in densities)),
        minimum_eigenvalue=float(min(np.linalg.eigvalsh((density + density.conj().T) / 2).min() for density in densities)),
    )
    if diagnostics["trace_error"] > 2e-9 or diagnostics["state_hermiticity_error"] > 2e-9 or diagnostics["minimum_eigenvalue"] < -2e-9:
        raise ArithmeticError("late-time density-matrix invariants failed")
    return result, diagnostics, densities


def solve_detailed(case, method="commuting_eigh"):
    operators = engine.build_model(case)
    fitted = engine.fit_bath(case["calibration"])
    bath_channels = engine.channels(case, operators, fitted["eta"])
    audit = case["audit"]
    audit_compiled = engine.secular_generator(
        engine.hamiltonian(case, operators, audit["action"]),
        engine.channels(case, operators, audit["bath"]["eta"]), audit["bath"])
    result = dict(bath=fitted, audit=engine.audit_response(audit_compiled, audit["states"]), predictions={})
    diagnostics, all_densities = {}, {}
    for action in engine.feasible_actions(case):
        compiled = engine.secular_generator(engine.hamiltonian(case, operators, action), bath_channels, fitted)
        prediction, details, densities = predict(case, operators, compiled, method)
        result["predictions"][action["id"]] = prediction
        diagnostics[action["id"]] = details
        all_densities[action["id"]] = densities
    result["selected_action"] = min(result["predictions"], key=lambda identifier: engine.risk(case, result["predictions"][identifier]))
    return result, diagnostics, all_densities


def solve(case: dict) -> dict:
    return solve_detailed(case)[0]
