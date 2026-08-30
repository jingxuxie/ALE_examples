#!/usr/bin/env python3
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
HIDDEN = ROOT / "evaluator/hidden"


def load_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def independent_sparse(values):
    positions = np.flatnonzero(values)
    weights = values[positions]
    correlations = np.zeros(len(values), dtype=np.int64)
    for source in positions:
        correlations[(positions - source) % len(values)] += values[source] * weights
    return correlations


def physics_audit(values, target):
    pair_count = len(values)
    direction_count = 2 * pair_count
    expected = np.array(target["cyclic_autocorrelation"], dtype=np.int64)
    independent = independent_sparse(values)
    spectrum = np.fft.rfft(values)
    fft_values = np.fft.irfft(spectrum * spectrum.conjugate(), n=pair_count)
    assert np.array_equal(independent, expected)
    assert np.array_equal(np.rint(fft_values).astype(np.int64), independent)
    fft_error = float(np.max(np.abs(fft_values-independent)))
    assert fft_error < 1e-7
    full_values = np.tile(values, 2)
    directed = independent_sparse(full_values)
    assert np.array_equal(directed, 2 * np.tile(expected, 2))
    angular = np.concatenate(([directed[0]], directed[1:pair_count] + directed[:pair_count:-1],
                               [directed[pair_count]]))
    expected_angular = np.concatenate(([2 * expected[0]], 4 * expected[1:], [2 * expected[0]]))
    assert np.array_equal(angular, expected_angular)
    positions = np.flatnonzero(full_values)
    angles = 2 * np.pi * positions / direction_count
    cosine, sine = np.cos(angles), np.sin(angles)
    weights = full_values[positions]
    geometric = np.zeros(pair_count + 1, dtype=np.int64)
    for start in range(0, len(positions), 64):
        stop = min(start + 64, len(positions))
        dots = cosine[start:stop, None] * cosine[None, :] + sine[start:stop, None] * sine[None, :]
        bins = np.rint(np.arccos(np.clip(dots, -1, 1)) * direction_count / (2 * np.pi)).astype(np.int64)
        products = weights[start:stop, None] * weights[None, :]
        contribution = np.bincount(bins.ravel(), weights=products.ravel(), minlength=pair_count + 1)
        assert np.array_equal(contribution, contribution.astype(np.int64))
        geometric += contribution.astype(np.int64)
    assert np.array_equal(geometric, angular)
    denominator = (2 * target["energy_integer_sum"]) ** 2
    assert Fraction(int(directed.sum()), denominator) == Fraction(int(angular.sum()), denominator) == 1
    assert Fraction(int(full_values.sum()), 2 * target["energy_integer_sum"]) == 1
    assert directed[0] == directed[pair_count] == int(full_values @ full_values) == 3072
    energies = weights / (2 * target["energy_integer_sum"])
    momentum = [math.fsum(energies * cosine), math.fsum(energies * sine)]
    mass_shell_error = float(np.max(np.abs(energies ** 2 - (energies * cosine) ** 2 - (energies * sine) ** 2)))
    first_moment = float(angular @ np.cos(2 * np.pi * np.arange(pair_count + 1) / direction_count) / denominator)
    assert max(abs(value) for value in momentum) < 2e-14 and mass_shell_error < 1e-18
    assert abs(first_moment) < 2e-14
    return {"integer_lags_crosschecked": pair_count, "fft_max_absolute_roundoff": fft_error,
            "directed_bins_checked": direction_count, "geometric_angular_bins_checked": pair_count + 1,
            "nonzero_ordered_full_event_pairs": len(positions) ** 2, "exact_energy_normalization": "1",
            "exact_directional_normalization": "1", "exact_angular_normalization": "1",
            "endpoint_numerator": 3072, "full_event_denominator": denominator,
            "momentum_residual": momentum, "mass_shell_residual": mass_shell_error,
            "first_cosine_moment": first_moment, "grader_correlation_helper_used": False}


def run_audit():
    started = time.perf_counter()
    grader = load_module("staged_grader", ROOT / "evaluator/evaluate.py")
    checker = load_module("staged_public_checker", ROOT / "participant/check.py")
    baseline = load_module("staged_baseline", ROOT / "participant/baseline/generate.py")
    target_bytes = (HIDDEN / "target.json").read_bytes()
    target = json.loads(target_bytes)
    manifest = json.loads((HIDDEN / "frozen_manifest.json").read_text())
    assert hashlib.sha256(target_bytes).hexdigest() == manifest["target_sha256"]
    assert target_bytes == (ROOT / "participant/input/target.json").read_bytes()
    assert (ROOT / "evaluator/validator.py").read_bytes() == (ROOT / "participant/check.py").read_bytes()
    plant_path = HIDDEN / "planted/design.json"
    assert hashlib.sha256(plant_path.read_bytes()).hexdigest() == manifest["planted_sha256"]
    design = json.loads(plant_path.read_text())
    values = design["a"]
    checker.validate_target(target)
    checker.validate_design(design, target)
    physics = physics_audit(np.array(values, dtype=np.int64), target)
    planted_report = grader.evaluate(plant_path)
    assert planted_report["passed"] and planted_report["valid"] and planted_report["matched_lags"] == 4096
    write_json(HIDDEN / "planted_report.json", planted_report)
    records = []
    with tempfile.TemporaryDirectory(prefix="author_audit_", dir=HIDDEN) as temporary:
        temporary_path = Path(temporary)
        case_root = temporary_path / "case"
        case_root.mkdir()

        def check_case(name, content, valid, passed):
            payload = content if isinstance(content, bytes) else json.dumps(content).encode()
            (case_root / "design.json").write_bytes(payload)
            actual = grader.evaluate(case_root)
            public = checker.evaluate(case_root, target)
            for report in (actual, public):
                assert report["valid"] is valid and report["passed"] is passed, name
                assert report["core_score"] == float(passed), name
                assert report["reason"] and math.isfinite(report["runtime_seconds"]), name
                assert all(math.isfinite(report[key]) and 0 <= report[key] <= 1 for key in
                           ("core_score", "worst_family_score", "runtime_score", "resource_score")), name
            if valid:
                assert actual["squared_error"] == public["squared_error"], name
            records.append({"name": name, "ok": True})

        check_case("planted", design, True, True)
        for shift in (1, 137, 2048, 4095):
            check_case(f"rotation_{shift}", {"schema_version": 1, "a": values[shift:] + values[:shift]}, True, True)
        check_case("reflection", {"schema_version": 1, "a": values[::-1]}, True, True)
        first_one, first_two, first_zero = values.index(1), values.index(2), values.index(0)
        for name, position, replacement in (("boolean", first_zero, False), ("float", first_one, 1.0),
                                             ("negative", first_one, -1), ("range", first_two, 3),
                                             ("string", first_one, "1"), ("null", first_one, None),
                                             ("bad_counts", first_one, 0), ("nan", first_one, float("nan")),
                                             ("infinity", first_one, float("inf"))):
            corrupted = values.copy()
            corrupted[position] = replacement
            check_case(name, {"schema_version": 1, "a": corrupted}, False, False)
        for name, content in (("wrong_version", {"schema_version": 2, "a": values}),
                              ("boolean_version", {"schema_version": True, "a": values}),
                              ("short_array", {"schema_version": 1, "a": values[:-1]}),
                              ("long_array", {"schema_version": 1, "a": values + [0]}),
                              ("extra_key", {"schema_version": 1, "a": values, "score": 1}),
                              ("missing_key", {"a": values}), ("top_level_list", values),
                              ("oversize", b' ' * 131073), ("invalid_utf8", b'\xff'),
                              ("deep_json", b'[' * 2000 + b'0' + b']' * 2000),
                              ("giant_integer", b'{"schema_version":' + b'9' * 5000 + b',"a":[]}'),
                              ("duplicate_keys", b'{"a":[],"a":' + json.dumps(values).encode() + b',"schema_version":1}'),
                              ("executable_text", b'print("not JSON")'),
                              ("trailing_code", json.dumps(design).encode() + b'\nprint(1)')):
            check_case(name, content, False, False)
        corrupted = values.copy()
        corrupted[(first_one + 1) % 4096] = corrupted[first_two]
        corrupted[first_two] = 0
        check_case("adjacent_slots", {"schema_version": 1, "a": corrupted}, False, False)
        wrap_values = [0] * 4096
        wrap_values[0] = wrap_values[-1] = 1
        for position in range(2, 1022, 2):
            wrap_values[position] = 1
        for position in range(1022, 1534, 2):
            wrap_values[position] = 2
        check_case("wraparound_spacing", {"schema_version": 1, "a": wrap_values}, False, False)
        swapped = values.copy()
        swapped[first_one], swapped[first_two] = swapped[first_two], swapped[first_one]
        check_case("feasible_wrong_autocorrelation", {"schema_version": 1, "a": swapped}, True, False)
        write_json(case_root / "target.json", {"cyclic_autocorrelation": independent_sparse(np.array(swapped)).tolist()})
        check_case("submitted_target_ignored", {"schema_version": 1, "a": swapped}, True, False)
        for name in ("symlink", "directory", "fifo"):
            special = temporary_path / name
            special.mkdir()
            candidate = special / "design.json"
            if name == "symlink":
                candidate.symlink_to(plant_path)
            elif name == "directory":
                candidate.mkdir()
            else:
                os.mkfifo(candidate)
            assert not grader.evaluate(special)["valid"], name
            records.append({"name": name, "ok": True})
        linked = temporary_path / "linked_submission"
        linked.symlink_to(plant_path.parent, target_is_directory=True)
        assert not grader.evaluate(linked)["valid"]
        missing = temporary_path / "missing"
        missing.mkdir()
        assert not grader.evaluate(missing)["valid"]
        records.append({"name": "missing_and_linked_submission", "ok": True})
        write_json(case_root / "design.json", design)
        marker = temporary_path / "submitted_code_executed"
        poison = f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\nraise RuntimeError('untrusted code')\n"
        for filename in ("validator.py", "json.py", "sitecustomize.py", "evaluate.py"):
            (case_root / filename).write_text(poison)
        report_path = temporary_path / "report.json"
        completed = subprocess.run([sys.executable, "-I", str(ROOT / "evaluator/evaluate.py"), str(case_root),
                                    "--report", str(report_path)], cwd=case_root, capture_output=True,
                                   text=True, check=True, timeout=20)
        assert json.loads(completed.stdout) == json.loads(report_path.read_text())
        assert json.loads(completed.stdout)["passed"] and not marker.exists()
        protected = subprocess.run([sys.executable, "-I", str(ROOT / "evaluator/evaluate.py"), str(case_root),
                                    "--report", str(case_root / "design.json")], capture_output=True, timeout=20)
        assert protected.returncode != 0 and json.loads((case_root / "design.json").read_text()) == design
        records.append({"name": "static_only_cli_report_and_overwrite_protection", "ok": True})
    expected = target["cyclic_autocorrelation"]
    every_lag_wrong = checker.score_correlation([value + 1 for value in expected], expected)
    assert every_lag_wrong["mismatched_lags"] == 4096 and every_lag_wrong["matched_lags"] == 0
    generator = np.random.default_rng(20260828)
    selected_lags = sorted(set([0, 1, 1023, 1024, 2047, 2048, 3071, 3072, 4095]
                               + generator.choice(4096, size=24, replace=False).tolist()))
    for lag in selected_lags:
        observed = expected.copy()
        observed[lag] += 1
        report = checker.score_correlation(observed, expected)
        assert report["mismatched_lags"] == 1 and report["squared_error"] == 1 and not report["passed"]
    records.append({"name": "all_lag_mismatch_vector_and_sparse_single_lag_score_tests", "ok": True})
    trial_values = np.array(values, dtype=np.int64)
    trial_before = independent_sparse(trial_values)
    swap_pairs = [(0, 2048), (0, 1), (4095, 0), (13, 13)]
    swap_pairs += [tuple(int(value) for value in generator.integers(0, 4096, size=2)) for trial in range(12)]
    for source, destination in swap_pairs:
        delta = baseline.swap_delta(np.tile(trial_values, 2), source, destination, 4096)
        changed = trial_values.copy()
        changed[source], changed[destination] = changed[destination], changed[source]
        assert np.array_equal(delta, independent_sparse(changed) - trial_before)
    records.append({"name": "16_exact_incremental_delta_checks", "ok": True})
    for source_path in ROOT.rglob("*.py"):
        compile(source_path.read_text(), str(source_path), "exec")
    assert target_bytes == (HIDDEN / "target.json").read_bytes() == (ROOT / "participant/input/target.json").read_bytes()
    result = {"passed": True, "named_checks": len(records), "checks": records, "physics": physics,
              "single_lag_score_checks": len(selected_lags), "all_lag_mismatch_vector_size": 4096,
              "incremental_delta_checks": len(swap_pairs), "planted_report": planted_report,
              "independent_arithmetic": True, "independent_agent_review": False,
              "expensive_per_lag_recomputations": 0, "runtime_seconds": time.perf_counter() - started}
    write_json(HIDDEN / "author_audit.json", result)
    return result


if __name__ == "__main__":
    report = run_audit()
    print(json.dumps({"passed": report["passed"], "named_checks": report["named_checks"],
                      "runtime_seconds": report["runtime_seconds"]}))
