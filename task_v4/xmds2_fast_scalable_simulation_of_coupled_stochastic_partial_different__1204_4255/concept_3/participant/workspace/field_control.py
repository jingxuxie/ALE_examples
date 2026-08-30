import hashlib
import json
import math
import os
import stat
from pathlib import Path

import numpy as np
from scipy.fft import fftn, ifftn
from scipy.interpolate import BSpline
from scipy.optimize import minimize
from scipy.signal import resample


CHANNELS = ("center", "separation", "omega_x", "omega_y", "detuning", "curvature")
AXES = (-2, -1)


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("nonfinite JSON constant: " + value)


def read_json(path, max_bytes=65536):
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > max_bytes:
            raise ValueError("expected a size-bounded regular JSON file, not a link/device")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            payload = stream.read(max_bytes + 1)
        if len(payload) > max_bytes:
            raise ValueError("artifact exceeds byte limit")
        return json.loads(payload.decode("utf-8"), object_pairs_hook=strict_object, parse_constant=reject_constant)
    finally:
        os.close(descriptor)


def knot_vector(protocol):
    spans = protocol["coefficient_count"] - protocol["spline_degree"]
    return np.r_[np.zeros(4), np.linspace(0.0, protocol["duration"], spans + 1)[1:-1], np.full(4, protocol["duration"])]


def validate_artifact(artifact, protocol):
    if not isinstance(artifact, dict) or set(artifact) != {"schema_version", "controls"}:
        raise ValueError("artifact must contain exactly schema_version and controls")
    if type(artifact["schema_version"]) is not int or artifact["schema_version"] != 1:
        raise ValueError("schema_version must be the integer 1")
    controls = artifact["controls"]
    if not isinstance(controls, dict) or set(controls) != set(CHANNELS):
        raise ValueError("controls must contain exactly the six specified channels")
    knots = knot_vector(protocol)
    splines = {}
    diagnostics = {}
    for channel in CHANNELS:
        values = controls[channel]
        if not isinstance(values, list) or len(values) != protocol["coefficient_count"]:
            raise ValueError(channel + ": expected 25 coefficients")
        if any(type(value) not in (int, float) for value in values):
            raise ValueError(channel + ": coefficients must be real JSON numbers, not booleans")
        coefficients = np.asarray(values, dtype=np.float64)
        if not np.all(np.isfinite(coefficients)):
            raise ValueError(channel + ": nonfinite coefficient")
        limits = protocol["channels"][channel]
        if np.any(coefficients < limits["range"][0] - 1e-12) or np.any(coefficients > limits["range"][1] + 1e-12):
            raise ValueError(channel + ": amplitude certificate failed")
        if np.max(np.abs(coefficients[:3] - limits["start"])) > 1e-12 or np.max(np.abs(coefficients[-3:] - limits["end"])) > 1e-12:
            raise ValueError(channel + ": first/last three coefficients must equal endpoints")
        spline = BSpline(knots, coefficients, 3, extrapolate=False)
        slew = float(np.max(np.abs(spline.derivative(1).c)))
        acceleration = float(np.max(np.abs(spline.derivative(2).c)))
        if slew > limits["slew"] + 1e-12 or acceleration > limits["acceleration"] + 1e-12:
            raise ValueError(channel + ": derivative control-polygon certificate failed")
        diagnostics[channel] = {"coefficient_min": float(coefficients.min()), "coefficient_max": float(coefficients.max()), "slew_bound": slew, "acceleration_bound": acceleration}
        splines[channel] = spline
    rf_radius = np.hypot(controls["omega_x"], controls["omega_y"])
    if np.max(rf_radius) > protocol["rf_radius"] + 1e-12:
        raise ValueError("joint RF coefficient radius exceeds 2.8")
    return splines, diagnostics


def resource_score(splines, protocol):
    nodes, weights = np.polynomial.legendre.leggauss(5)
    breaks = np.unique(knot_vector(protocol))
    integral = 0.0
    for left, right in zip(breaks[:-1], breaks[1:]):
        times = (left + right) / 2 + (right - left) / 2 * nodes
        rf = (splines["omega_x"](times) ** 2 + splines["omega_y"](times) ** 2) / protocol["rf_radius"] ** 2
        motion = 0.5 * ((splines["center"].derivative()(times) / 1.2) ** 2 + (splines["separation"].derivative()(times) / 1.8) ** 2)
        detuning = (splines["detuning"](times) / 3.0) ** 2
        integral += (right - left) / 2 * float(weights @ (0.5 * rf + 0.25 * motion + 0.25 * detuning))
    return float(np.clip(1.0 - integral / protocol["duration"], 0.0, 1.0))


def geometry(shape, domain=((-10.0, 10.0), (-6.0, 6.0))):
    count_x, count_y = shape
    spacing_x = (domain[0][1] - domain[0][0]) / count_x
    spacing_y = (domain[1][1] - domain[1][0]) / count_y
    position_x = domain[0][0] + spacing_x * np.arange(count_x)[:, None]
    position_y = domain[1][0] + spacing_y * np.arange(count_y)[None, :]
    momentum_x = 2 * np.pi * np.fft.fftfreq(count_x, spacing_x)[:, None]
    momentum_y = 2 * np.pi * np.fft.fftfreq(count_y, spacing_y)[None, :]
    kinetic = 0.5 * (momentum_x ** 2 + momentum_y ** 2)
    return position_x, position_y, kinetic, spacing_x * spacing_y


def case_arrays(cases):
    keys = ("g", "self_ratio", "cross_ratio", "trap_x", "trap_y", "rf_gain", "bias", "gradient")
    return {key: np.asarray([case[key] for case in cases])[:, None, None] for key in keys}


def potential(parameters, position_x, position_y, controls):
    center, separation, omega_x, omega_y, detuning, curvature = controls
    common_y = (1.6 * parameters["trap_y"] * position_y) ** 2
    left = 0.5 * ((parameters["trap_x"] ** 2) * curvature * (position_x - center + separation) ** 2 + common_y)
    right = 0.5 * ((parameters["trap_x"] ** 2) * curvature * (position_x - center - separation) ** 2 + common_y)
    bias = 0.5 * (detuning + parameters["bias"] + parameters["gradient"] * position_x)
    return np.stack((left + bias, right - bias), axis=1)


def nonlinear_potential(state, parameters):
    density = np.abs(state) ** 2
    left = parameters["g"] * (density[:, 0] + parameters["cross_ratio"] * density[:, 1])
    right = parameters["g"] * (parameters["self_ratio"] * density[:, 1] + parameters["cross_ratio"] * density[:, 0])
    return np.stack((left, right), axis=1)


def rotate(state, drive_x, drive_y, duration):
    radius = np.hypot(drive_x, drive_y)
    cosine = np.cos(0.5 * duration * radius)
    sine_over_radius = 0.5 * duration * np.sinc(0.5 * duration * radius / np.pi)
    coupling = drive_x - 1j * drive_y
    left = cosine * state[:, 0] - 1j * sine_over_radius * coupling * state[:, 1]
    right = cosine * state[:, 1] - 1j * sine_over_radius * coupling.conjugate() * state[:, 0]
    return np.stack((left, right), axis=1)


def split_step(state, kinetic_phase, trap, parameters, drive_x, drive_y, duration):
    state = ifftn(fftn(state, axes=AXES) * kinetic_phase, axes=AXES)
    state *= np.exp(-0.5j * duration * (trap + nonlinear_potential(state, parameters)))
    state = rotate(state, drive_x, drive_y, duration)
    state *= np.exp(-0.5j * duration * (trap + nonlinear_potential(state, parameters)))
    return ifftn(fftn(state, axes=AXES) * kinetic_phase, axes=AXES)


def stationary(case, shape, final=False, tolerance=2e-6):
    position_x, position_y, kinetic, volume = geometry(shape)
    parameters = case_arrays([case])
    endpoint = (1.0, 2.2, 0.0, 0.0, 0.0, 1.0) if final else (0.0, 0.0, 0.0, 0.0, 0.0, 1.0)
    trap = potential(parameters, position_x, position_y, endpoint)[0]
    masses = np.asarray([0.5, 0.5] if final else [1.0])
    components = len(masses)
    trap = trap[:components]
    centers = ([-1.2, 3.2] if final else [0.0])
    initial = np.stack([np.exp(-0.5 * (case["trap_x"] * (position_x - center) ** 2 + 1.6 * case["trap_y"] * position_y ** 2)) for center in centers])
    preconditioner = np.sqrt(1.0 + kinetic)
    transformed = ifftn(fftn(initial, axes=AXES) * preconditioner, axes=AXES).real

    def unpack(vector):
        field = ifftn(fftn(vector.reshape((components,) + tuple(shape)), axes=AXES) / preconditioner, axes=AXES).real
        lengths = np.sqrt(volume * np.sum(field * field, axis=AXES))
        return field * (np.sqrt(masses) / lengths)[:, None, None], lengths

    def objective(vector):
        field, lengths = unpack(vector)
        kinetic_field = ifftn(fftn(field, axes=AXES) * kinetic, axes=AXES).real
        density = field * field
        coupling = np.asarray([case["g"], case["g"] * case["self_ratio"]])[:components, None, None]
        local = trap + coupling * density
        energy = volume * np.sum(field * kinetic_field + trap * density + 0.5 * coupling * density ** 2)
        if components == 2:
            cross = case["g"] * case["cross_ratio"]
            energy += volume * cross * np.sum(density[0] * density[1])
            local = local + cross * density[::-1]
        hamiltonian = kinetic_field + local * field
        chemical = volume * np.sum(field * hamiltonian, axis=AXES) / masses
        residual = hamiltonian - chemical[:, None, None] * field
        gradient = 2.0 * volume * residual * (np.sqrt(masses) / lengths)[:, None, None]
        gradient = ifftn(fftn(gradient, axes=AXES) / preconditioner, axes=AXES).real
        return float(energy), gradient.ravel()

    result = minimize(objective, transformed.ravel(), jac=True, method="L-BFGS-B", options={"maxiter": 1600, "ftol": 1e-15, "gtol": 1e-11, "maxcor": 12, "maxls": 40})
    field, lengths = unpack(result.x)
    for component in range(components):
        if np.sum(field[component]) < 0:
            field[component] *= -1
    state = np.zeros((2,) + tuple(shape), dtype=np.complex128)
    state[:components] = field
    hamiltonian = ifftn(fftn(state, axes=AXES) * kinetic, axes=AXES) + (potential(parameters, position_x, position_y, endpoint)[0] + nonlinear_potential(state[None], parameters)[0]) * state
    residuals = []
    for component, mass in enumerate(masses):
        chemical = volume * np.vdot(state[component], hamiltonian[component]).real / mass
        residuals.append(float(np.sqrt(volume * np.sum(np.abs(hamiltonian[component] - chemical * state[component]) ** 2) / mass)))
    residual = max(residuals)
    if not np.isfinite(residual) or residual > tolerance:
        raise ArithmeticError("stationary reference residual %.3g exceeds %.3g for %s" % (residual, tolerance, case["id"]))
    if final:
        state[1] *= -1j
    return state, {"residual": residual, "iterations": int(result.nit), "energy": float(result.fun)}


def reference_key(cases, shape):
    payload = json.dumps({"cases": cases, "shape": list(shape), "reference_version": 1}, sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()


def references(cases, shape, cache_directory=None):
    key = reference_key(cases, shape)
    cache = None if cache_directory is None else Path(cache_directory) / (key + ".npz")
    if cache is not None and cache.exists():
        with np.load(cache, allow_pickle=False) as data:
            return data["initial"].copy(), data["target"].copy(), float(data["residual"])
    initial_states, target_states, residuals = [], [], []
    for case in cases:
        initial, initial_info = stationary(case, shape)
        target, target_info = stationary(case, shape, final=True)
        initial_states.append(initial)
        target_states.append(target)
        residuals.extend((initial_info["residual"], target_info["residual"]))
    result = np.asarray(initial_states), np.asarray(target_states), max(residuals)
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache, initial=result[0], target=result[1], residual=result[2])
    return result


def diagnostics(state, shape):
    position_x, position_y, kinetic, volume = geometry(shape)
    density = np.sum(np.abs(state) ** 2, axis=1)
    norm = volume * np.sum(density, axis=AXES)
    boundary = (np.abs(position_x) >= 8.0) | (np.abs(position_y) >= 4.8)
    boundary_mass = volume * np.sum(density * boundary, axis=AXES)
    spectrum = np.sum(np.abs(fftn(state, axes=AXES)) ** 2, axis=1)
    frequency_x = np.abs(np.fft.fftfreq(shape[0]))[:, None]
    frequency_y = np.abs(np.fft.fftfreq(shape[1]))[None, :]
    tail = (frequency_x >= 0.4) | (frequency_y >= 0.4)
    tail_mass = np.sum(spectrum * tail, axis=AXES) / np.sum(spectrum, axis=AXES)
    return np.abs(norm - 1.0), boundary_mass, tail_mass


def evolve(splines, cases, shape, dt, initial, duration=8.0):
    steps = int(round(duration / dt))
    if steps < 1 or abs(steps * dt - duration) > 1e-10:
        raise ValueError("duration must be an integer multiple of dt")
    position_x, position_y, kinetic, volume = geometry(shape)
    parameters = case_arrays(cases)
    controls = np.stack([splines[channel]((np.arange(steps) + 0.5) * dt) for channel in CHANNELS], axis=1)
    kinetic_phase = np.exp(-0.5j * dt * kinetic)
    state = initial.copy()
    maxima = np.zeros((3, len(cases)))
    for step_index, values in enumerate(controls):
        trap = potential(parameters, position_x, position_y, values)
        state = split_step(state, kinetic_phase, trap, parameters, parameters["rf_gain"] * values[2], parameters["rf_gain"] * values[3], dt)
        if step_index % 20 == 0 or step_index == steps - 1:
            if not np.all(np.isfinite(state)):
                raise ArithmeticError("nonfinite propagated state")
            maxima = np.maximum(maxima, np.asarray(diagnostics(state, shape)))
    return state, {"norm_error": maxima[0], "boundary_mass": maxima[1], "spectral_tail": maxima[2]}


def fidelities(state, target, shape):
    volume = geometry(shape)[3]
    overlap = volume * np.sum(np.conj(target) * state, axis=(1, 2, 3))
    return np.clip(np.abs(overlap) ** 2, 0.0, 1.0)


def state_distance(left, right, shape):
    volume = geometry(shape)[3]
    overlap = volume * np.sum(np.conj(left) * right, axis=(1, 2, 3))
    alignment = np.exp(-1j * np.angle(overlap))[:, None, None, None]
    return np.sqrt(volume * np.sum(np.abs(left - right * alignment) ** 2, axis=(1, 2, 3)))


def prolong(state, shape):
    return resample(resample(state, shape[0], axis=-2), shape[1], axis=-1)


def summarize(values, cases, protocol):
    families = sorted({case["family"] for case in cases})
    family_scores = {family: float(np.mean([value for value, case in zip(values, cases) if case["family"] == family])) for family in families}
    core = float(np.mean(list(family_scores.values())))
    worst_family = min(family_scores.values())
    worst_case = float(np.min(values))
    thresholds = protocol["thresholds"]
    passed = core >= thresholds["core_score"] and worst_family >= thresholds["worst_family_score"] and worst_case >= thresholds["worst_case_score"]
    return {"core_score": core, "worst_family_score": worst_family, "worst_case_score": worst_case, "family_scores": family_scores, "passed": bool(passed)}


def failure(reason, elapsed=0.0):
    return {"core_score": 0.0, "worst_family_score": 0.0, "worst_case_score": 0.0, "runtime_score": 0.0, "resource_score": 0.0, "runtime_seconds": float(elapsed), "passed": False, "valid": False, "reason": reason}
