import numpy as np
from physics import LOWER, UPPER, STATES, STATE_INDEX, OCCUPATIONS, SPINS, EXCHANGE, ISING, READOUT_DIFFERENCES, hamiltonian


def predict_with_jac(normalized, experiments):
    ranges = UPPER - LOWER
    parameters = LOWER + ranges * normalized
    energies, vectors = np.linalg.eigh(hamiltonian(parameters))
    operators = np.zeros((14, len(STATES), len(STATES)))
    diagonal = np.diag_indices(len(STATES))
    for site in range(6):
        operators[site] = EXCHANGE[site]
        operators[site][diagonal] += parameters[11] * ISING[site]
    for site in range(5):
        operators[6 + site][diagonal] = SPINS[:, site] - SPINS[:, 5]
    couplings = np.concatenate((parameters[:6], parameters[12 + np.arange(6) % 2]))
    operators[11][diagonal] = couplings @ ISING
    for parity in range(2):
        operators[12 + parity] = EXCHANGE[6 + parity::2].sum(axis=0)
        operators[12 + parity][diagonal] += parameters[11] * ISING[6 + parity::2].sum(axis=0)
    operators *= ranges[:14, None, None]
    spectral_operators = np.einsum("ia,pij,jb->pab", vectors, operators, vectors, optimize=True)
    rates = parameters[14:20]
    detector = np.prod(np.where(READOUT_DIFFERENCES, rates, 1 - rates), axis=2)
    detector_derivatives = np.moveaxis(detector[:, :, None] * np.where(READOUT_DIFFERENCES, 1.0 / rates, -1.0 / (1 - rates)) * ranges[14:20], -1, 0)
    gaps = energies[:, None] - energies[None, :]
    gap_nonzero = np.abs(gaps) > 1e-10
    predictions = []
    jacobians = []
    for experiment in experiments:
        duration = float(experiment["time"]) / 2
        phase = np.exp(-1j * energies * duration)
        divided = np.empty(gaps.shape, dtype=complex)
        np.divide(phase[:, None] - phase[None, :], gaps, out=divided, where=gap_nonzero)
        divided[~gap_nonzero] = (-1j * duration * np.exp(-0.5j * duration * (energies[:, None] + energies[None, :])))[~gap_nonzero]
        propagator = (vectors * phase) @ vectors.T
        derivative = np.einsum("ia,pab,jb->pij", vectors, spectral_operators * divided, vectors, optimize=True)
        preparation = STATE_INDEX[int(experiment["preparation"])]
        first = propagator[:, preparation]
        kick = np.exp(-1j * (OCCUPATIONS @ experiment["phases"]))
        final = propagator @ (kick * first)
        differentiated = np.einsum("pij,j->pi", derivative, kick * first) + np.einsum("ij,pj->pi", propagator, kick * derivative[:, :, preparation])
        true = np.abs(final) ** 2
        probability = detector @ true
        jacobian = np.empty((64, 20))
        jacobian[:, :14] = detector @ (2 * np.real(final.conj()[None, :] * differentiated)).T
        jacobian[:, 14:] = np.einsum("pij,j->ip", detector_derivatives, true)
        predictions.append(probability)
        jacobians.append(jacobian)
    return np.asarray(predictions), np.asarray(jacobians)
