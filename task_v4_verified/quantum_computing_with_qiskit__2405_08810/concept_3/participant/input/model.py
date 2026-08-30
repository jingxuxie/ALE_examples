import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


CONFIG = json.loads(Path(__file__).with_name("config.json").read_text())
BOUNDS = np.array(CONFIG["bounds"], dtype=float)
NORMALIZATION = np.array(CONFIG["normalization"], dtype=float)
PAULIS = {
    "I": np.eye(2, dtype=complex),
    "X": np.array([[0, 1], [1, 0]], dtype=complex),
    "Y": np.array([[0, -1j], [1j, 0]], dtype=complex),
    "Z": np.diag([1, -1]).astype(complex),
}
PREPARATIONS = tuple(axis + sign for axis in "XYZ" for sign in "+-")
MEASUREMENTS = tuple(left + right for left in "IXYZ" for right in "IXYZ" if left + right != "II")
GENERATORS = np.stack([np.kron(PAULIS[term[0]], PAULIS[term[1]]) for term in ("IX", "ZX", "IZ", "ZZ", "ZI")])


def finite_number(value):
    if type(value) not in (int, float):
        return False
    try:
        return bool(np.isfinite(value))
    except (TypeError, OverflowError):
        return False


def validate_experiment(message):
    if not isinstance(message, dict) or set(message) != {"type", "prep", "measure", "time", "shots"}:
        raise ValueError("experiment must contain exactly type, prep, measure, time, shots")
    if message["type"] != "experiment":
        raise ValueError("expected experiment")
    if not isinstance(message["prep"], list) or len(message["prep"]) != 2:
        raise ValueError("prep must be a two-element list")
    if any(not isinstance(state, str) or state not in PREPARATIONS for state in message["prep"]):
        raise ValueError("invalid preparation")
    if not isinstance(message["measure"], str) or message["measure"] not in MEASUREMENTS:
        raise ValueError("measure must be a nonidentity two-qubit Pauli string")
    if not finite_number(message["time"]) or not 0 <= message["time"] <= CONFIG["budget"]["max_time"]:
        raise ValueError("time out of bounds")
    if type(message["shots"]) is not int or not 1 <= message["shots"] <= CONFIG["budget"]["max_shots_per_query"]:
        raise ValueError("shots out of bounds")
    return message


def validate_estimate(message):
    if not isinstance(message, dict) or set(message) not in ({"type", "omega"}, {"type", "omega", "nuisance"}):
        raise ValueError("estimate must contain type, omega, and optionally nuisance")
    if message["type"] != "estimate":
        raise ValueError("expected estimate")
    omega = message["omega"]
    if not isinstance(omega, list) or len(omega) != 5 or not all(finite_number(value) for value in omega):
        raise ValueError("omega must contain five finite numbers")
    if np.any(np.array(omega) < BOUNDS[:5, 0]) or np.any(np.array(omega) > BOUNDS[:5, 1]):
        raise ValueError("omega out of bounds")
    if "nuisance" in message:
        nuisance = message["nuisance"]
        if not isinstance(nuisance, list) or len(nuisance) != 4 or not all(finite_number(value) for value in nuisance):
            raise ValueError("nuisance must contain four finite numbers")
        if np.any(np.array(nuisance) < BOUNDS[5:, 0]) or np.any(np.array(nuisance) > BOUNDS[5:, 1]):
            raise ValueError("nuisance out of bounds")
    return np.array(omega, dtype=float)


def hamiltonian(parameters):
    return np.einsum("a,aij->ij", np.asarray(parameters)[:5], GENERATORS) / 2


def unitaries(parameters, times):
    omega_ix, omega_zx, omega_iz, omega_zz, omega_zi = np.asarray(parameters)[:5]
    times = np.atleast_1d(times).astype(float)
    result = np.zeros((len(times), 4, 4), dtype=complex)
    for control_index, control_sign in enumerate((1, -1)):
        axis_x = omega_ix + control_sign * omega_zx
        axis_z = omega_iz + control_sign * omega_zz
        frequency = np.hypot(axis_x, axis_z)
        cosine = np.cos(frequency * times / 2)
        sine_over_frequency = times / 2 * np.sinc(frequency * times / (2 * np.pi))
        phase = np.exp(-0.5j * control_sign * omega_zi * times)
        block_start = 2 * control_index
        result[:, block_start, block_start] = phase * (cosine - 1j * sine_over_frequency * axis_z)
        result[:, block_start + 1, block_start + 1] = phase * (cosine + 1j * sine_over_frequency * axis_z)
        result[:, block_start, block_start + 1] = -1j * phase * sine_over_frequency * axis_x
        result[:, block_start + 1, block_start] = -1j * phase * sine_over_frequency * axis_x
    return result


@dataclass
class ExperimentBatch:
    times: np.ndarray
    linear_density: np.ndarray
    quadratic_density: np.ndarray
    observables: np.ndarray

    def subset(self, mask):
        return ExperimentBatch(self.times[mask], self.linear_density[mask], self.quadratic_density[mask], self.observables[mask])


def compile_experiments(experiments):
    linear_density = []
    quadratic_density = []
    observables = []
    for experiment in experiments:
        control_state, target_state = experiment["prep"]
        control_axis = PAULIS[control_state[0]] * (1 if control_state[1] == "+" else -1)
        target_axis = PAULIS[target_state[0]] * (1 if target_state[1] == "+" else -1)
        linear_density.append((np.kron(control_axis, PAULIS["I"]) + np.kron(PAULIS["I"], target_axis)) / 4)
        quadratic_density.append(np.kron(control_axis, target_axis) / 4)
        observable = experiment["measure"]
        observables.append(np.kron(PAULIS[observable[0]], PAULIS[observable[1]]))
    return ExperimentBatch(
        np.array([experiment["time"] for experiment in experiments], dtype=float),
        np.array(linear_density), np.array(quadratic_density), np.array(observables),
    )


def probabilities(parameters, experiments):
    batch = experiments if isinstance(experiments, ExperimentBatch) else compile_experiments(experiments)
    prep_visibility, readout_contrast, readout_bias, decay_rate = np.asarray(parameters)[5:]
    unitary = unitaries(parameters, batch.times)
    traceless_density = prep_visibility * batch.linear_density + prep_visibility**2 * batch.quadratic_density
    evolved = unitary @ traceless_density @ unitary.conj().transpose(0, 2, 1)
    expectation = np.einsum("nij,nji->n", batch.observables, evolved).real
    probability = (1 + readout_bias + readout_contrast * np.exp(-decay_rate * batch.times) * expectation) / 2
    return np.clip(probability, 0, 1)


def draw_parameters(rng, family):
    def signed_uniform(lower, upper):
        return float(rng.choice([-1, 1]) * rng.uniform(lower, upper))

    if family == "aliasing":
        omega = [signed_uniform(3.2, 5), signed_uniform(0.5, 1.8), signed_uniform(1, 2.8), signed_uniform(0.1, 1.1), signed_uniform(1, 2.5)]
    elif family == "near_degenerate":
        while True:
            omega_ix = signed_uniform(1, 2.4)
            omega_iz = signed_uniform(1.1, 2.5)
            omega_zx = signed_uniform(0.2, 0.8)
            omega_zz = -omega_ix * omega_zx / omega_iz + rng.uniform(-0.015, 0.015)
            if abs(omega_zz) < 1.2:
                break
        omega = [omega_ix, omega_zx, omega_iz, float(omega_zz), signed_uniform(0.12, 1.6)]
    elif family == "weak_entangling":
        omega = [signed_uniform(1, 3.5), signed_uniform(0.04, 0.16), signed_uniform(0.3, 2.2), signed_uniform(0.02, 0.12), signed_uniform(0.2, 1.8)]
    elif family == "nuisance_decoherence":
        omega = [signed_uniform(0.7, 3.8), signed_uniform(0.25, 1.5), signed_uniform(0.3, 2.4), signed_uniform(0.15, 1.1), signed_uniform(0.2, 2)]
    else:
        raise ValueError("unknown family")
    if family == "nuisance_decoherence":
        nuisance = [rng.uniform(0.78, 0.86), rng.uniform(0.78, 0.85), rng.uniform(-0.045, 0.045), rng.uniform(0.1, 0.16)]
    else:
        nuisance = [rng.uniform(0.91, 0.99), rng.uniform(0.9, 0.95), rng.uniform(-0.025, 0.025), rng.uniform(0.008, 0.045)]
    return np.array(omega + nuisance, dtype=float)


def normalized_error(omega, parameters):
    return float(np.sqrt(np.mean(((np.asarray(omega) - np.asarray(parameters)[:5]) / NORMALIZATION)**2)))
