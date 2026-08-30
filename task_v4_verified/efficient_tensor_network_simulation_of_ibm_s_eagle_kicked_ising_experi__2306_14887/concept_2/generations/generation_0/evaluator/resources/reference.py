"""Independent bit-pair statevector oracle, with independent ZZ measurement."""

import numpy as np


def exact_state(angles, n_sites=12):
    amplitudes = np.zeros(2 ** n_sites, dtype=complex)
    amplitudes[0] = 1
    indices = np.arange(len(amplitudes))
    for angle in angles:
        for site in range(n_sites):
            zero = indices[(indices & (1 << site)) == 0]
            one = zero | (1 << site)
            first, second = amplitudes[zero].copy(), amplitudes[one].copy()
            amplitudes[zero] = np.cos(angle / 2) * first - 1j * np.sin(angle / 2) * second
            amplitudes[one] = np.cos(angle / 2) * second - 1j * np.sin(angle / 2) * first
        for site in range(n_sites):
            opposite = ((indices >> site) ^ (indices >> ((site + 1) % n_sites))) & 1
            amplitudes *= np.where(opposite, np.exp(-1j * np.pi / 4), np.exp(1j * np.pi / 4))
    return amplitudes


def zz1(state, n_sites=12):
    result = 0.0
    mask = (1 << n_sites) - 1
    for index, amplitude in enumerate(state):
        rotated = ((index << 1) & mask) | (index >> (n_sites - 1))
        correlation = 1 - 2 * (index ^ rotated).bit_count() / n_sites
        result += correlation * abs(amplitude) ** 2
    return float(result / np.vdot(state, state).real)
