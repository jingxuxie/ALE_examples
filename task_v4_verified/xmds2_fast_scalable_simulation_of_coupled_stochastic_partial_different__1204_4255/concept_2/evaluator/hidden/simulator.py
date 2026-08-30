import json
import math
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp


FRACTIONS = tuple(np.arange(1, 9) / 8)


DEFAULT = {
    "dispersion": 0.25,
    "nonlinearity": 12.0,
    "cross": 0.8,
    "coupling": 0.6,
    "detuning": 0.2,
    "duration": 1.0,
    "population": 0.55,
    "a1": 0.22,
    "b1": 0.12,
    "c1": 0.14,
    "a2": 0.18,
    "b2": 0.1,
    "c2": -0.12,
    "phase1": 0.5,
    "phase2": 1.1,
    "shift": 0.7,
    "relative_phase": 0.3,
}


def modes(size):
    return np.fft.fftfreq(size, 1.0 / size)


def resize(state, size):
    source_size = state.shape[-1]
    result = np.zeros(state.shape[:-1] + (size,), dtype=np.complex128)
    source_modes = modes(source_size).astype(int)
    keep = (source_modes >= -size // 2) & (source_modes < size // 2)
    result[..., source_modes[keep] % size] = state[..., keep]
    return result


def initial(parameters, size):
    position = 2 * np.pi * np.arange(size) / size
    first = (
        1 + parameters["a1"] * np.cos(position)
        + parameters["b1"] * np.cos(2 * position + parameters["phase1"])
        + 1j * parameters["c1"] * np.sin(position + parameters["phase2"])
    )
    second = (
        1 + parameters["a2"] * np.cos(position + parameters["shift"])
        + parameters["b2"] * np.cos(3 * position + parameters["phase2"])
        + 1j * parameters["c2"] * np.sin(2 * position + parameters["phase1"])
    )
    first *= np.sqrt(parameters["population"] / np.mean(abs(first) ** 2))
    second *= np.sqrt((1 - parameters["population"]) / np.mean(abs(second) ** 2))
    second *= np.exp(1j * parameters["relative_phase"])
    return np.fft.fft(np.array([first, second]), axis=-1) / size


class Dynamics:
    def __init__(self, parameters, size):
        self.parameters = parameters
        self.size = size
        self.wavenumbers = modes(size)
        self.dispersion = parameters["dispersion"] * self.wavenumbers ** 2
        self.frequency = math.hypot(parameters["coupling"], parameters["detuning"])
        self.matrix = np.array([
            [parameters["detuning"], parameters["coupling"]],
            [parameters["coupling"], -parameters["detuning"]],
        ])
        self.padding = 2 * size
        self.indices = self.wavenumbers.astype(int) % self.padding

    def propagator(self, interval):
        rotation = np.cos(self.frequency * interval) * np.eye(2, dtype=complex)
        if self.frequency:
            rotation -= 1j * np.sin(self.frequency * interval) / self.frequency * self.matrix
        return np.exp(-1j * interval * self.dispersion), rotation

    def linear(self, state, propagator):
        diagonal, rotation = propagator
        return diagonal * (rotation @ state)

    def nonlinear(self, state):
        padded = np.zeros((2, self.padding), dtype=complex)
        padded[:, self.indices] = state
        field = np.fft.ifft(padded, axis=-1) * self.padding
        density = abs(field) ** 2
        potential = self.parameters["nonlinearity"] * (
            density + self.parameters["cross"] * density[::-1]
        )
        transformed = np.fft.fft(1j * potential * field, axis=-1) / self.padding
        return transformed[:, self.indices]

    def hamiltonian(self, state):
        field = np.fft.ifft(resize(state, self.padding), axis=-1) * self.padding
        density = abs(field) ** 2
        kinetic = np.sum(self.dispersion * abs(state) ** 2)
        mixing = np.vdot(state, self.matrix @ state).real
        potential = -0.5 * self.parameters["nonlinearity"] * np.mean(
            density[0] ** 2 + density[1] ** 2
            + 2 * self.parameters["cross"] * density[0] * density[1]
        )
        return float(kinetic + mixing + potential)


def integrate(parameters, size=32, steps=512, fractions=FRACTIONS):
    dynamics = Dynamics(parameters, size)
    state = initial(parameters, size)
    interval = parameters["duration"] / steps
    half = dynamics.propagator(interval / 2)
    full = dynamics.propagator(interval)
    save_at = {round(fraction * steps): index for index, fraction in enumerate(fractions)}
    if any(abs(round(fraction * steps) - fraction * steps) > 1e-9 for fraction in fractions):
        raise ValueError("steps must align with observation times")
    snapshots = np.empty((len(fractions), 2, size), dtype=complex)
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        for step_index in range(1, steps + 1):
            first = dynamics.nonlinear(state)
            midpoint = dynamics.linear(state, half)
            second = dynamics.nonlinear(midpoint + interval / 2 * dynamics.linear(first, half))
            third = dynamics.nonlinear(midpoint + interval / 2 * second)
            fourth = dynamics.nonlinear(dynamics.linear(state, full) + interval * dynamics.linear(third, half))
            state = dynamics.linear(state + interval / 6 * first, full)
            state += interval / 3 * dynamics.linear(second + third, half) + interval / 6 * fourth
            if step_index in save_at:
                if not np.isfinite(state).all() or np.max(abs(state)) > 100:
                    raise ValueError("unstable trajectory")
                snapshots[save_at[step_index]] = state
    return snapshots


def independent(parameters, size=128, tolerance=2e-10, fractions=FRACTIONS):
    dynamics = Dynamics(parameters, size)
    start = initial(parameters, size)

    def derivative(time, flattened):
        interaction = flattened.reshape(2, size)
        state = dynamics.linear(interaction, dynamics.propagator(time))
        nonlinear = dynamics.nonlinear(state)
        return dynamics.linear(nonlinear, dynamics.propagator(-time)).ravel()

    times = np.asarray(fractions) * parameters["duration"]
    solution = solve_ivp(
        derivative, (0, parameters["duration"]), start.ravel(), method="DOP853",
        t_eval=times, rtol=tolerance, atol=tolerance * 0.02,
        max_step=parameters["duration"] / 64,
    )
    if not solution.success:
        raise ValueError("independent reference did not converge")
    snapshots = np.array([
        dynamics.linear(solution.y[:, index].reshape(2, size), dynamics.propagator(time))
        for index, time in enumerate(times)
    ])
    return snapshots, int(solution.nfev)


def field_distance(first, second):
    size = max(first.shape[-1], second.shape[-1])
    difference = resize(first, size) - resize(second, size)
    return np.sqrt(np.sum(abs(difference) ** 2, axis=(-1, -2)))


def observables(states):
    size = 2 * states.shape[-1]
    fields = np.fft.ifft(resize(states, size), axis=-1) * size
    density = abs(fields) ** 2
    transformed = np.fft.fft(density, axis=-1) / size
    selected = np.arange(-4, 5) % size
    return transformed[..., selected]


def observable_distance(first, second):
    difference = observables(first) - observables(second)
    return np.sqrt(np.sum(abs(difference) ** 2, axis=(-1, -2)))


def diagnostics(parameters, states):
    size = states.shape[-1]
    dynamics = Dynamics(parameters, size)
    start = initial(parameters, size)
    mass = np.sum(abs(states) ** 2, axis=(-1, -2))
    energy_start = dynamics.hamiltonian(start)
    energy = np.array([dynamics.hamiltonian(state) for state in states])
    tail = np.sum(abs(states[..., abs(modes(size)) >= 0.375 * size]) ** 2, axis=(-1, -2))
    return {
        "mass_drift": float(np.max(abs(mass - 1))),
        "energy_drift": float(np.max(abs(energy - energy_start)) / max(1, abs(energy_start))),
        "tail_mass": float(np.max(tail)),
    }


def quick(parameters, steps=512, reference_size=96):
    coarse = integrate(parameters, 32, steps)
    fine = integrate(parameters, 32, 2 * steps)
    reference = integrate(parameters, reference_size, 4 * steps)
    return {
        "certificate": float(np.max(field_distance(coarse, fine))),
        "observable_gap": float(np.min(observable_distance(fine, reference)[-3:])),
        "field_gap": float(np.min(field_distance(fine, reference)[-3:])),
        **diagnostics(parameters, fine),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("submission")
    parser.add_argument("--steps", type=int, default=512)
    arguments = parser.parse_args()
    payload = json.loads(Path(arguments.submission).read_text())
    print(json.dumps(quick(payload["parameters"], arguments.steps), allow_nan=False, indent=2))
