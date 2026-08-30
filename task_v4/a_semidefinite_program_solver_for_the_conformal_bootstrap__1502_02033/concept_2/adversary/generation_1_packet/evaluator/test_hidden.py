"""Private infrastructure/control tests, not fresh-agent witness attempts."""

import copy
import hashlib
import importlib.util
import json
import sys
import types
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]


def load(relative, name):
    specification = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


cases = load("adversary/cases.py", "concept2_test_cases")
checker = cases.checker
guard = cases.guard
evaluator = load("evaluator/evaluate.py", "concept2_test_evaluator")


@pytest.fixture
def negative():
    return cases.eligible_candidate()[0]


def write_document(tmp_path, document):
    path = tmp_path / "witness.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_exact_rayleigh_uses_normalized_fraction(negative):
    checked = checker.check_document(negative)
    assert checked["evidence_valid"]
    assert checked["rayleigh"] <= Fraction(-1, 10**7)
    scaled = copy.deepcopy(negative)
    scaled["vector"] = [str(Fraction(component) / 2) for component in negative["vector"]]
    assert checker.check_document(scaled)["rayleigh"] == checked["rayleigh"]


def test_recurrence_agrees_with_direct_power_evaluation(negative):
    import sympy as symbolic

    checked = checker.check_document(negative)
    point = Fraction(negative["x"])
    coordinate = symbolic.Rational(2 * point.numerator - point.denominator, point.denominator)
    matrix = checker.matrix_at(checked["coefficients"], point)
    for row, column in ((0, 0), (1, 3), (3, 2)):
        direct = sum(symbolic.Rational(negative["coefficients"][degree][row][column], negative["denominator"]) * symbolic.chebyshevt(degree, coordinate) for degree in range(len(negative["coefficients"])))
        assert matrix[row][column] == Fraction(int(direct.p), int(direct.q))


@pytest.mark.parametrize("kind", ["wrong_direction", "positive", "roundoff_depth"])
def test_insufficient_evidence_never_scores(tmp_path, negative, kind):
    if kind == "wrong_direction":
        negative["vector"] = [str(Fraction(int(entry), 5)) for entry in cases.baseline.ROTATION_NUMERATORS[:, 3]]
    elif kind == "positive":
        negative = cases.eligible_candidate(depth=-3e-4, gap=3e-4)[0]
    else:
        negative = cases.eligible_candidate(depth=1e-9)[0]
    result = evaluator.evaluate(write_document(tmp_path, negative))
    assert result["valid"]
    assert not result["evidence_valid"]
    assert not result["passed"]
    assert result["core_score"] == result["runtime_score"] == 0


@pytest.mark.parametrize("kind", ["denominator_zero", "denominator_negative", "denominator_bool", "denominator_huge", "coefficient_float", "coefficient_bool", "coefficient_huge", "trace", "asymmetry", "ragged", "too_high_degree", "trailing_zero", "zero_vector", "sparse_vector", "outside", "unreduced", "negative_denominator", "giant_fraction", "unknown_key", "commuting", "minor_failure"])
def test_invalid_constraints_rejected(tmp_path, negative, kind):
    if kind == "denominator_zero":
        negative["denominator"] = 0
    elif kind == "denominator_negative":
        negative["denominator"] = -1
    elif kind == "denominator_bool":
        negative["denominator"] = True
    elif kind == "denominator_huge":
        negative["denominator"] = 10**12 + 1
    elif kind == "coefficient_float":
        negative["coefficients"][0][0][0] = 1.0
    elif kind == "coefficient_bool":
        negative["coefficients"][0][0][0] = True
    elif kind == "coefficient_huge":
        negative["coefficients"][0][0][0] = 10**13
    elif kind == "trace":
        negative["coefficients"][0][0][0] += 1
    elif kind == "asymmetry":
        negative["coefficients"][1][0][1] += 1
    elif kind == "ragged":
        negative["coefficients"][0][0].pop()
    elif kind == "too_high_degree":
        negative["coefficients"] *= 3
    elif kind == "trailing_zero":
        negative["coefficients"][-1] = [[0] * 4 for row in range(4)]
    elif kind == "zero_vector":
        negative["vector"] = ["0"] * 4
    elif kind == "sparse_vector":
        negative["vector"] = ["1", "0", "0", "0"]
    elif kind == "outside":
        negative["x"] = "0"
    elif kind == "unreduced":
        negative["x"] = "2/4"
    elif kind == "negative_denominator":
        negative["x"] = "1/-2"
    elif kind == "giant_fraction":
        negative["x"] = "1/1000000000001"
    elif kind == "unknown_key":
        negative["execute"] = "__import__('os').system('false')"
    elif kind == "commuting":
        for matrix in negative["coefficients"]:
            for row in range(4):
                for column in range(4):
                    if row != column:
                        matrix[row][column] = 0
    else:
        negative["coefficients"][0][0][0] -= negative["denominator"] // 2
        negative["coefficients"][0][3][3] += negative["denominator"] // 2
    result = evaluator.evaluate(write_document(tmp_path, negative))
    assert not result["valid"]
    assert not result["passed"]
    assert result["core_score"] == result["worst_family_score"] == result["runtime_score"] == 0


@pytest.mark.parametrize("payload", [b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}', b'{"x":1e309}', b'{"x":1,"x":2}', b'{"x":9999999999999999999999999999999999}', b'[' * 2000 + b']' * 2000, b' ' * 65537, b'\xff'])
def test_malformed_and_overflow_inputs_fail_closed(tmp_path, payload):
    path = tmp_path / "witness.json"
    path.write_bytes(payload)
    result = evaluator.evaluate(path)
    assert not result["valid"]
    assert not result["passed"]


@pytest.mark.parametrize("kind", ["constant", "strict_coupled", "rank_deficient"])
def test_guard_accepts_psd_controls(kind):
    if kind == "constant":
        coefficients = np.zeros((3, 4, 4))
        coefficients[0] = np.eye(4) / 4.0
    elif kind == "strict_coupled":
        coefficients = cases.floating(cases.eligible_candidate(order=11, depth=-3e-4, gap=3e-4)[0])
    else:
        coefficients = cases.rank_deficient_psd()
    reports = guard.screen_all(coefficients)
    assert all(report["accepted"] for report in reports), reports


def test_narrow_rotated_quadratic_not_solved_by_single_mesh():
    coefficients, center = cases.narrow_quadratic()
    uniform = np.linalg.eigvalsh(guard.evaluate_matrices(coefficients, np.linspace(0.0, 1.0, 257)))
    assert uniform[:, 0].min() > 0
    assert np.linalg.eigvalsh(guard.evaluate_matrices(coefficients, [float(center)]))[0, 0] < -1e-7
    assert not any(report["accepted"] for report in guard.screen_all(coefficients))


def test_determinant_layer_detects_quadratic_with_coarse_mesh(monkeypatch):
    coefficients, center = cases.narrow_quadratic()
    monkeypatch.setattr(guard, "_mesh", lambda profile: np.linspace(0.0, 1.0, 17))
    reports = guard.screen_all(coefficients)
    assert all(not report["accepted"] and report["last_stage"] == "determinant_roots_and_stationary_points" for report in reports)


def test_adaptive_layer_detects_quadratic_without_determinant(monkeypatch):
    coefficients, center = cases.narrow_quadratic()
    monkeypatch.setattr(guard, "determinant_candidates", lambda coefficients: np.empty(0))
    monkeypatch.setattr(guard, "_mesh", lambda profile: np.linspace(0.0, 1.0, 17))
    assert not any(report["accepted"] for report in guard.screen_all(coefficients))


def test_guard_nonfinite_is_not_acceptance():
    coefficients = np.zeros((3, 4, 4))
    coefficients[0, 0, 0] = float("nan")
    with pytest.raises(ValueError):
        guard.screen_all(coefficients)


def test_frozen_files_match_manifest():
    manifest = json.loads((ROOT / "evaluator/frozen_manifest.json").read_text())
    assert (ROOT / "participant/workspace/guard.py").read_bytes() == (ROOT / "evaluator/_frozen_guard.py").read_bytes()
    assert hashlib.sha256((ROOT / "evaluator/_frozen_guard.py").read_bytes()).hexdigest() == manifest["guard_sha256"]
    assert hashlib.sha256((ROOT / "evaluator/exact_checker.py").read_bytes()).hexdigest() == manifest["exact_checker_sha256"]


def test_public_module_override_cannot_change_score(tmp_path, negative, monkeypatch):
    monkeypatch.setitem(sys.modules, "guard", types.SimpleNamespace(screen_all=lambda coefficients: [{"accepted": True}]))
    (tmp_path / "guard.py").write_text("raise RuntimeError('must not execute')\n")
    (tmp_path / "solution.py").write_text("raise RuntimeError('must not execute')\n")
    result = evaluator.evaluate(write_document(tmp_path, negative))
    assert result["valid"] and result["evidence_valid"]
    assert not result["passed"]
    assert result["core_score"] == 0


def test_integrity_drift_fails_closed(tmp_path, negative, monkeypatch):
    for filename in ("frozen_manifest.json", "exact_checker.py", "_frozen_guard.py"):
        content = (ROOT / "evaluator" / filename).read_bytes()
        (tmp_path / filename).write_bytes(content + (b"\n" if filename == "_frozen_guard.py" else b""))
    monkeypatch.setattr(evaluator, "PRIVATE_DIRECTORY", tmp_path)
    result = evaluator.evaluate(write_document(tmp_path, negative))
    assert not result["passed"]
    assert "integrity" not in result["reason"] or result["core_score"] == 0
    assert result["reason"].startswith("evaluator failure")


def test_scoring_plumbing_with_explicit_mock_not_a_witness(tmp_path, negative, monkeypatch):
    original = evaluator._load_private
    fake = types.SimpleNamespace(PROFILES=("first", "second", "third"), screen_all=lambda coefficients: [{"accepted": True}] * 3)
    monkeypatch.setattr(evaluator, "_load_private", lambda filename, name, digest: fake if filename == "_frozen_guard.py" else original(filename, name, digest))
    result = evaluator.evaluate(write_document(tmp_path, negative))
    assert result["valid"] and result["evidence_valid"] and result["passed"]
    assert result["core_score"] == result["worst_family_score"] == 1


def test_missing_submission_is_invalid(tmp_path):
    result = evaluator.evaluate(tmp_path / "missing.json")
    assert not result["valid"] and not result["passed"]


def test_nonregular_submission_is_invalid(tmp_path):
    result = evaluator.evaluate(tmp_path)
    assert not result["valid"] and not result["passed"]
