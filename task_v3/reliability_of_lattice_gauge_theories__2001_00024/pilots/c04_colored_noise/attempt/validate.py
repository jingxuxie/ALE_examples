"""Independent local numerical checks; uses only the public example case."""

import copy
import json
import pathlib
import time

import solver
import numpy as np
from scipy.linalg import eigh
from scipy.sparse.linalg import expm_multiply


def tensor_operator(operator, position):
    product = np.array([[1.0]])
    for qubit in range(6):
        product = np.kron(product, operator if qubit == position else np.eye(2))
    return product


def check_hamiltonian(case):
    model = case["model"]
    ideal, error, violations, density, observables, masks = solver.build_model(model, case["initial"])
    annihilation = [tensor_operator(np.array([[0, 1], [0, 0]]), 2 * site) for site in range(3)]
    link_x = [tensor_operator(np.array([[0, 1], [1, 0]]), 2 * site + 1) for site in range(3)]
    link_z = [tensor_operator(np.diag([1, -1]), 2 * site + 1) for site in range(3)]
    expected_ideal = np.zeros((64, 64), dtype=complex)
    expected_error = np.zeros((64, 64), dtype=complex)
    for site in range(3):
        hopping = annihilation[site].T @ annihilation[(site + 1) % 3]
        amplitude = model["hopping"][site] * np.exp(1j * model["phase"][site])
        expected_ideal += amplitude * hopping @ link_x[site] + amplitude.conjugate() * hopping.T @ link_x[site]
        expected_ideal += -model["electric"][site] * link_z[site] + model["mass"][site] * annihilation[site].T @ annihilation[site]
        expected_error += model["error_hop"][site] * (hopping + hopping.T) + model["error_link"][site] * link_x[site]
    np.testing.assert_allclose(ideal, expected_ideal, atol=1e-14)
    np.testing.assert_allclose(error, expected_error, atol=1e-14)
    for violation in violations:
        np.testing.assert_allclose(ideal * violation[None, :] - violation[:, None] * ideal, 0, atol=1e-14)
    np.testing.assert_allclose(observables[0] @ np.abs(solver.state_vector(case["initial"])) ** 2, 0, atol=1e-14)
    print("Tensor Hamiltonian and Gauss-law checks passed")


def check_calibration(case):
    probe_frequencies = np.r_[0.0, np.geomspace(0.02, 30, 33)]
    baths = [
        {"beta": 0, "amplitude": 0.034, "cutoff": 1.0, "floor": 0.0, "eta": 0.0},
        {"beta": 0, "amplitude": 0.12, "cutoff": 1.0, "floor": 0.0, "eta": 1.0},
        {"beta": 1, "amplitude": 0.024, "cutoff": 0.34, "floor": 0.001, "eta": 0.63},
        {"beta": 2, "amplitude": 0.016, "cutoff": 0.27, "floor": 0.0004, "eta": 1.0},
        {"beta": 2, "amplitude": 0.004, "cutoff": 0.12, "floor": 0.02, "eta": 0.0},
    ]
    for bath in baths:
        rows = copy.deepcopy(case["calibration"])
        for row in rows:
            rate = float(np.dot(row["weight"], solver.spectrum(bath, row["omega"])))
            row["value"] = (1 + row["mode"] * bath["eta"]) * rate
            row["sigma"] = max(1e-6, rate * 0.01)
        fit = solver.fit_bath(rows)
        assert fit["beta"] == bath["beta"], (bath, fit)
        relative = np.max(np.abs(solver.spectrum(fit, probe_frequencies) / solver.spectrum(bath, probe_frequencies) - 1))
        assert relative < 2e-6, (bath, fit, relative)
        assert abs(fit["eta"] - bath["eta"]) < 2e-6, (bath, fit)
        print("Noiseless fit:", bath["beta"], bath["eta"], "relative error", relative)


def explicit_audit(system, bath, specification):
    psi = system.unitary.conj().T @ solver.state_vector(specification)
    response = np.zeros((64, 64), dtype=complex)
    activity = np.zeros(3)
    channels = []
    for species in range(2):
        operators = system.local[species::2] * np.sqrt(system.weights[species])[:, None, None]
        channels.extend(np.sqrt(1 - bath["eta"]) * operators)
        channels.append(np.sqrt(bath["eta"]) * np.einsum("j,jab->ab", system.signs[species], operators))
    for frequency, indices in system.groups:
        rate = float(solver.spectrum(bath, frequency))
        bin_index = 0 if abs(frequency) <= 1e-8 else (1 if abs(frequency) < 2 else 2)
        for channel in channels:
            jump = np.zeros((64, 64), dtype=complex)
            jump.ravel()[indices] = channel.ravel()[indices]
            after_jump = jump @ psi
            after_loss = jump.conj().T @ after_jump
            response += rate * (np.outer(after_jump, after_jump.conj())
                                - 0.5 * np.outer(after_loss, psi.conj())
                                - 0.5 * np.outer(psi, after_loss.conj()))
            activity[bin_index] += rate * np.vdot(after_jump, after_jump).real
    return system.unitary @ response @ system.unitary.conj().T, activity


def check_dissipator(case, degenerate=False):
    model = copy.deepcopy(case["model"])
    action = case["audit"]["action"]
    if degenerate:
        for name in ("phase", "mass", "crosstalk"):
            model[name] = [0.0, 0.0, 0.0]
        model["hopping"] = [1.0, 1.0, 1.0]
        model["electric"] = [0.4, 0.4, 0.4]
        model["lambda"] = 0.0
        model["kappa"] = 0.0
        model["matter_sign"] = [1, -1, 1]
        model["link_sign"] = [-1, 1, 1]
        action = {"strength": 1.4, "coefficients": [1, -1, 1]}
    ideal, error, violations, density, observables, masks = solver.build_model(model, case["initial"])
    coefficients = np.asarray(action["coefficients"])
    strength = action["strength"]
    detuning = model["kappa"] * strength**2 * (np.asarray(model["crosstalk"]) * coefficients**2) @ density
    hamiltonian = ideal + model["lambda"] * error + np.diag(strength * coefficients @ violations + detuning)
    system = solver.SecularSystem(hamiltonian, masks, model)
    bath = dict(case["audit"]["bath"])
    bath["eta"] = 0.71 if degenerate else 1.0
    bath["beta"] = 2 if degenerate else 1
    dissipator, activities = system.dissipator(bath)
    diagonal_identity = np.eye(64).ravel()
    assert np.linalg.norm(dissipator @ diagonal_identity) < 1e-11
    assert np.linalg.norm(dissipator.T @ diagonal_identity) < 1e-11
    difference = dissipator - dissipator.getH()
    assert np.linalg.norm(difference.data) < 1e-10
    actual = system.audit(bath, case["audit"]["states"])
    for specification, output in zip(case["audit"]["states"], actual):
        expected, activity = explicit_audit(system, bath, specification)
        response = np.asarray(output["real"]) + 1j * np.asarray(output["imag"])
        relative_error = np.linalg.norm(response - expected) / np.linalg.norm(expected)
        assert relative_error < 1e-10, relative_error
        np.testing.assert_allclose(output["activity"], activity, atol=1e-12, rtol=1e-10)
        print("Explicit audit:", "degenerate" if degenerate else "generic", "relative error", relative_error)
    state = system.unitary.conj().T @ solver.state_vector(case["initial"])
    generator = dissipator + solver.sparse.diags(-1j * (system.energies[:, None] - system.energies[None, :]).ravel())
    trajectory = expm_multiply(generator, np.outer(state, state.conj()).ravel(), start=0, stop=5, num=5).reshape(5, 64, 64)
    for rho in trajectory:
        assert abs(np.trace(rho) - 1) < 1e-10
        assert np.linalg.norm(rho - rho.conj().T) < 1e-10
        assert np.linalg.eigvalsh(rho).min() >= -1e-10
    energies, unitary = eigh(ideal)
    times = np.array([0, 0.4, 0.8])
    initial = solver.state_vector(case["initial"])
    ideal_states = (np.exp(-1j * times[:, None] * energies) * (unitary.conj().T @ initial)) @ unitary.T
    noiseless = {"beta": 0, "amplitude": 0.0, "eta": 0.0, "cutoff": 1.0, "floor": 0.0}
    prediction = system.predict(noiseless, initial, ideal_states, observables, times)
    states = (np.exp(-1j * times[:, None] * system.energies) * state) @ system.unitary.T
    expected_observables = np.abs(states)**2 @ observables.T
    expected_fidelity = np.abs(np.einsum("ti,ti->t", ideal_states.conj(), states))**2
    np.testing.assert_allclose(prediction["gauge"], expected_observables[:, 0], atol=1e-12)
    np.testing.assert_allclose(prediction["electric"], expected_observables[:, 1], atol=1e-12)
    np.testing.assert_allclose(prediction["density"], expected_observables[:, 2:], atol=1e-12)
    np.testing.assert_allclose(prediction["fidelity"], expected_fidelity, atol=1e-12)
    print("Trace, unitality, positivity, and unitary-limit checks passed; nnz", dissipator.nnz)


def check_zero_frequency(case):
    model = case["model"]
    masks = 1 << np.arange(5, -1, -1)
    system = solver.SecularSystem(np.zeros((64, 64)), masks, model)
    assert len(system.groups) == 1
    bath = {"beta": 2, "amplitude": 0.019, "cutoff": 0.23, "floor": 0.0007, "eta": 0.82}
    specification = case["audit"]["states"][1]
    psi = solver.state_vector(specification)
    rho = np.outer(psi, psi.conj())
    expected = np.zeros_like(rho)
    expected_activity = 0.0
    for species_index, species in enumerate(("matter", "link")):
        operators = [np.sqrt(model[species + "_weight"][site]) * tensor_operator(np.array([[0, 1], [1, 0]]), 2 * site + species_index)
                     for site in range(3)]
        channels = [np.sqrt(1 - bath["eta"]) * operator for operator in operators]
        channels.append(np.sqrt(bath["eta"]) * sum(model[species + "_sign"][site] * operators[site] for site in range(3)))
        for channel in channels:
            rate = float(solver.spectrum(bath, 0))
            squared = channel.conj().T @ channel
            expected += rate * (channel @ rho @ channel.conj().T - 0.5 * (squared @ rho + rho @ squared))
            expected_activity += rate * np.vdot(channel @ psi, channel @ psi).real
    actual = system.audit(bath, [specification])[0]
    response = np.asarray(actual["real"]) + 1j * np.asarray(actual["imag"])
    np.testing.assert_allclose(response, expected, atol=1e-12)
    np.testing.assert_allclose(actual["activity"], [expected_activity, 0, 0], atol=1e-12)
    clusters = solver.cluster_sorted(np.array([0.0, 0.9e-9, 1.8e-9, 2.7e-9]), 1e-9)
    assert [len(indices) for mean, indices in clusters] == [2, 2]
    print("Fully degenerate raw-channel and first-value clustering checks passed")


def main():
    example_path = pathlib.Path(__file__).resolve().parent.parent / "participant" / "input" / "example_case.json"
    with example_path.open() as source:
        case = json.load(source)
    start = time.perf_counter()
    check_hamiltonian(case)
    check_calibration(case)
    check_dissipator(case)
    check_dissipator(case, degenerate=True)
    check_zero_frequency(case)
    result = solver.solve(case)
    json.dumps(result, allow_nan=False)
    feasible = [action["id"] for action in case["actions"]
                if action["strength"]**2 * np.dot(action["coefficients"], action["coefficients"]) <= case["budget"] + 1e-10]
    assert set(result["predictions"]) == set(feasible)
    assert result["selected_action"] in feasible
    print("All local checks passed in %.3f seconds" % (time.perf_counter() - start))


if __name__ == "__main__":
    main()
