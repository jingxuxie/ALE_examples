import ast
import copy
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import sympy

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "authoring/sources/Qualtran/qualtran/bloqs"
sys.path.insert(0, str(ROOT / "participant/workspace"))
import checker
import target_method

spec = importlib.util.spec_from_file_location("baseline", ROOT / "participant/baseline/solve.py")
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)


def source_function(path, name, environment):
    tree = ast.parse(path.read_text())
    function = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)
    function.decorator_list = []
    module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), function], type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, str(path), "exec"), environment)
    return environment[name]


def main():
    environment = {"np": np, "sympy": sympy}
    rotation = source_function(SOURCE / "basic_gates/su2_rotation.py", "rotation_matrix", environment)
    class Rotation:
        def __init__(self, theta, phi, lambd):
            self.theta, self.phi, self.lambd, self.global_shift = theta, phi, lambd, 0
        @property
        def rotation_matrix(self):
            return rotation(self)
    environment["SU2RotationGate"] = Rotation
    original_fft = source_function(SOURCE / "qsp/fft_qsp.py", "fft_complementary_polynomial", environment)
    original_phases = source_function(SOURCE / "qsp/generalized_qsp.py", "qsp_phase_factors", environment)
    checks = 0
    rng = np.random.default_rng(550491)
    for length in (3, 9, 33, 41, 49):
        polynomial = (rng.normal(size=length) + 1j * rng.normal(size=length)) / (10 * length)
        for resolution in (128, 4096, 8192):
            expected = original_fft(polynomial, tolerance=0, num_modes=resolution)
            actual = target_method.fft_complementary_polynomial(polynomial, tolerance=0, num_modes=resolution)
            assert np.array_equal(expected, actual)
            expected_phases = original_phases(polynomial, expected)
            actual_phases = target_method.qsp_phase_factors(polynomial, actual)
            for expected_value, actual_value in zip(expected_phases, actual_phases):
                assert np.array_equal(expected_value, actual_value)
            checks += 1
    assert checker.exact_residual(np.array([0.5, 0.5]), np.array([0.5, -0.5])) == 0
    simple = np.array([0.5 + 0j, 0.5 + 0j])
    complement = np.array([0.5 + 0j, -0.5 + 0j])
    error, _ = checker.reconstructed_error(simple, complement, target_method.qsp_phase_factors(simple, complement))
    assert error < 1e-14
    checks += 2
    baseline_report = checker.evaluate(ROOT / "participant/baseline")
    assert baseline_report.get("admissible") and not baseline_report["passed"]
    candidate = baseline.candidate()
    with tempfile.TemporaryDirectory(dir=ROOT / "adversary") as temporary:
        destination = Path(temporary)
        for mutation in ("bad_certificate", "degree", "boolean", "missing"):
            malformed = copy.deepcopy(candidate)
            if mutation == "bad_certificate": malformed["H"][0][0] += 1e-5
            if mutation == "degree": malformed["P"] = malformed["P"][:12]
            if mutation == "boolean": malformed["P"][0][0] = True
            if mutation == "missing": del malformed["H"]
            (destination / "counterexample.json").write_text(json.dumps(malformed))
            assert not checker.evaluate(destination)["input_valid"]
            checks += 1
        (destination / "counterexample.json").write_text('{"P":[],"P":[],"H":[]}')
        assert not checker.evaluate(destination)["input_valid"]
        checks += 1
    data = baseline.candidate(seed=73000, degree=96)
    polynomial = checker.coefficients(data["P"])
    complementary = target_method.fft_complementary_polynomial(polynomial, tolerance=0, num_modes=8192)
    unstable_angles = target_method.qsp_phase_factors(polynomial, complementary)
    unstable_error, block_error = checker.reconstructed_error(polynomial, complementary, unstable_angles)
    higher_precision, _ = checker.reconstructed_error(polynomial, complementary, unstable_angles, digits=120)
    assert abs(unstable_error - higher_precision) < 1e-13
    reversed_complement = complementary[::-1].conj()
    stable_angles = target_method.qsp_phase_factors(polynomial, reversed_complement)
    stable_error, _ = checker.reconstructed_error(polynomial, reversed_complement, stable_angles)
    assert stable_error < 1e-10
    diagnostic = {"degree": 96, "inside_task_domain": False,
                  "completion_residual_bound": float(checker.exact_residual(polynomial, complementary)),
                  "guard_margin": target_method.phase_guard_margin(polynomial, complementary, *unstable_angles[:2]),
                  "rms_error": unstable_error, "top_block_error": block_error,
                  "120_digit_error": higher_precision, "alternate_complement_error": stable_error,
                  "demonstrates_task_solvability": False}
    (ROOT / "adversary/out_of_domain_diagnostic.json").write_text(json.dumps(diagnostic, indent=2))
    (ROOT / "adversary/selftest.json").write_text(json.dumps({"passed": True, "checks": checks + 3,
        "source_functions_bitwise_equal": True, "baseline_admissible": True,
        "independent_expansion_precision_digits": [80, 120], "exact_dyadic_validation": True}, indent=2))
    print(json.dumps({"checks": checks + 3, "baseline_score": baseline_report["core_score"], "diagnostic": diagnostic}, indent=2))


if __name__ == "__main__":
    main()
