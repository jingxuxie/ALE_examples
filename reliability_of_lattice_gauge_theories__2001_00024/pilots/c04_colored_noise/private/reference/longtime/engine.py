import math

import numpy as np
from scipy import sparse
from scipy.optimize import least_squares
from scipy.sparse.linalg import expm_multiply


def spectrum(bath, omega):
    omega = np.asarray(omega, dtype=float)
    if bath["beta"] == 0:
        return np.full_like(omega, bath["amplitude"])
    return bath["amplitude"] * (omega**2 + bath["cutoff"]**2) ** (
        -bath["beta"] / 2
    ) + bath["floor"]


def calibration_rates(bath, rows):
    return np.array([
        (1 + row["mode"] * bath["eta"])
        * np.dot(row["weight"], spectrum(bath, row["omega"]))
        for row in rows
    ])


def fit_bath(rows):
    frequencies = np.asarray([row["omega"] for row in rows])
    weights = np.asarray([row["weight"] for row in rows])
    modes = np.asarray([row["mode"] for row in rows])
    values = np.asarray([row["value"] for row in rows])
    sigmas = np.asarray([row["sigma"] for row in rows])
    median = np.clip(np.median(values[modes == 0]), 1.1e-5, 0.119)
    candidates = []
    for beta in (0, 1, 2):
        def unpack(parameters):
            if beta == 0:
                return dict(beta=0, amplitude=float(np.exp(parameters[0])),
                            cutoff=1.0, floor=0.0, eta=float(parameters[1]))
            return dict(beta=beta, amplitude=float(np.exp(parameters[0])),
                        cutoff=float(np.exp(parameters[1])),
                        floor=float(0.02 * parameters[2]), eta=float(parameters[3]))

        def residual(parameters):
            bath = unpack(parameters)
            predicted = np.sum(weights * spectrum(bath, frequencies), axis=1)
            return (predicted * (1 + modes * bath["eta"]) - values) / sigmas

        if beta == 0:
            bounds = ([math.log(1e-5), 0], [math.log(0.12), 1])
            starts = [[math.log(median), 0.4]]
        else:
            bounds = ([math.log(1e-5), math.log(0.12), 0, 0],
                      [math.log(0.12), math.log(1.2), 1, 1])
            starts = [[math.log(median), math.log(cutoff), 0.01, 0.4]
                      for cutoff in (0.18, 0.5, 1.05)]
        best = None
        for start in starts:
            fitted = least_squares(residual, start, bounds=bounds, xtol=2e-12,
                                   ftol=2e-12, gtol=2e-12, max_nfev=1500)
            objective = float(np.dot(fitted.fun, fitted.fun))
            if best is None or objective < best[0]:
                best = objective, unpack(fitted.x)
        candidates.append((best[0] + (2 if beta == 0 else 4) * math.log(len(rows)),
                           best[1]))
    minimum = min(item[0] for item in candidates)
    return next(bath for objective, bath in candidates if objective <= minimum + 1e-8)


def state_vector(specification, dimension=64):
    vector = np.zeros(dimension, dtype=complex)
    vector[specification["indices"]] = (
        np.asarray(specification["real"]) + 1j * np.asarray(specification["imag"])
    )
    return vector


def build_model(case):
    model = case["model"]
    length = 3
    dimension = 64
    identity = np.eye(dimension)
    indices = np.arange(dimension)
    flips, zvalues, annihilators = [], [], []
    for qubit in range(2 * length):
        mask = 1 << (2 * length - qubit - 1)
        flips.append(identity[:, indices ^ mask])
        zvalues.append(1 - 2 * ((indices & mask) != 0))
        annihilator = np.zeros((dimension, dimension))
        sources = indices[(indices & mask) != 0]
        annihilator[sources ^ mask, sources] = 1
        annihilators.append(annihilator)
    occupancies = [np.diag((1 - zvalues[2 * site]) / 2) for site in range(length)]
    hzero = np.zeros((dimension, dimension), dtype=complex)
    herror = np.zeros_like(hzero)
    charges = []
    first_index = case["initial"]["indices"][0]
    for site in range(length):
        successor = (site + 1) % length
        hopping = annihilators[2 * site].T @ annihilators[2 * successor]
        coupled = hopping @ flips[2 * site + 1]
        coefficient = model["hopping"][site] * np.exp(1j * model["phase"][site])
        hzero += coefficient * coupled + coefficient.conjugate() * coupled.T
        hzero += -model["electric"][site] * np.diag(zvalues[2 * site + 1])
        hzero += model["mass"][site] * occupancies[site]
        herror += model["error_hop"][site] * (hopping + hopping.T)
        herror += model["error_link"][site] * flips[2 * site + 1]
        signs = zvalues[2 * site] * zvalues[2 * ((site - 1) % length) + 1]
        signs = signs * zvalues[2 * site + 1]
        charges.append(np.diag((1 - signs[first_index] * signs) / 2))
    return dict(hzero=hzero, herror=herror, charges=charges,
                gauge=sum(charges) / length, occupancies=occupancies,
                electric=np.diag(sum(zvalues[1::2]) / length), flips=flips,
                initial=state_vector(case["initial"]))


def hamiltonian(case, operators, action):
    strength = action["strength"]
    coefficients = action["coefficients"]
    model = case["model"]
    result = operators["hzero"] + model["lambda"] * operators["herror"]
    for site, coefficient in enumerate(coefficients):
        result = result + strength * coefficient * operators["charges"][site]
        result = result + model["kappa"] * strength**2 * model["crosstalk"][site] * (
            coefficient**2 * operators["occupancies"][site]
        )
    return result


def channels(case, operators, eta):
    result = []
    for species, offset in (("matter", 0), ("link", 1)):
        collective = np.zeros((64, 64), dtype=complex)
        for site in range(3):
            amplitude = math.sqrt(case["model"][species + "_weight"][site])
            operator = amplitude * operators["flips"][2 * site + offset]
            result.append(math.sqrt(1 - eta) * operator)
            collective += case["model"][species + "_sign"][site] * operator
        result.append(math.sqrt(eta) * collective)
    return np.asarray(result)


def clustered(values, tolerance):
    values = np.asarray(values)
    order = np.argsort(values, kind="mergesort")
    groups, means = [], []
    start = 0
    while start < len(order):
        stop = int(np.searchsorted(values[order], values[order[start]] + tolerance,
                                   side="right"))
        group = order[start:stop]
        groups.append(group)
        means.append(float(np.mean(values[group])))
        start = stop
    return groups, np.asarray(means)


def secular_generator(hamiltonian_matrix, channel_matrices, bath, eigensystem=None,
                      split_transitions=False):
    dimension = len(hamiltonian_matrix)
    energies, vectors = (np.linalg.eigh(hamiltonian_matrix) if eigensystem is None
                         else eigensystem)
    energy_groups, energy_means = clustered(energies, 1e-9)
    clustered_energies = energies.copy()
    for group, mean in zip(energy_groups, energy_means):
        clustered_energies[group] = mean
    gaps = (clustered_energies[None, :] - clustered_energies[:, None]).ravel()
    gap_groups, frequencies = clustered(gaps, 1e-8)
    transformed = np.asarray([vectors.conj().T @ channel @ vectors
                              for channel in channel_matrices])
    active = np.sum(np.abs(transformed)**2, axis=0).ravel() > 1e-26
    gain_rows, gain_columns, gain_values = [], [], []
    losses = np.zeros((3, dimension, dimension), dtype=complex)
    degeneracy_count = 0
    for group, frequency in zip(gap_groups, frequencies):
        group = group[active[group]]
        if not len(group):
            continue
        rows, columns = group // dimension, group % dimension
        amplitudes = transformed[:, rows, columns]
        gram = spectrum(bath, frequency) * (amplitudes.T @ amplitudes.conj())
        if split_transitions:
            gram = np.diag(np.diag(gram))
        degeneracy_count += int(len(group) > 1)
        gain_rows.append((rows[:, None] + dimension * rows[None, :]).ravel())
        gain_columns.append((columns[:, None] + dimension * columns[None, :]).ravel())
        gain_values.append(gram.ravel())
        left, right = np.nonzero(rows[:, None] == rows[None, :])
        band = 0 if abs(frequency) <= 1e-8 else (1 if abs(frequency) < 2 else 2)
        np.add.at(losses[band], (columns[left], columns[right]), gram[right, left])
    if gain_values:
        gain = sparse.coo_matrix((np.concatenate(gain_values),
                                  (np.concatenate(gain_rows), np.concatenate(gain_columns))),
                                 shape=(dimension**2, dimension**2)).tocsr()
    else:
        gain = sparse.csr_matrix((dimension**2, dimension**2), dtype=complex)
    loss = sparse.csr_matrix(np.sum(losses, axis=0))
    identity = sparse.eye(dimension, format="csr")
    dissipator = gain - 0.5 * (sparse.kron(identity, loss) + sparse.kron(loss.T, identity))
    dissipator = dissipator.tocsr()
    dissipator.eliminate_zeros()
    coherent = -1j * (energies[:, None] - energies[None, :]).ravel(order="F")
    generator = dissipator + sparse.diags(coherent)
    return dict(vectors=vectors, dissipator=dissipator, generator=generator.tocsr(),
                losses=losses, degeneracy_count=degeneracy_count,
                energy_groups=energy_groups, energies=energies)


def raw_generator(hamiltonian_matrix, channel_matrices, rate):
    dimension = len(hamiltonian_matrix)
    identity = sparse.eye(dimension, format="csr")
    dissipator = sparse.csr_matrix((dimension**2, dimension**2), dtype=complex)
    loss = np.zeros((dimension, dimension), dtype=complex)
    for channel in channel_matrices:
        operator = sparse.csr_matrix(channel)
        product = channel.conj().T @ channel
        dissipator += rate * (sparse.kron(operator.conj(), operator)
                              - 0.5 * sparse.kron(identity, sparse.csr_matrix(product))
                              - 0.5 * sparse.kron(sparse.csr_matrix(product.T), identity))
        loss += rate * product
    hamiltonian_sparse = sparse.csr_matrix(hamiltonian_matrix)
    generator = dissipator - 1j * (sparse.kron(identity, hamiltonian_sparse)
                                   - sparse.kron(hamiltonian_sparse.T, identity))
    return dict(vectors=np.eye(dimension), dissipator=dissipator.tocsr(),
                generator=generator.tocsr(), losses=np.asarray([0 * loss, loss, 0 * loss]))


def audit_response(compiled, states):
    result = []
    vectors = compiled["vectors"]
    dimension = len(vectors)
    for specification in states:
        vector = vectors.conj().T @ state_vector(specification, dimension)
        density = np.outer(vector, vector.conj())
        derivative = (compiled["dissipator"] @ density.ravel(order="F")).reshape(
            (dimension, dimension), order="F"
        )
        derivative = vectors @ derivative @ vectors.conj().T
        activity = np.einsum("bij,ji->b", compiled["losses"], density).real
        result.append(dict(real=derivative.real.tolist(), imag=derivative.imag.tolist(),
                           activity=activity.tolist()))
    return result


def feasible_actions(case):
    return [action for action in case["actions"] if action_cost(action) <= case["budget"] + 1e-10]


def action_cost(action):
    return action["strength"]**2 * sum(value**2 for value in action["coefficients"])


def propagate(case, operators, compiled, return_states=False):
    vectors = compiled["vectors"]
    dimension = len(vectors)
    initial = vectors.conj().T @ operators["initial"]
    initial_density = np.outer(initial, initial.conj()).ravel(order="F")
    times = np.asarray(case["times"])
    evolved = expm_multiply(compiled["generator"], initial_density, start=0,
                            stop=times[-1], num=len(times), endpoint=True)
    densities = np.asarray([row.reshape((dimension, dimension), order="F") for row in evolved])
    ideal_energies, ideal_vectors = np.linalg.eigh(operators["hzero"])
    ideal_coefficients = ideal_vectors.conj().T @ operators["initial"]
    ideal_states = (ideal_vectors @ (np.exp(-1j * np.outer(ideal_energies, times))
                                    * ideal_coefficients[:, None])).T
    ideal_states = (vectors.conj().T @ ideal_states.T).T

    def expectation(operator):
        rotated = vectors.conj().T @ operator @ vectors
        return np.einsum("ij,tji->t", rotated, densities).real

    fidelity = np.einsum("ti,tij,tj->t", ideal_states.conj(), densities, ideal_states).real
    result = dict(gauge=expectation(operators["gauge"]).tolist(), fidelity=fidelity.tolist(),
                  electric=expectation(operators["electric"]).tolist(),
                  density=np.asarray([expectation(operator) for operator in
                                      operators["occupancies"]]).T.tolist())
    return (result, densities) if return_states else result


def risk(case, prediction):
    integrand = 0.45 * np.asarray(prediction["gauge"]) + 0.55 * (
        1 - np.asarray(prediction["fidelity"])
    )
    return float(np.trapz(integrand, case["times"]) / case["times"][-1])


def solve_model(case, weak=False, split_transitions=False, force_eta=None):
    operators = build_model(case)
    if weak:
        amplitude = np.median([row["value"] for row in case["calibration"] if row["mode"] == 0])
        bath = dict(beta=0, amplitude=float(np.clip(amplitude, 1e-5, 0.12)),
                    cutoff=1.0, floor=0.0, eta=0.0)
    else:
        bath = fit_bath(case["calibration"])

    def compile_model(action, parameters):
        hsystem = hamiltonian(case, operators, action)
        if weak:
            return raw_generator(hsystem, channels(case, operators, 0),
                                 float(spectrum(parameters, 1.0)))
        eta = parameters["eta"] if force_eta is None else force_eta
        return secular_generator(hsystem, channels(case, operators, eta), parameters,
                                 split_transitions=split_transitions)

    audit_model = compile_model(case["audit"]["action"], case["audit"]["bath"])
    audit = audit_response(audit_model, case["audit"]["states"])
    predictions = {}
    actions = feasible_actions(case)
    for action in actions:
        compiled = compile_model(action, bath)
        predictions[action["id"]] = propagate(case, operators, compiled)
    selected = (max(actions, key=action_cost)["id"] if weak else
                min(actions, key=lambda action: risk(case, predictions[action["id"]]))["id"])
    return dict(bath=bath, audit=audit, predictions=predictions, selected_action=selected)


def solve(case: dict) -> dict:
    return solve_model(case)


def weak_solve(case: dict) -> dict:
    return solve_model(case, weak=True)
