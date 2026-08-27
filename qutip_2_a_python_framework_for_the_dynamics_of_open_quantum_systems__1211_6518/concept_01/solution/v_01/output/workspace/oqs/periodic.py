import numpy as np
from scipy.integrate import solve_ivp
from scipy.linalg import schur

from .baths import spectrum
from .io import hamiltonian
from .spectral import dissipator, evolve_generator


def floquet_states(case, options):
    dimension = len(case['H0'])
    period = case['period']
    frequency = 2 * np.pi / period
    samples = options['samples']
    harmonics = min(options['harmonics'], samples // 2 - 1)

    def derivative(time, vector):
        return (-1j * hamiltonian(case, time) @ vector.reshape(dimension, dimension)).ravel()

    evolution = solve_ivp(derivative, (0, period), np.eye(dimension, dtype=complex).ravel(),
                          method='DOP853', dense_output=True, rtol=min(options['rtol'], 1e-11),
                          atol=min(options['atol'], 1e-13), max_step=period / max(128, samples))
    if not evolution.success:
        raise RuntimeError(evolution.message)
    triangular, basis = schur(evolution.y[:, -1].reshape(dimension, dimension), output='complex')
    energies = -np.angle(np.diag(triangular)) / period
    grid = np.arange(samples) * period / samples
    modes = (evolution.sol(grid).T.reshape(-1, dimension, dimension) @ basis) * np.exp(1j * grid[:, None, None] * energies[None, None, :])
    generator = np.zeros((dimension ** 2, dimension ** 2), dtype=complex)
    for coupling, bath in zip(case['a_ops'], case['baths']):
        transformed = modes.conj().transpose(0, 2, 1) @ coupling @ modes
        coefficients = np.fft.fft(transformed, axis=0) / samples
        components = []
        for harmonic in range(-harmonics, harmonics + 1):
            for target in range(dimension):
                for source in range(dimension):
                    amplitude = coefficients[harmonic % samples, target, source]
                    if abs(amplitude) > 2e-13:
                        release = energies[source] - energies[target] - harmonic * frequency
                        components.append((release, target, source, amplitude))
        components.sort(key=lambda item: item[0])
        groups = []
        for release, target, source, amplitude in components:
            if not groups or abs(release - groups[-1][0]) >= 1e-7:
                groups.append((release, np.zeros((dimension, dimension), dtype=complex)))
            groups[-1][1][target, source] += amplitude
        for release, operator in groups:
            rate = float(spectrum(bath, release))
            if rate > 0:
                generator += rate * dissipator(operator)

    def frame(time):
        residue = time % period
        propagator = evolution.sol(residue).reshape(dimension, dimension)
        return (propagator @ basis) * np.exp(-1j * energies * (time - residue))[None, :]

    initial_frame = frame(case['times'][0])
    initial = initial_frame.conj().T @ case['rho0'] @ initial_frame
    states = evolve_generator(generator, initial, case['times'] - case['times'][0])
    return np.asarray([frame(time) @ density @ frame(time).conj().T for time, density in zip(case['times'], states)])
