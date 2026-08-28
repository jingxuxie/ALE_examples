import json
import sys
from pathlib import Path
import numpy as np
from numba import njit

PUBLIC = Path(__file__).resolve().parents[2] / 'participant' / 'workspace'
sys.path.insert(0, str(PUBLIC))
from common import initialize, effective_field


def spectrum(frequency, values, thermostat):
    amplitude, damping, center, temperature = values['A'], values['Gamma'], values['omega0'], values['T']
    denominator = (center ** 2 - frequency ** 2) ** 2 + damping ** 2 * frequency ** 2
    if thermostat == 'classical':
        return 2 * temperature * amplitude * damping / denominator
    thermal = np.zeros_like(frequency)
    if temperature > 0:
        positive = frequency > 0
        with np.errstate(over='ignore', divide='ignore'):
            thermal[positive] = 2 * frequency[positive] / np.expm1(frequency[positive] / temperature)
        thermal[~positive] = 2 * temperature
    if thermostat == 'quantum':
        thermal += frequency
    return amplitude * damping * thermal / denominator


def forcing(case, material):
    coarse_dt = case['dt'] * case['decimation']
    fft_size = case['nfft']
    frequency = 2 * np.pi * np.fft.rfftfreq(fft_size, coarse_dt)
    density = np.array([spectrum(frequency, values, case['thermostat']) for values in case['materials']])
    covariance = np.fft.irfft(2 * density / coarse_dt, n=fft_size, axis=1)[:, case['lags']]
    required = case['steps'] // case['decimation'] + 2
    noise = np.empty((len(material), 3, required), dtype=np.float64)
    random = np.random.default_rng(case['noise_seed'])
    batch_size = 512
    for start in range(0, len(material), batch_size):
        stop = min(start + batch_size, len(material))
        white = random.standard_normal((stop - start, 3, fft_size))
        transformed = np.fft.rfft(white, axis=2)
        transformed *= np.sqrt(2 * density[material[start:stop], None, :] / coarse_dt)
        noise[start:stop] = np.fft.irfft(transformed, n=fft_size, axis=2)[:, :, :required]
    return noise, covariance


@njit(cache=True)
def derivative(state, time_step, noise, decimation, material, neighbors, parameters, exchange, applied):
    field = effective_field(state[:, :3], material, neighbors, parameters, exchange, applied)
    result = np.empty_like(state)
    coarse_position = time_step / decimation
    left = int(coarse_position)
    fraction = coarse_position - left
    for atom in range(len(state)):
        species = material[atom]
        for component in range(3):
            field[atom, component] += ((1 - fraction) * noise[atom, component, left]
                + fraction * noise[atom, component, left + 1]) / np.sqrt(parameters[species, 0])
            field[atom, component] += state[atom, component + 3]
        result[atom, 0] = state[atom, 1] * field[atom, 2] - state[atom, 2] * field[atom, 1]
        result[atom, 1] = state[atom, 2] * field[atom, 0] - state[atom, 0] * field[atom, 2]
        result[atom, 2] = state[atom, 0] * field[atom, 1] - state[atom, 1] * field[atom, 0]
        for component in range(3):
            result[atom, component + 3] = state[atom, component + 6]
            result[atom, component + 6] = (parameters[species, 2] * state[atom, component]
                - parameters[species, 3] ** 2 * state[atom, component + 3]
                - parameters[species, 4] * state[atom, component + 6])
    return result


@njit(cache=True)
def project(state):
    for atom in range(len(state)):
        norm = np.sqrt(np.sum(state[atom, :3] ** 2))
        state[atom, :3] /= norm
    return state


@njit(cache=True)
def integrate(state, noise, material, neighbors, parameters, exchange, applied, dt, steps, decimation, samples, substeps):
    trace = np.zeros((len(samples), len(parameters), 3))
    snapshot = 0
    for step in range(steps + 1):
        if snapshot < len(samples) and step == samples[snapshot]:
            for species in range(len(parameters)):
                count = 0
                for atom in range(len(state)):
                    if material[atom] == species:
                        count += 1
                        trace[snapshot, species] += state[atom, :3]
                trace[snapshot, species] /= count
            snapshot += 1
        if step == steps:
            break
        step_dt = dt / substeps
        for substep in range(substeps):
            time = step + substep / substeps
            first = derivative(state, time, noise, decimation, material, neighbors, parameters, exchange, applied)
            second = derivative(project(state + step_dt * first / 2), time + 0.5 / substeps,
                noise, decimation, material, neighbors, parameters, exchange, applied)
            third = derivative(project(state + step_dt * second / 2), time + 0.5 / substeps,
                noise, decimation, material, neighbors, parameters, exchange, applied)
            fourth = derivative(project(state + step_dt * third), time + 1.0 / substeps,
                noise, decimation, material, neighbors, parameters, exchange, applied)
            state += step_dt * (first + 2 * second + 2 * third + fourth) / 6
            project(state)
    return state, trace


def solve(case, substeps=1):
    spins, material, neighbors, parameters = initialize(case)
    noise, covariance = forcing(case, material)
    state = np.zeros((len(spins), 9))
    state[:, :3] = spins
    if case['initial_memory'] == 'equilibrated':
        state[:, 3:6] = spins * (parameters[material, 2] / parameters[material, 3] ** 2)[:, None]
    state, trace = integrate(state, noise, material, neighbors, parameters, np.asarray(case['exchange']),
        np.asarray(case['field']), case['dt'], case['steps'], case['decimation'],
        np.asarray(case['sample_steps']), substeps)
    return dict(spins=state[:, :3], memory=state[:, 3:], trace=trace, covariance=covariance)


if __name__ == '__main__':
    np.savez(sys.argv[2], **solve(json.load(open(sys.argv[1]))))
