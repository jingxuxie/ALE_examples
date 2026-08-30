import ctypes
import importlib.util
import json
import os
from pathlib import Path

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location("trusted_static_checker", ROOT / "evaluator" / "evaluate.py")
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)
LIBRARY = ctypes.CDLL(str(HERE / "statevector.so"))
ARRAY = np.ctypeslib.ndpointer(dtype=np.float64, flags="C_CONTIGUOUS")
LIBRARY.evaluate.argtypes = [ARRAY, ARRAY, ctypes.c_int, ctypes.c_int, ARRAY, ARRAY]
LIBRARY.evaluate.restype = None
LIBRARY.error_derivatives.argtypes = [ARRAY, ARRAY, ctypes.c_int, ARRAY, ARRAY]
LIBRARY.error_derivatives.restype = None
CALIBRATION_SCALE = np.r_[0.025, 0.025, 0.015, np.full(12, 0.005)]


def champion():
    return np.asarray(json.loads((ROOT / "champions" / "generation_2" / "pulses.json").read_text())["angles"])


def fast(angles, scenarios, gradients=False):
    controls = np.ascontiguousarray(angles, dtype=np.float64).reshape(48)
    rows = np.ascontiguousarray(scenarios, dtype=np.float64).reshape(-1, 39)
    scores = np.zeros(len(rows))
    derivative = np.zeros((len(rows), 48))
    LIBRARY.evaluate(controls, rows, len(rows), int(gradients), scores, derivative)
    return scores, derivative


def static_row(scenario):
    drift = scenario["z_drift_radians_per_layer"]
    return np.r_[scenario["gain_a"], scenario["gain_b"], scenario["zz_common"], scenario["zz_local"], drift, drift]


def error_derivatives(angles, scenarios):
    controls = np.ascontiguousarray(angles, dtype=np.float64).reshape(48)
    rows = np.ascontiguousarray(scenarios, dtype=np.float64).reshape(-1, 39)
    scores = np.zeros(len(rows))
    gradients = np.zeros((len(rows), 39))
    LIBRARY.error_derivatives(controls, rows, len(rows), scores, gradients)
    return scores, gradients


def row_to_scenario(row):
    return {"gain_a": float(row[0]), "gain_b": float(row[1]), "zz_common": float(row[2]),
            "zz_local": row[3:15].tolist(), "z_drift_even_matching": row[15:27].tolist(),
            "z_drift_odd_matching": row[27:39].tolist()}


def admissibility(row):
    row = np.asarray(row)
    bounded = bool(np.all(np.isfinite(row)) and np.all(np.abs(row[:15]) <= CALIBRATION_SCALE + 1e-15)
                   and np.max(np.abs(row[15:])) <= 0.01 + 1e-15)
    return {"all_published_amplitude_bounds_respected": bounded,
            "admissible_under_current_static_model": bounded and bool(np.array_equal(row[15:27], row[27:39])),
            "admissible_under_proposed_matching_model": bounded}


def exact(angles, row):
    tensor = np.full((2,) * 12, 1 / 64, dtype=np.complex128)
    for layer in range(24):
        matching = layer % 2
        for edge in range(matching, 12, 2):
            exponent = np.pi / 4 * (1 + row[2] + row[3 + edge])
            tensor = CHECKER.apply_zz(tensor, edge, (edge + 1) % 12, exponent)
        for site, group in enumerate(CHECKER.GROUPS):
            half = angles[layer, group] * (1 + row[group]) / 2
            gate = np.array([[np.cos(half), -1j * np.sin(half)], [-1j * np.sin(half), np.cos(half)]])
            tensor = CHECKER.apply_one(tensor, gate, site)
        for site, detuning in enumerate(row[15 + 12 * matching:27 + 12 * matching]):
            gate = np.diag(np.exp(-0.5j * detuning * np.array([1.0, -1.0])))
            tensor = CHECKER.apply_one(tensor, gate, site)
    state = tensor.reshape(-1)
    population = float(abs(state[0]) ** 2 + abs(state[-1]) ** 2)
    coherence = float(2 * (np.conj(state[0]) * state[-1]).real)
    parity = float(np.vdot(state, state[::-1]).real)
    return {"fidelity": float(abs((state[0] + state[-1]) / np.sqrt(2)) ** 2),
            "norm_error": abs(float(np.vdot(state, state).real) - 1),
            "cat_basis_population": population, "cat_coherence": coherence,
            "cat_relative_phase_radians": float(np.angle(np.conj(state[0]) * state[-1])),
            "global_x_expectation": parity, "negative_parity_population": (1 - parity) / 2}


def confirm(angles, row, score, label):
    checked = exact(angles, row)
    assert abs(score - checked["fidelity"]) < 1e-10 and checked["norm_error"] < 1e-10
    return {"label": label, "scenario": row_to_scenario(row), "compiled_fidelity": float(score),
            "independent": checked, "admissibility": admissibility(row),
            "below_095": checked["fidelity"] < 0.95}


def audit():
    generator = np.random.default_rng(2887002)
    rows = np.c_[generator.uniform(-1, 1, (7, 15)) * CALIBRATION_SCALE,
                 generator.uniform(-0.01, 0.01, (7, 24))]
    rows[0] = 0
    rows[1, 27:] = rows[1, 15:27]
    controls = champion()
    scores, derivatives = fast(controls, rows, gradients=True)
    trusted = [exact(controls, row) for row in rows]
    discrepancy = float(max(abs(score - check["fidelity"]) for score, check in zip(scores, trusted)))
    gradient_error = 0.0
    for coordinate in (0, 9, 22, 35, 47):
        direction = np.zeros(48)
        direction[coordinate] = 1e-6
        upper = fast(controls.reshape(-1) + direction, rows)[0]
        lower = fast(controls.reshape(-1) - direction, rows)[0]
        gradient_error = max(gradient_error, float(np.max(np.abs((upper - lower) / 2e-6 - derivatives[:, coordinate]))))
    original_discrepancy = 0.0
    for index in (0, 1):
        row = rows[index]
        scenario = {"gain_a": row[0], "gain_b": row[1], "zz_common": row[2],
                    "zz_local": row[3:15], "z_drift_radians_per_layer": row[15:27]}
        state = CHECKER.evolve(controls, scenario)
        original_score = abs((state[0] + state[-1]) / np.sqrt(2)) ** 2
        original_discrepancy = max(original_discrepancy, float(abs(original_score - scores[index])))
    report = {"passed": discrepancy < 1e-10 and gradient_error < 1e-7 and original_discrepancy < 1e-10,
              "max_compiled_independent_error": discrepancy, "max_pulse_gradient_error": gradient_error,
              "max_equal_vector_current_checker_error": original_discrepancy,
              "max_norm_error": max(check["norm_error"] for check in trusted)}
    error_scores, error_gradients = error_derivatives(controls, rows[:2])
    error_gradient_error = 0.0
    for coordinate in (0, 1, 2, 3, 9, 14, 15, 22, 27, 38):
        direction = np.zeros((2, 39))
        direction[:, coordinate] = 1e-6
        upper = fast(controls, rows[:2] + direction)[0]
        lower = fast(controls, rows[:2] - direction)[0]
        error_gradient_error = max(error_gradient_error, float(np.max(np.abs((upper - lower) / 2e-6 - error_gradients[:, coordinate]))))
    report["max_calibration_gradient_error"] = error_gradient_error
    report["passed"] = report["passed"] and error_gradient_error < 1e-7
    (HERE / "simulator_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)
    assert report["passed"]


if __name__ == "__main__":
    audit()
