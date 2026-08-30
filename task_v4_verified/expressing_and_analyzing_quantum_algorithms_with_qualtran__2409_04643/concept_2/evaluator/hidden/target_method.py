"""Numerically faithful extraction from Qualtran 096a2d009059faee0cfae462c3d59cb055300eb9."""

import numpy as np


def rotation_matrix(theta, phi, lambd):
    return np.exp(1j * 0) * np.array(
        [
            [
                np.exp(1j * (lambd + phi)) * np.cos(theta),
                np.exp(1j * phi) * np.sin(theta),
            ],
            [np.exp(1j * lambd) * np.sin(theta), -np.cos(theta)],
        ]
    )


def fft_complementary_polynomial(polynomial, tolerance=1e-4, num_modes=500):
    polynomial = np.array(polynomial)

    def scale(values):
        return (1 - tolerance / 4) * values

    def pad_poly(values):
        return np.pad(scale(values), (0, num_modes - 1))

    def evaluate(values):
        return np.fft.ifft(pad_poly(values), norm="forward")

    def get_log(values):
        return np.log(1 - (np.abs(evaluate(values))) ** 2)

    def fourier_multiplier(the_log):
        modes = np.fft.fft(the_log, norm="forward")
        modes[0] *= 1 / 2
        modes[num_modes // 2 + 1 :] = 0
        return modes

    def get_modes(values):
        return np.fft.ifft(fourier_multiplier(get_log(values)), norm="forward")

    return np.fft.fft(np.exp(get_modes(polynomial)), norm="forward")[: polynomial.shape[0]]


def qsp_phase_factors(polynomial, complement):
    if len(polynomial) != len(complement):
        raise ValueError("Polynomials P and Q must have the same degree.")
    state = np.array([polynomial, complement])
    length = state.shape[1]
    theta = np.zeros(length)
    phi = np.zeros(length)
    lambd = 0

    def safe_angle(value):
        return 0 if np.isclose(value, 0, atol=1e-10) else np.angle(value)

    for degree in reversed(range(length)):
        assert state.shape == (2, degree + 1)
        leading, other = state[:, degree]
        theta[degree] = np.arctan2(np.abs(other), np.abs(leading))
        phi[degree] = (
            0
            if np.isclose(np.abs(other), 0, atol=1e-10)
            else safe_angle(leading * np.conj(other))
        )
        if degree == 0:
            lambd = safe_angle(other)
        else:
            state = rotation_matrix(theta[degree], phi[degree], 0).conj().T @ state
            state = np.array([state[0][1 : degree + 1], state[1][0:degree]])
    return theta, phi, lambd


def phase_guard_margin(polynomial, complement, theta, phi):
    state = np.array([polynomial, complement])
    minimum = float("inf")
    for degree in reversed(range(len(polynomial))):
        leading, other = state[:, degree]
        minimum = min(minimum, float(abs(other)), float(abs(leading * np.conj(other))))
        if degree:
            state = rotation_matrix(theta[degree], phi[degree], 0).conj().T @ state
            state = np.array([state[0][1 : degree + 1], state[1][0:degree]])
    return minimum
