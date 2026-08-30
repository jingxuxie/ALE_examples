import copy
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator/hidden"))
from field_control import case_arrays, evolve, geometry, nonlinear_potential, prolong, read_json, references, rotate, split_step, state_distance, stationary, validate_artifact


def run():
    started = time.perf_counter()
    protocol = read_json(ROOT / "participant/input/protocol.json")
    artifact = read_json(ROOT / "participant/baseline/control.json")
    cases = read_json(ROOT / "participant/input/public_cases.json")
    splines, certificate = validate_artifact(artifact, protocol)
    invalid = []
    mutations = [
        ("nan", lambda data: data["controls"]["center"].__setitem__(10, float("nan"))),
        ("infinity", lambda data: data["controls"]["center"].__setitem__(10, float("inf"))),
        ("boolean", lambda data: data["controls"]["center"].__setitem__(10, True)),
        ("bad_endpoint", lambda data: data["controls"]["center"].__setitem__(0, 0.1)),
        ("amplitude", lambda data: data["controls"]["center"].__setitem__(10, 2.0)),
        ("slew", lambda data: data["controls"]["center"].__setitem__(10, 1.8)),
        ("acceleration", lambda data: data["controls"].__setitem__("center", [0.0] * 11 + [0.43, 0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])),
        ("length", lambda data: data["controls"]["center"].pop()),
        ("extra_key", lambda data: data.__setitem__("execute", "evil.py")),
        ("schema_boolean", lambda data: data.__setitem__("schema_version", True)),
        ("string_number", lambda data: data["controls"]["center"].__setitem__(10, "0.1"))
    ]
    for name, mutate in mutations:
        bad = copy.deepcopy(artifact)
        mutate(bad)
        try:
            validate_artifact(bad, protocol)
        except (ValueError, OverflowError):
            invalid.append(name)
        else:
            raise AssertionError("malformed artifact accepted: " + name)
    bad = copy.deepcopy(artifact)
    fraction = np.clip((np.arange(25) - 2) / 20.0, 0.0, 1.0)
    hump = (2.5 * np.sin(np.pi * fraction) ** 2).tolist()
    hump[:3] = [0.0] * 3
    hump[-3:] = [0.0] * 3
    bad["controls"]["omega_x"] = hump
    bad["controls"]["omega_y"] = hump
    try:
        validate_artifact(bad, protocol)
    except ValueError as error:
        assert "joint RF" in str(error)
        invalid.append("joint_rf_radius")
    else:
        raise AssertionError("joint RF radius violation accepted")
    temporary_root = ROOT / "adversary"
    with tempfile.TemporaryDirectory(dir=temporary_root) as temporary:
        directory = Path(temporary)
        for name, payload in (("duplicate", '{"schema_version":1,"schema_version":1}'), ("json_nan", '{"x":NaN}'), ("json_inf", '{"x":Infinity}'), ("oversize", " " * 65537), ("executable", "import os\nos.system('true')")):
            path = directory / (name + ".json")
            path.write_text(payload)
            try:
                read_json(path)
            except (ValueError, UnicodeError):
                invalid.append(name)
            else:
                raise AssertionError("malformed JSON accepted: " + name)
        link = directory / "link.json"
        link.symlink_to(ROOT / "participant/baseline/control.json")
        fifo = directory / "fifo.json"
        os.mkfifo(fifo)
        for name, path in (("symlink", link), ("fifo", fifo)):
            try:
                read_json(path)
            except (ValueError, OSError):
                invalid.append(name)
            else:
                raise AssertionError("special file accepted: " + name)
    nominal = cases[0]
    shape = (24, 16)
    position_x, position_y, kinetic, volume = geometry(shape)
    parameters = case_arrays([dict(nominal, self_ratio=1.0, cross_ratio=1.0)])
    state = np.zeros((1, 2) + shape, dtype=np.complex128)
    state[:, 0] = 1.0 / np.sqrt(240.0)
    initial = state.copy()
    trap = np.zeros_like(state.real)
    duration = 0.013
    drive_x = np.full((1, 1, 1), 0.7)
    drive_y = np.full((1, 1, 1), -0.4)
    for index in range(37):
        state = split_step(state, np.exp(-0.5j * duration * kinetic), trap, parameters, drive_x, drive_y, duration)
    exact = rotate(initial, drive_x, drive_y, 37 * duration) * np.exp(-1j * nominal["g"] / 240.0 * 37 * duration)
    rabi_error = float(np.sqrt(volume * np.sum(np.abs(state - exact) ** 2)))
    assert rabi_error < 1e-12, rabi_error
    parameters = case_arrays([nominal])
    initial = np.zeros((1, 2) + shape, dtype=np.complex128)
    initial[:, 0] = np.sqrt(0.7 / 240.0) * np.exp(2j * np.pi * (position_x + 10.0) / 20.0)
    initial[:, 1] = np.sqrt(0.3 / 240.0) * np.exp(4j * np.pi * (position_y + 6.0) / 12.0)
    state = split_step(initial, np.exp(-0.5j * duration * kinetic), trap, parameters, 0.0, 0.0, duration)
    energies = np.asarray([0.5 * (2 * np.pi / 20.0) ** 2, 0.5 * (4 * np.pi / 12.0) ** 2])[None, :, None, None] + nonlinear_potential(initial, parameters)
    exact = initial * np.exp(-1j * duration * energies)
    plane_error = float(np.sqrt(volume * np.sum(np.abs(state - exact) ** 2)))
    assert plane_error < 1e-12, plane_error
    random = np.random.default_rng(4255)
    trap = random.normal(size=initial.shape)
    forward = split_step(initial, np.exp(-0.5j * duration * kinetic), trap, parameters, drive_x, drive_y, duration)
    backward = split_step(forward, np.exp(0.5j * duration * kinetic), trap, parameters, drive_x, drive_y, -duration)
    reversal_error = float(np.sqrt(volume * np.sum(np.abs(initial - backward) ** 2)))
    assert reversal_error < 1e-12, reversal_error
    small_parameters = case_arrays([dict(nominal, self_ratio=1.07, cross_ratio=0.83)])
    local_initial = np.asarray([[[[np.sqrt(0.8)]]], [[[np.sqrt(0.2) * 1j]]]]).reshape(1, 2, 1, 1)
    local_trap = np.asarray([0.31, -0.17]).reshape(1, 2, 1, 1)

    def rhs(current_time, vector):
        field = vector.reshape(1, 2, 1, 1)
        result = (local_trap + nonlinear_potential(field, small_parameters)) * field
        result[:, 0] += (0.7 + 0.4j) * field[:, 1] / 2
        result[:, 1] += (0.7 - 0.4j) * field[:, 0] / 2
        return (-1j * result).ravel()

    independent = solve_ivp(rhs, (0.0, 0.8), local_initial.ravel(), method="DOP853", rtol=2e-13, atol=2e-14).y[:, -1]
    ode_errors = []
    for timestep in (0.02, 0.01, 0.005):
        field = local_initial.copy()
        for index in range(round(0.8 / timestep)):
            field = split_step(field, np.ones((1, 1)), local_trap, small_parameters, drive_x, drive_y, timestep)
        ode_errors.append(float(np.linalg.norm(field.ravel() - independent)))
    assert 3.8 < ode_errors[0] / ode_errors[1] < 4.2
    assert 3.8 < ode_errors[1] / ode_errors[2] < 4.2
    linear_case = dict(nominal, id="linear_ground", g=0.0)
    ground, ground_info = stationary(linear_case, (64, 32))
    position_x, position_y, kinetic, volume = geometry((64, 32))
    gaussian = np.exp(-0.5 * (position_x ** 2 + 1.6 * position_y ** 2))
    gaussian /= np.sqrt(volume * np.sum(gaussian ** 2))
    harmonic_fidelity = float(abs(volume * np.vdot(gaussian, ground[0])) ** 2)
    assert harmonic_fidelity > 1 - 1e-9
    assert abs(ground_info["energy"] - 1.3) < 1e-8
    shape = (64, 32)
    initial, target, residual = references(cases[:1], shape, ROOT / "authoring/reference_cache")
    fields = []
    runtime = []
    for timestep in (0.04, 0.02, 0.01, 0.005):
        started_evolution = time.perf_counter()
        field, audit = evolve(splines, cases[:1], shape, timestep, initial)
        runtime.append(time.perf_counter() - started_evolution)
        fields.append(field)
        assert float(np.max(audit["norm_error"])) < 1e-10
    field_errors = [float(state_distance(field, fields[-1], shape)[0]) for field in fields[:-1]]
    assert field_errors[0] > 3 * field_errors[1] > 9 * field_errors[2], field_errors
    initial_high, target_high, high_residual = references(cases[:1], (112, 56), ROOT / "authoring/reference_cache")
    reference_distance = float(state_distance(prolong(target, (112, 56)), target_high, (112, 56))[0])
    assert reference_distance < 2e-5, reference_distance
    hidden = read_json(ROOT / "evaluator/hidden/cases.json")
    for case in hidden:
        for key, bounds in protocol["uncertainty"].items():
            assert bounds[0] <= case[key] <= bounds[1]
    assert len(hidden) == 21
    assert (ROOT / "evaluator/hidden/field_control.py").read_bytes() == (ROOT / "participant/workspace/field_control.py").read_bytes()
    assert (ROOT / "evaluator/hidden/protocol.json").read_bytes() == (ROOT / "participant/input/protocol.json").read_bytes()
    result = {"passed": True, "fresh_agents_run": 0, "malformed_rejections": invalid, "rabi_exact_error": rabi_error, "plane_wave_exact_error": plane_error, "time_reversal_error": reversal_error, "independent_dop853_errors": ode_errors, "harmonic_ground_fidelity": harmonic_fidelity, "harmonic_ground_energy": ground_info["energy"], "field_refinement_distances_to_dt_0_005": field_errors, "reference_grid_distance": reference_distance, "maximum_reference_residual": max(residual, high_residual), "single_case_evolution_seconds": runtime, "runtime_seconds": time.perf_counter() - started}
    (ROOT / "adversary/validation.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    run()
