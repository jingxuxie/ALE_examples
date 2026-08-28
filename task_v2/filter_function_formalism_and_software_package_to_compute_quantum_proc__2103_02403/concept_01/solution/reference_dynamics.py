"""Private deterministic reference channels for piecewise-constant Hamiltonians.

All channels act on column-major vectorized density matrices in the laboratory
frame. Noise coordinates are stationary at the start, and their state is carried
through every segment. No Monte Carlo sampling or quantum-toolbox dependency is
used. Truncation errors are estimated by successive, independent refinements;
they are not rigorous bounds on the infinite-dimensional problem.
"""

from collections.abc import Mapping
from itertools import product
from math import ceil, comb, exp, log2
from time import perf_counter

import numpy as np
from scipy import sparse
from scipy.special import roots_hermitenorm


__all__ = ["solve_exact"]


def _real_array(value, name):
    array = np.asarray(value)
    if np.iscomplexobj(array):
        raise ValueError(f"{name} must be real")
    array = np.asarray(array, dtype=float)
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be finite")
    return array


def _parameter(law, name, latent_count):
    value = _real_array(law.get(name, np.ones(latent_count)), name)
    if value.ndim == 0:
        value = np.full(latent_count, float(value))
    if value.shape != (latent_count,) or np.any(value < 0):
        raise ValueError(f"{name} must have shape ({latent_count},) and be nonnegative")
    return value


def _prepare(dt, hamiltonians, noise_operators, law, tolerance):
    if not isinstance(law, Mapping):
        raise ValueError("law must be a mapping")
    kind = law.get("kind")
    if kind not in ("static", "ou", "telegraph", "white"):
        raise ValueError("law.kind must be static, ou, telegraph, or white")
    tolerance = float(tolerance)
    if not np.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("tolerance must be positive and finite")
    durations = _real_array(dt, "dt")
    if durations.ndim != 1 or np.any(durations < 0):
        raise ValueError("dt must be a one-dimensional array of nonnegative durations")
    controls = np.asarray(hamiltonians, dtype=complex)
    operators = np.asarray(noise_operators, dtype=complex)
    if (
        controls.ndim != 3
        or controls.shape[0] != len(durations)
        or controls.shape[1] != controls.shape[2]
        or controls.shape[1] == 0
    ):
        raise ValueError("hamiltonians must have shape (segments, d, d)")
    dimension = controls.shape[-1]
    if (
        operators.ndim != 4
        or operators.shape[0] != len(durations)
        or operators.shape[2:] != (dimension, dimension)
    ):
        raise ValueError("noise_operators must have shape (segments, channels, d, d)")
    for name, matrices in (("hamiltonians", controls), ("noise_operators", operators)):
        if not np.all(np.isfinite(matrices)) or not np.allclose(
            matrices, matrices.swapaxes(-1, -2).conj(), rtol=1e-12, atol=1e-13
        ):
            raise ValueError(f"{name} must be finite and Hermitian")
    if "mixing" not in law:
        raise ValueError("law must contain mixing with shape (channels, latent)")
    mixing = _real_array(law["mixing"], "mixing")
    if mixing.ndim != 2 or mixing.shape[0] != operators.shape[1]:
        raise ValueError("mixing must have shape (channels, latent)")
    latent_count = mixing.shape[1]
    sigma = _parameter(law, "sigma", latent_count)
    rates = _parameter(law, "rates", latent_count)
    controls = (controls + controls.swapaxes(-1, -2).conj()) * 0.5
    operators = (operators + operators.swapaxes(-1, -2).conj()) * 0.5
    loaded = np.einsum("am,sajk,m->smjk", mixing, operators, sigma, optimize=True)
    identity = np.eye(dimension)
    controls = controls - np.trace(controls, axis1=-2, axis2=-1)[..., None, None] * identity / dimension
    loaded = loaded - np.trace(loaded, axis1=-2, axis2=-1)[..., None, None] * identity / dimension
    if not np.all(np.isfinite(loaded)):
        raise ValueError("loaded noise coefficients overflowed")
    positive = durations > 0
    durations, controls, loaded = durations[positive], controls[positive], loaded[positive]
    active = np.any(loaded != 0, axis=(0, 2, 3))
    loaded, rates = loaded[:, active], rates[active]
    merged_durations, merged_controls, merged_loaded = [], [], []
    for duration, control, noise in zip(durations, controls, loaded):
        if merged_controls and np.array_equal(control, merged_controls[-1]) and np.array_equal(noise, merged_loaded[-1]):
            merged_durations[-1] += duration
        else:
            merged_durations.append(float(duration))
            merged_controls.append(control)
            merged_loaded.append(noise)
    durations = np.asarray(merged_durations)
    controls = np.asarray(merged_controls, dtype=complex).reshape(-1, dimension, dimension)
    loaded = np.asarray(merged_loaded, dtype=complex).reshape(len(durations), int(active.sum()), dimension, dimension)
    return durations, controls, loaded, rates, kind, tolerance, latent_count


def _unitary_channel(unitary):
    return np.kron(unitary.conj(), unitary)


def _clean_evolution(durations, controls):
    dimension = controls.shape[-1]
    eigenvalues, eigenvectors = np.linalg.eigh(controls)
    steps = (eigenvectors * np.exp(-1j * durations[:, None] * eigenvalues)[:, None, :]) @ eigenvectors.swapaxes(-1, -2).conj()
    prefixes = [np.eye(dimension, dtype=complex)]
    for step in steps:
        prefixes.append(step @ prefixes[-1])
    return steps, prefixes, eigenvalues, eigenvectors


def _commutator(operator):
    identity = np.eye(len(operator))
    return np.kron(identity, operator) - np.kron(operator.T, identity)


def _noise_strength(durations, loaded, kind):
    if loaded.size == 0:
        return 0.0
    eigenvalues = np.linalg.eigvalsh(loaded)
    spreads = eigenvalues[..., -1] - eigenvalues[..., 0]
    if kind == "white":
        return float(np.sqrt(np.sum(durations[:, None] * spreads ** 2)))
    return float(np.linalg.norm(np.sum(durations[:, None] * spreads, axis=0)))


def _taylor_degree(norm, steps=1):
    remainder, degree = exp(norm), 0
    while remainder > 2e-18 / steps:
        degree += 1
        remainder *= norm / degree
    return max(1, degree)


def _exponential_action(generator, state, duration):
    """Deterministic scaled Taylor action using an exact matrix 1-norm.

    A real scalar shift reduces stiff decay before scaling each substep's norm
    to at most four. The exponential-series tail bound selects the degree,
    without randomized norm estimates, early exits based on a large clean
    component, or changes to NumPy's random state.
    """
    scaled = generator * duration
    norm = float(np.asarray(abs(scaled).sum(axis=0)).max())
    if norm == 0:
        return state.copy()
    shift = 0.0
    if norm > 4:
        diagonal = scaled.diagonal().real
        candidate_shift = float((diagonal.min() + diagonal.max()) / 2)
        shifted = scaled - candidate_shift * sparse.eye(scaled.shape[0], format="csr")
        shifted_norm = float(np.asarray(abs(shifted).sum(axis=0)).max())
        if shifted_norm < norm:
            scaled, norm, shift = shifted, shifted_norm, candidate_shift
    steps = max(1, int(ceil(norm / 4)))
    scaled = scaled / steps
    degree = _taylor_degree(norm / steps, steps)
    scalar_factor = exp(shift / steps)
    result = state.copy()
    for _ in range(steps):
        term = result.copy()
        total = result.copy()
        for power in range(1, degree + 1):
            term = scaled.dot(term) / power
            total += term
        result = scalar_factor * total
    return result


def _unitary_difference(control, perturbations, duration, eigenvalues, eigenvectors):
    """Compute exp(-it(H+E))-exp(-itH) without subtracting unitaries."""
    dimension = len(control)
    norm = duration * (np.linalg.norm(control, 1) + np.max(np.sum(abs(perturbations), axis=1)))
    squarings = max(0, int(ceil(log2(max(1.0, 2 * norm)))))
    divisor = 2 ** squarings
    clean_generator = -1j * duration / divisor * control
    perturbation = -1j * duration / divisor * perturbations
    clean_term = np.eye(dimension, dtype=complex)
    delta_term = np.zeros_like(perturbation)
    delta = delta_term.copy()
    for power in range(1, _taylor_degree(norm / divisor) + 1):
        delta_term = (clean_generator @ delta_term + perturbation @ (clean_term + delta_term)) / power
        clean_term = clean_generator @ clean_term / power
        delta += delta_term
    clean_step = (eigenvectors * np.exp(-1j * duration / divisor * eigenvalues)) @ eigenvectors.conj().T
    for _ in range(squarings):
        delta = clean_step @ delta + delta @ clean_step + delta @ delta
        clean_step = clean_step @ clean_step
    return delta


def _average_channel(unitaries, weights):
    dimension = unitaries.shape[-1]
    return np.einsum("nik,njl,n->ijkl", unitaries, unitaries.conj(), weights).reshape(dimension ** 2, dimension ** 2, order="F")


def _static_correction(order, durations, controls, loaded, clean, small_noise):
    steps, prefixes, eigenvalues, eigenvectors = clean
    dimension, latent_count = controls.shape[-1], loaded.shape[1]
    nodes, weights = roots_hermitenorm(order)
    weights /= np.sqrt(2 * np.pi)
    total = np.zeros((dimension ** 2, dimension ** 2), dtype=complex)
    for offset in range(0, order ** latent_count, 2048):
        indices = np.asarray(np.unravel_index(np.arange(offset, min(offset + 2048, order ** latent_count)), (order,) * latent_count))
        coordinates = nodes[indices].T
        probabilities = np.prod(weights[indices], axis=0)
        batch_size = len(probabilities)
        if small_noise:
            delta = np.zeros((batch_size, dimension, dimension), dtype=complex)
            for segment, duration in enumerate(durations):
                perturbations = np.einsum("nm,mij->nij", coordinates, loaded[segment])
                delta_step = _unitary_difference(controls[segment], perturbations, duration, eigenvalues[segment], eigenvectors[segment])
                delta = steps[segment] @ delta + delta_step @ (prefixes[segment] + delta)
            mean_delta = np.einsum("n,nij->ij", probabilities, delta)
            total += np.kron(prefixes[-1].conj(), mean_delta) + np.kron(mean_delta.conj(), prefixes[-1]) + _average_channel(delta, probabilities)
        else:
            unitaries = np.broadcast_to(np.eye(dimension, dtype=complex), (batch_size, dimension, dimension)).copy()
            for duration, control, noise in zip(durations, controls, loaded):
                values, vectors = np.linalg.eigh(control + np.einsum("nm,mij->nij", coordinates, noise))
                step = (vectors * np.exp(-1j * duration * values)[:, None, :]) @ vectors.swapaxes(-1, -2).conj()
                unitaries = step @ unitaries
            total += _average_channel(unitaries, probabilities)
    if not small_noise:
        total -= _unitary_channel(prefixes[-1])
    return total


def _compositions(total, count):
    if count == 1:
        yield (total,)
    else:
        for first in range(total + 1):
            for remaining in _compositions(total - first, count - 1):
                yield (first,) + remaining


def _hermite_modes(degree, latent_count):
    return [mode for total in range(degree + 1) for mode in _compositions(total, latent_count)]


def _mode_operators(modes, rates, telegraph=False):
    mode_count, latent_count = len(modes), len(rates)
    lookup = {mode: index for index, mode in enumerate(modes)}
    couplings = []
    for latent in range(latent_count):
        rows, columns, values = [], [], []
        for index, mode in enumerate(modes):
            raised = list(mode)
            raised[latent] += 1
            neighbor = lookup.get(tuple(raised))
            if neighbor is not None:
                coefficient = 1.0 if telegraph else np.sqrt(raised[latent])
                rows.extend((index, neighbor))
                columns.extend((neighbor, index))
                values.extend((coefficient, coefficient))
        couplings.append(sparse.csr_matrix((values, (rows, columns)), shape=(mode_count, mode_count)))
    damping = -(2.0 if telegraph else 1.0) * (np.asarray(modes) @ rates)
    return damping, couplings


def _dynamic_correction(durations, controls, loaded, clean, damping, couplings, white=False):
    """Propagate a stationary hierarchy together with a clean anchor.

    The zero-mode stores rho_0-rho_clean, not rho_0. An auxiliary clean block
    drives this difference and is refreshed from the same noiseless unitary
    prefixes at every boundary. Higher modes are never reset. Telegraph uses
    the Walsh transform of the exact 2**latent finite-state Liouville equation.
    OU uses orthonormal probabilists' Hermites: couplings sqrt(n+1), damping
    -sum(n_m*rate_m), and initially only the stationary zero-mode.
    """
    dimension = controls.shape[-1]
    channel_size, mode_count = dimension ** 2, len(damping)
    identity = sparse.eye(channel_size, format="csr", dtype=complex)
    mode_identity = sparse.eye(mode_count, format="csr")
    drift = sparse.kron(sparse.diags(damping, format="csr"), identity, format="csr")
    state = np.zeros(((mode_count + 1) * channel_size, channel_size), dtype=complex)
    selector = sparse.csr_matrix(([1.0], ([0], [0])), shape=(mode_count, 1))
    zero_row = sparse.csr_matrix((channel_size, mode_count * channel_size), dtype=complex)
    for segment, (duration, control, noise) in enumerate(zip(durations, controls, loaded)):
        control_generator = sparse.csr_matrix(-1j * _commutator(control))
        generator = drift + sparse.kron(mode_identity, control_generator, format="csr")
        source = sparse.csr_matrix((mode_count * channel_size, channel_size), dtype=complex)
        for latent, operator in enumerate(noise):
            commutator = _commutator(operator)
            if white:
                noise_generator = sparse.csr_matrix(-0.5 * (commutator @ commutator))
                generator += noise_generator
                source += noise_generator
            else:
                noise_generator = sparse.csr_matrix(-1j * commutator)
                generator += sparse.kron(couplings[latent], noise_generator, format="csr")
                source += sparse.kron(couplings[latent] @ selector, noise_generator, format="csr")
        augmented = sparse.bmat([[generator, source], [zero_row, control_generator]], format="csr")
        state[-channel_size:] = _unitary_channel(clean[1][segment])
        state = _exponential_action(augmented, state, duration)
    return state[:channel_size]


def _refine(evaluate, orders, target, size, max_size):
    previous, current = None, None
    history, stable = [], 0
    reason = "maximum refinement reached"
    for order in orders:
        if size(order) > max_size:
            reason = "refinement resource limit reached"
            break
        current = evaluate(order)
        error = None if previous is None else float(np.linalg.norm(current - previous, "fro"))
        history.append({"order": order, "size": size(order), "error_estimate": error})
        stable = stable + 1 if error is not None and error <= target else 0
        if stable >= 2:
            return current, {"converged": True, "order": order, "error_estimate": error, "history": history}
        previous = current
    if current is None:
        raise ValueError("too many latent directions for the reference solver's resource limit")
    return current, {"converged": False, "order": history[-1]["order"], "error_estimate": history[-1]["error_estimate"], "history": history, "reason": reason}


def solve_exact(dt, hamiltonians, noise_operators, law, *, tolerance=1e-9):
    """Return ``(complex_lab_channel, diagnostics)`` for a stationary noise law.

    ``law['mixing']`` has shape (physical_channels, latent_processes). Physical
    sensitivity belongs in ``noise_operators``; sigma and mixing are applied
    exactly once. Missing sigma/rates default to one per latent; scalars also
    broadcast. Rates may be zero. White noise means sigma**2 * delta(t-s), not
    twice that intensity, and gives -0.5 * sigma**2 * ad(B)**2.

    Static Gaussian quadrature and OU total-degree Hermite truncations require
    two consecutive refinement comparisons against tolerance in absolute
    Frobenius norm. Corrections are retained separately from clean motion;
    weak OU therefore reaches at least degree three even when its first
    comparison passes. This supports extrapolation at tiny sigma without
    cancellation inside the solver. The returned full channel still has ordinary double-precision
    roundoff. Setting ``law['return_noise_correction'] = True`` additionally
    returns the small laboratory-frame difference as the complex ndarray
    ``diagnostics['noise_correction']``. Otherwise diagnostics are JSON-safe.

    OU refinements start at degrees 1, 2, 3, allowing weak many-latent problems
    to converge without allocating higher tiers. A private verification can
    override the strictly increasing positive degrees with
    ``law['hierarchy_degrees']``; the same two-comparison stopping rule applies.

    ``converged=False`` explicitly reports exhausted quadrature/hierarchy limits;
    such a result must not be treated as a validated reference. Finite-state and
    white generators have no model truncation; their error_estimate is zero for
    truncation only, not a claim of zero floating-point error. No projection onto
    trace-preserving or positive maps is applied.
    """
    started = perf_counter()
    durations, controls, loaded, rates, kind, tolerance, latent_count = _prepare(dt, hamiltonians, noise_operators, law, tolerance)
    segment_count = len(dt)
    clean = _clean_evolution(durations, controls)
    clean_channel = _unitary_channel(clean[1][-1])
    active_count = loaded.shape[1]
    strength = _noise_strength(durations, loaded, kind)
    target = tolerance
    diagnostics = {"kind": kind, "tolerance": tolerance, "comparison_tolerance": target, "segments": segment_count, "effective_segments": len(durations), "latent_processes": latent_count, "active_latents": active_count, "noise_strength": strength}
    if active_count == 0:
        correction = np.zeros_like(clean_channel)
        details = {"method": "noiseless_unitary", "converged": True, "error_estimate": 0.0, "history": []}
    elif kind == "static" or (kind == "ou" and np.all(rates == 0)):
        small_noise = strength <= 0.05
        orders = (3, 5, 7, 10, 14, 20, 28, 40, 56, 80, 112, 160, 224, 320, 448) if small_noise else (6, 10, 16, 24, 34, 48, 68, 96, 136, 192, 272, 384, 512)
        correction, details = _refine(lambda order: _static_correction(order, durations, controls, loaded, clean, small_noise), orders, target, lambda order: order ** active_count, 262144)
        details["method"] = "gauss_hermite_static"
        details["quadrature_nodes"] = details["order"] ** active_count
        details["stable_weak_noise"] = small_noise
    elif kind == "ou":
        degrees = tuple(law.get("hierarchy_degrees", (1, 2, 3, 4, 6, 9, 13, 18, 25, 34, 46, 62, 84, 112, 150)))
        if (
            not degrees
            or any(not isinstance(degree, (int, np.integer)) or degree < 1 for degree in degrees)
            or any(second <= first for first, second in zip(degrees, degrees[1:]))
        ):
            raise ValueError("hierarchy_degrees must be strictly increasing positive integers")
        degrees = tuple(int(degree) for degree in degrees)

        def evaluate(degree):
            modes = _hermite_modes(degree, active_count)
            damping, couplings = _mode_operators(modes, rates)
            return _dynamic_correction(durations, controls, loaded, clean, damping, couplings)

        correction, details = _refine(evaluate, degrees, target, lambda degree: comb(degree + active_count, active_count), 4096)
        details["method"] = "sparse_hermite_ou"
        details["hierarchy_degree"] = details["order"]
        details["hierarchy_modes"] = comb(details["order"] + active_count, active_count)
    else:
        if kind == "telegraph":
            if 2 ** active_count > 4096:
                raise ValueError("too many telegraph states for the reference solver")
            modes = list(product((0, 1), repeat=active_count))
            damping, couplings = _mode_operators(modes, rates, telegraph=True)
        else:
            modes, damping, couplings = [(0,)], np.zeros(1), []
        correction = _dynamic_correction(durations, controls, loaded, clean, damping, couplings, white=kind == "white")
        details = {"method": "finite_state_telegraph" if kind == "telegraph" else "exact_white_liouvillian", "converged": True, "error_estimate": 0.0, "error_estimate_kind": "model_truncation_only", "states": len(modes), "history": []}
    diagnostics.update(details)
    channel = clean_channel + correction
    dimension = controls.shape[-1]
    identity_vector = np.eye(dimension).reshape(-1, order="F")
    choi = channel.reshape((dimension,) * 4, order="F").transpose(0, 2, 1, 3).reshape(channel.shape, order="F")
    diagnostics.update({
        "trace_preservation_error": float(np.linalg.norm(identity_vector @ channel - identity_vector)),
        "unitality_error": float(np.linalg.norm(channel @ identity_vector - identity_vector)),
        "hermiticity_error": float(np.linalg.norm(choi - choi.conj().T, "fro")),
        "choi_min_eigenvalue": float(np.linalg.eigvalsh((choi + choi.conj().T) * 0.5)[0]),
        "elapsed_seconds": perf_counter() - started,
    })
    if law.get("return_noise_correction", False):
        diagnostics["noise_correction"] = correction
    return np.asarray(channel, dtype=complex), diagnostics
