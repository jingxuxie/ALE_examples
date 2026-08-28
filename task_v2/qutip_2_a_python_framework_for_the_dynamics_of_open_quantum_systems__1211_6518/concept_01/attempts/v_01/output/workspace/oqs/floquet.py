import numpy as np
import warnings
from scipy.linalg import polar, schur

from .baths import spectrum
from .integration import integrate
from .io import hamiltonian
from .io import scalar
from .operators import dissipator, evolve_generator, frequency_sectors


def floquet_modes(case, options):
    dimension = len(case['H0'])
    period = case['period']
    integration_options = dict(options, rtol=options.get('unitary_rtol', 2e-12),
                               atol=options.get('unitary_atol', 2e-14), max_step=period / 32)

    def derivative(time, vector):
        return (-1j * hamiltonian(case, time) @ vector.reshape(dimension, dimension)).ravel()

    trajectory, unitary = integrate(case, derivative, np.eye(dimension, dtype=complex),
                                    np.array([0.0, period]), integration_options, dense=True)
    monodromy, unused = polar(trajectory[-1])
    triangular, basis = schur(monodromy, output='complex')
    quasienergies = -np.angle(np.diag(triangular)) / period
    if 'branch_shifts' in options:
        quasienergies += 2 * np.pi / period * np.asarray(options['branch_shifts'])

    def periodic_modes(times):
        times = np.atleast_1d(times)
        return (unitary(times) @ basis) * np.exp(1j * times[:, None] * quasienergies)[..., None, :]

    def laboratory_frame(times):
        times = np.atleast_1d(times)
        residual = np.remainder(times, period)
        return periodic_modes(residual) * np.exp(-1j * times[:, None] * quasienergies)[..., None, :]

    return quasienergies, periodic_modes, laboratory_frame


def harmonic_generator(case, quasienergies, modes, samples, harmonics):
    dimension = len(quasienergies)
    generator = np.zeros((dimension ** 2, dimension ** 2), dtype=complex)
    period = case['period']
    grid = np.arange(samples) * period / samples
    frames = modes(grid)
    frequencies_base = quasienergies[None, :] - quasienergies[:, None]
    angular_frequency = 2 * np.pi / period
    for bath, operator in zip(case['baths'], case['a_ops']):
        transformed = frames.conj().transpose(0, 2, 1) @ operator @ frames
        fourier = np.fft.fft(transformed, axis=0) / samples
        frequencies = []
        amplitudes = []
        for harmonic in range(-harmonics, harmonics + 1):
            component = fourier[harmonic % samples]
            for row in range(dimension):
                for column in range(dimension):
                    if abs(component[row, column]) < 1e-14:
                        continue
                    amplitude = np.zeros((dimension, dimension), dtype=complex)
                    amplitude[row, column] = component[row, column]
                    amplitudes.append(amplitude)
                    frequencies.append(frequencies_base[row, column] - harmonic * angular_frequency)
        for frequency, jump in frequency_sectors(frequencies, amplitudes):
            strength = float(spectrum(bath, frequency))
            if strength:
                generator += strength * dissipator(jump)
    return generator


def propagate_floquet(case, initial, options):
    quasienergies, modes, laboratory_frame = floquet_modes(case, options)
    samples = options.get('samples', 256)
    harmonics = min(options.get('harmonics', 48), samples // 2 - 1)
    if options.get('adaptive_harmonics', True):
        angular_frequency = 2 * np.pi / case['period']
        energy_span = float(np.ptp(np.linalg.eigvalsh(case['H0'])))
        drive_harmonic = 0.0
        for operator, specification in zip(case['h_ops'], case['h_coeffs']):
            if specification['kind'] == 'constant':
                magnitude = abs(scalar(specification.get('value', 1.0)))
            elif specification['kind'] == 'steps':
                magnitude = max(abs(scalar(value)) for value in specification['values'])
            else:
                magnitude = abs(scalar(specification.get('offset', 0.0))) + abs(scalar(specification.get('amplitude', 1.0)))
            energy_span += 2 * magnitude * np.linalg.norm(operator, 2)
            if specification['kind'] in ('sin', 'cos', 'carrier'):
                drive_harmonic = max(drive_harmonic, abs(specification.get('omega', 1.0)) / angular_frequency)
        branch_span = np.ptp(options.get('branch_shifts', [0]))
        minimum_harmonics = int(np.ceil(energy_span / angular_frequency + 2 * drive_harmonic + branch_span)) + 8
        harmonics = max(harmonics, minimum_harmonics)
        samples = max(samples, 2 ** int(np.ceil(np.log2(4 * harmonics + 2))))
    previous = harmonic_generator(case, quasienergies, modes, samples, harmonics)
    convergence = options.get('harmonic_tolerance', 2e-10)
    duration = max(1.0, float(case['times'][-1] - case['times'][0]))
    limit = max(options.get('max_samples', 4096), 2 * samples)
    difference = -1.0
    converged = False
    while samples * 2 <= limit and options.get('adaptive_harmonics', True):
        samples *= 2
        harmonics = min(harmonics * 2, samples // 2 - 1)
        generator = harmonic_generator(case, quasienergies, modes, samples, harmonics)
        difference = np.linalg.norm(generator - previous)
        previous = generator
        if difference * duration < convergence:
            converged = True
            break
    if options.get('adaptive_harmonics', True) and not converged:
        warnings.warn('Floquet harmonic refinement reached max_samples before its error target', RuntimeWarning)
    if '_diagnostics' in options:
        options['_diagnostics'].update({'fourier_samples': samples, 'retained_harmonics': harmonics,
                                       'generator_refinement_delta': float(difference),
                                       'harmonics_converged': int(converged)})
    frames = laboratory_frame(case['times'])
    transformed = frames[0].conj().T @ initial @ frames[0]
    states = evolve_generator(previous, transformed, case['times'] - case['times'][0])
    if initial.ndim == 3:
        frames = frames[:, None]
    return frames @ states @ frames.conj().swapaxes(-1, -2)
