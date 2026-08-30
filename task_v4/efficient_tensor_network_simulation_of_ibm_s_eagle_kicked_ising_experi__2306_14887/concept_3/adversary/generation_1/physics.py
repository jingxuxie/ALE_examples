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
SPEC = importlib.util.spec_from_file_location("trusted_original_checker", ROOT / "evaluator" / "evaluate.py")
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)
LIBRARY = ctypes.CDLL(str(HERE / "statevector.so"))
ARRAY = np.ctypeslib.ndpointer(dtype=np.float64, flags="C_CONTIGUOUS")
LIBRARY.evaluate.argtypes = [ARRAY, ARRAY, ctypes.c_int, ctypes.c_int, ARRAY, ARRAY]
LIBRARY.evaluate.restype = None
OLD_SCALE = np.r_[0.025, 0.025, 0.015, np.full(12, 0.005)]


def champion():
    return np.asarray(json.loads((ROOT / "champions" / "generation_1" / "pulses.json").read_text())["angles"])


def fast(angles, scenarios, gradients=False):
    angles = np.ascontiguousarray(angles, dtype=np.float64).reshape(48)
    scenarios = np.ascontiguousarray(scenarios, dtype=np.float64).reshape(-1, 27)
    scores = np.empty(len(scenarios))
    derivative = np.zeros((len(scenarios), 48))
    LIBRARY.evaluate(angles, scenarios, len(scenarios), int(gradients), scores, derivative)
    return scores, derivative


def row_to_scenario(row):
    return {"gain_a": float(row[0]), "gain_b": float(row[1]), "zz_common": float(row[2]),
            "zz_local": row[3:15].tolist(), "z_drift_radians_per_layer": row[15:].tolist()}


def exact(angles, row):
    scenario = row_to_scenario(row)
    tensor = np.full((2,) * 12, 1 / 64, dtype=np.complex128)
    for layer in range(24):
        for edge in range(layer % 2, 12, 2):
            exponent = np.pi / 4 * (1 + scenario["zz_common"] + scenario["zz_local"][edge])
            tensor = CHECKER.apply_zz(tensor, edge, (edge + 1) % 12, exponent)
        for site, group in enumerate(CHECKER.GROUPS):
            half_angle = angles[layer, group] * (1 + row[group]) / 2
            gate = np.array([[np.cos(half_angle), -1j * np.sin(half_angle)],
                             [-1j * np.sin(half_angle), np.cos(half_angle)]])
            tensor = CHECKER.apply_one(tensor, gate, site)
        for site, detuning in enumerate(row[15:]):
            gate = np.diag(np.exp(-0.5j * detuning * np.array([1.0, -1.0])))
            tensor = CHECKER.apply_one(tensor, gate, site)
    state = tensor.reshape(-1)
    population = float(abs(state[0]) ** 2 + abs(state[-1]) ** 2)
    coherence = float(2 * (np.conj(state[0]) * state[-1]).real)
    parity = float(np.vdot(state, state[::-1]).real)
    return {"fidelity": float(abs((state[0] + state[-1]) / np.sqrt(2)) ** 2),
            "norm_error": abs(float(np.vdot(state, state).real) - 1),
            "global_x_expectation": parity, "negative_parity_population": (1 - parity) / 2,
            "cat_basis_population": population, "cat_coherence": coherence,
            "cat_relative_phase_radians": float(np.angle(np.conj(state[0]) * state[-1]))}


def admissibility(row, drift_bound=0.0):
    row = np.asarray(row)
    old_valid = bool(np.all(np.abs(row[:15]) <= OLD_SCALE + 1e-15))
    return {"original_calibration_coordinates_admissible": old_valid,
            "admissible_under_original_model": old_valid and bool(np.all(row[15:] == 0)),
            "admissible_under_proposed_extension": old_valid and bool(np.max(np.abs(row[15:])) <= drift_bound + 1e-15)}


def audit():
    generator = np.random.default_rng(280887)
    rows = np.c_[generator.uniform(-1, 1, (5, 15)) * OLD_SCALE,
                 generator.uniform(-0.02, 0.02, (5, 12))]
    rows[0] = 0
    controls = champion()
    scores, derivatives = fast(controls, rows, gradients=True)
    trusted = [exact(controls, row) for row in rows]
    max_error = float(max(abs(score - result["fidelity"]) for score, result in zip(scores, trusted)))
    derivative_error = 0.0
    for coordinate in (0, 9, 22, 35, 47):
        direction = np.zeros(48)
        direction[coordinate] = 1e-6
        upper = fast(controls.reshape(-1) + direction, rows)[0]
        lower = fast(controls.reshape(-1) - direction, rows)[0]
        derivative_error = max(derivative_error, float(np.max(np.abs((upper - lower) / 2e-6 - derivatives[:, coordinate]))))
    zero_row = np.zeros(27)
    original = CHECKER.evolve(controls, row_to_scenario(zero_row))
    original_score = float(abs((original[0] + original[-1]) / np.sqrt(2)) ** 2)
    report = {"max_compiled_independent_error": max_error, "max_gradient_error": derivative_error,
              "zero_drift_original_checker_error": abs(original_score - scores[0]),
              "max_norm_error": max(result["norm_error"] for result in trusted),
              "passed": max_error < 1e-10 and derivative_error < 1e-7}
    (HERE / "simulator_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)
    assert report["passed"]


if __name__ == "__main__":
    audit()
