import numpy as np
import gc
from scipy.integrate import DOP853
from .protocols import signal, perturbation
from .observables import measure


def evolve_batch(case, hamiltonian, energies, initial, active, entries, config):
    dimension = hamiltonian.shape[0]
    count = len(energies)
    density, current = [], []
    active_lookup = {int(global_index): index for index, global_index in enumerate(active)}
    groups = []
    for drive in case['drives']:
        selected = [entry for entry in entries if entry[-1] is drive]
        groups.append((drive, selected))
    state = np.zeros((dimension, count), complex)

    def rhs(clock, flattened):
        correction = flattened.reshape(dimension, count)
        result = hamiltonian @ correction
        local = correction[active] + initial * np.exp(-1j * energies * clock)
        for drive, selected in groups:
            amplitude = signal(clock, drive)
            for row, column, base, kind, spec in selected:
                change = base * (np.exp(-1j * amplitude) - 1) if kind == 'phase' else base * amplitude
                result[row] += change * local[active_lookup[column]]
                if row != column:
                    result[column] += change.conjugate() * local[active_lookup[row]]
        return (-1j * result).ravel()

    def observe(clock, correction):
        local = correction.reshape(dimension, count)[active] + initial * np.exp(-1j * energies * clock)
        central_size = len(case['hamiltonian']['real'])
        central_hamiltonian = (hamiltonian + perturbation(clock, entries, dimension))[:central_size, :central_size]
        densities, currents = measure(case, central_hamiltonian, local[:central_size])
        density.append(densities)
        current.append(currents)

    times = np.asarray(case['times'])
    observe(0., state)
    if not count or not entries or times[-1] == 0:
        for target in times[1:]:
            observe(target, state)
        return np.asarray(density), np.asarray(current), dict(rhs_evaluations=0, accepted_time_steps=0)
    solver = DOP853(rhs, 0., state.ravel(), times[-1], rtol=config['rtol'],
                    atol=config['atol'], max_step=config['max_step'])
    events = sorted({event for drive in case['drives']
                     if drive.get('start', 0.) > 0 or drive['duration'] < 2 * config['max_step']
                     for event in [drive.get('start', 0.), drive.get('start', 0.) + drive['duration']]
                     if 0 < event < times[-1]})
    event_index = 0
    output_index = 1
    steps = 0
    while solver.status == 'running':
        while event_index < len(events) and events[event_index] <= solver.t + 1e-12:
            event_index += 1
        maximum_step = config['max_step']
        if event_index < len(events):
            maximum_step = min(maximum_step, events[event_index] - solver.t)
        for drive in case['drives']:
            if drive['profile'] == 'ac' and solver.t >= drive.get('start', 0.) and abs(drive['omega']) > 0:
                maximum_step = min(maximum_step, np.pi / abs(drive['omega']))
        solver.max_step = maximum_step
        solver.step()
        steps += 1
        if solver.status == 'failed':
            raise RuntimeError('time integration failed')
        if output_index < len(times) and times[output_index] <= solver.t + 1e-12:
            interpolation = solver.dense_output()
            while output_index < len(times) and times[output_index] <= solver.t + 1e-12:
                target = times[output_index]
                observe(target, interpolation(min(target, solver.t)))
                output_index += 1
    return np.asarray(density), np.asarray(current), dict(rhs_evaluations=solver.nfev, accepted_time_steps=steps)


def evolve_source(case, hamiltonian, energies, initial, active, entries, config):
    if not np.all(np.isfinite(energies)) or not np.all(np.isfinite(initial)):
        raise FloatingPointError('nonfinite scattering preparation; refusing time propagation')
    density = np.zeros((len(case['times']), len(case['hamiltonian']['real'])))
    current = np.zeros((len(case['times']), len(case['current_bonds'])))
    metadata = dict(rhs_evaluations=0, accepted_time_steps=0, state_batches=0)
    for start in range(0, max(1, len(energies)), config['state_batch_size']):
        stop = min(start + config['state_batch_size'], len(energies))
        batch_density, batch_current, batch_metadata = evolve_batch(
            case, hamiltonian, energies[start:stop], initial[:, start:stop], active, entries, config)
        density += batch_density
        current += batch_current
        metadata['rhs_evaluations'] += batch_metadata['rhs_evaluations']
        metadata['accepted_time_steps'] += batch_metadata['accepted_time_steps']
        metadata['state_batches'] += 1
        gc.collect()
    return density, current, metadata
