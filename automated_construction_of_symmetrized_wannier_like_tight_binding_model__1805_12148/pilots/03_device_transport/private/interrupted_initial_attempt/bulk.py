"""Bulk Fourier interpolation adapted from the historical Model.hamilton method."""

import numpy as np


def hamiltonian(case, reduced_k):
    phases = np.exp(2j * np.pi * (case["h_R"] @ np.asarray(reduced_k)))
    return np.einsum("r,rij->ij", phases, case["h_matrices"])


def eigenvalues(case, reduced_k):
    return np.linalg.eigvalsh(hamiltonian(case, reduced_k))
