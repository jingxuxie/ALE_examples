#!/usr/bin/env python3
from collections import Counter
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
HIDDEN = ROOT / "evaluator" / "hidden"


def load_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def dense_correlation(values):
    return [sum(values[slot] * values[(slot + lag) % len(values)] for slot in range(len(values)))
            for lag in range(len(values))]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def independent_physics(values, target):
    assert Counter(values) == {0: 416, 1: 64, 2: 32}
    assert all(not (values[slot] and values[(slot + 1) % 512]) for slot in range(512))
    assert dense_correlation(values) == target
    full_values = values + values
    occupied = [(direction, weight) for direction, weight in enumerate(full_values) if weight]
    trigonometry = [(math.cos(2 * math.pi * direction / 1024),
                     math.sin(2 * math.pi * direction / 1024)) for direction in range(1024)]
    directional = [0] * 1024
    angular = [0] * 513
    geometric = [0] * 513
    for source, source_weight in occupied:
        for destination, destination_weight in occupied:
            numerator = source_weight * destination_weight
            lag = (destination - source) % 1024
            directional[lag] += numerator
            angular[min(lag, 1024 - lag)] += numerator
            dot_product = (trigonometry[source][0] * trigonometry[destination][0]
                           + trigonometry[source][1] * trigonometry[destination][1])
            angle = math.acos(max(-1.0, min(1.0, dot_product)))
            angular_bin = round(angle * 512 / math.pi)
            geometric[angular_bin] += numerator
    expected_directional = [2 * target[lag % 512] for lag in range(1024)]
    expected_angular = [2 * target[0]] + [4 * target[lag % 512] for lag in range(1, 512)] + [2 * target[0]]
    assert directional == expected_directional
    assert angular == expected_angular == geometric
    assert sum(Fraction(value, 65536) for value in directional) == 1
    assert sum(Fraction(value, 65536) for value in angular) == 1
    assert sum(Fraction(value, 256) for value in full_values) == 1
    assert directional[0] == directional[512] == sum(value * value for value in full_values) == 384
    momentum = [math.fsum(full_values[direction] * trigonometry[direction][component] / 256
                          for direction in range(1024)) for component in (0, 1)]
    mass_shell_error = max(abs((weight / 256) ** 2
                              - (weight * trigonometry[direction][0] / 256) ** 2
                              - (weight * trigonometry[direction][1] / 256) ** 2)
                          for direction, weight in occupied)
    first_cosine_moment = math.fsum(angular[angle_bin] * math.cos(2 * math.pi * angle_bin / 1024)
                                   / 65536 for angle_bin in range(513))
    assert max(abs(value) for value in momentum) < 2e-14
    assert mass_shell_error < 1e-18
    assert abs(first_cosine_moment) < 2e-14
    spectrum = np.fft.fft(np.array(target, dtype=np.float64))
    assert np.max(np.abs(spectrum.imag)) < 1e-8 and np.min(spectrum.real) > -1e-8
    return {"directed_bins_checked": 1024, "angular_bins_checked": 513,
            "ordered_nonzero_pairs_checked": len(occupied) ** 2,
            "directional_rational_normalization": "1", "angular_rational_normalization": "1",
            "energy_rational_normalization": "1", "self_and_antipodal_numerators": 384,
            "common_full_event_denominator": 65536, "momentum_residual": momentum,
            "max_mass_shell_residual": mass_shell_error, "first_cosine_moment": first_cosine_moment,
            "minimum_fourier_power": float(np.min(spectrum.real)),
            "uses_grader_autocorrelation_helper": False}


def run_tests():
    started = time.perf_counter()
    grader = load_module("trusted_eec_grader", ROOT / "evaluator" / "evaluate.py")
    public = load_module("public_eec_checker", ROOT / "participant" / "check.py")
    baseline = load_module("public_eec_baseline", ROOT / "participant" / "baseline" / "generate.py")
    manifest = json.loads((HIDDEN / "frozen_manifest.json").read_text())
    target_payload = (HIDDEN / "target.json").read_bytes()
    assert hashlib.sha256(target_payload).hexdigest() == manifest["target_sha256"]
    assert target_payload == (ROOT / "participant" / "input" / "target.json").read_bytes()
    plant_path = HIDDEN / "planted" / "design.json"
    assert hashlib.sha256(plant_path.read_bytes()).hexdigest() == manifest["planted_sha256"]
    design = json.loads(plant_path.read_text())
    values = design["a"]
    target = json.loads(target_payload)["cyclic_autocorrelation"]
    physics = independent_physics(values, target)
    planted_report = grader.evaluate(plant_path.parent)
    assert planted_report["valid"] and planted_report["passed"] and planted_report["core_score"] == 1.0
    write_json(HIDDEN / "planted_report.json", planted_report)
    records = []
    with tempfile.TemporaryDirectory(prefix="author_checks_", dir=HIDDEN) as temporary:
        temporary_path = Path(temporary)
        case_root = temporary_path / "case"
        case_root.mkdir()

        def check_case(name, payload, expected_valid, expected_passed):
            artifact = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
            (case_root / "design.json").write_bytes(artifact)
            actual = grader.evaluate(case_root)
            local = public.evaluate(case_root)
            for checked in (actual, local):
                assert checked["valid"] is expected_valid, name
                assert checked["passed"] is expected_passed, name
                assert checked["core_score"] == float(expected_passed), name
                assert isinstance(checked["reason"], str) and checked["reason"], name
                for metric in ("core_score", "worst_family_score", "runtime_score", "resource_score"):
                    assert math.isfinite(checked[metric]) and 0 <= checked[metric] <= 1, name
                assert math.isfinite(checked["runtime_seconds"]) and checked["runtime_seconds"] >= 0, name
            if expected_valid:
                assert actual["squared_error"] == local["squared_error"], name
                assert actual["matched_lags"] == local["matched_lags"], name
            records.append({"name": name, "expected_valid": expected_valid,
                            "expected_passed": expected_passed, "ok": True})

        check_case("planted", design, True, True)
        for shift in (1, 37, 256, 511):
            check_case(f"rotation_{shift}", {"schema_version": 1, "a": values[shift:] + values[:shift]}, True, True)
        check_case("reflection", {"schema_version": 1, "a": list(reversed(values))}, True, True)
        first_one = values.index(1)
        first_two = values.index(2)
        first_zero = values.index(0)
        for name, position, replacement in (("boolean", first_zero, False), ("float", first_one, 1.0),
                                             ("negative", first_one, -1), ("too_large", first_two, 3),
                                             ("string", first_one, "1"), ("null", first_one, None),
                                             ("bad_counts", first_one, 0), ("nan", first_one, float("nan")),
                                             ("infinity", first_one, float("inf"))):
            corrupted = values.copy()
            corrupted[position] = replacement
            check_case(name, {"schema_version": 1, "a": corrupted}, False, False)
        check_case("version_boolean", {"schema_version": True, "a": values}, False, False)
        check_case("version_float", {"schema_version": 1.0, "a": values}, False, False)
        check_case("version_unknown", {"schema_version": 2, "a": values}, False, False)
        check_case("short_array", {"schema_version": 1, "a": values[:-1]}, False, False)
        check_case("long_array", {"schema_version": 1, "a": values + [0]}, False, False)
        check_case("missing_key", {"a": values}, False, False)
        check_case("extra_key", {"schema_version": 1, "a": values, "claimed_score": 1}, False, False)
        check_case("zero_event", {"schema_version": 1, "a": [0] * 512}, False, False)
        check_case("top_level_list", values, False, False)
        check_case("duplicate_keys", b'{"a":[],"a":' + json.dumps(values).encode() + b',"schema_version":1}', False, False)
        check_case("oversized_integer", b'{"schema_version":' + b'9' * 6000 + b',"a":[]}', False, False)
        check_case("too_deep", b'[' * 2000 + b'0' + b']' * 2000, False, False)
        check_case("invalid_utf8", b'\xff', False, False)
        check_case("oversized_file", b' ' * 16385, False, False)
        check_case("python_instead_of_json", b'print("not a design")', False, False)
        check_case("pickle_instead_of_json", b'\x80\x04not-json', False, False)
        check_case("trailing_code", json.dumps(design).encode() + b'\nprint(1)', False, False)
        corrupted = values.copy()
        corrupted[(first_one + 1) % 512] = corrupted[first_two]
        corrupted[first_two] = 0
        check_case("adjacent_occupied", {"schema_version": 1, "a": corrupted}, False, False)
        wrap_values = [0] * 512
        wrap_values[0] = wrap_values[511] = 1
        for position in range(2, 126, 2):
            wrap_values[position] = 1
        for position in range(126, 190, 2):
            wrap_values[position] = 2
        check_case("wraparound_spacing", {"schema_version": 1, "a": wrap_values}, False, False)
        swapped = values.copy()
        swapped[first_one], swapped[first_two] = swapped[first_two], swapped[first_one]
        assert dense_correlation(swapped) != target
        check_case("feasible_wrong_correlation", {"schema_version": 1, "a": swapped}, True, False)
        wrong_submission = {"schema_version": 1, "a": swapped}
        fake_target = json.loads(target_payload)
        fake_target["cyclic_autocorrelation"] = dense_correlation(swapped)
        write_json(case_root / "target.json", fake_target)
        check_case("submitted_target_ignored", wrong_submission, True, False)
        original_loader = grader.load_target
        try:
            for lag in range(512):
                altered_target = target.copy()
                altered_target[lag] += 1
                grader.load_target = lambda expected=altered_target: (expected, manifest["target_sha256"])
                result = grader.evaluate(plant_path)
                assert result["valid"] and not result["passed"] and result["matched_lags"] == 511
        finally:
            grader.load_target = original_loader
        records.append({"name": "all_512_lags_individually_enforced_in_memory", "ok": True})
        missing = temporary_path / "missing"
        missing.mkdir()
        assert not grader.evaluate(missing)["valid"]
        for name in ("symlink_file", "directory_file", "fifo_file"):
            special_root = temporary_path / name
            special_root.mkdir()
            special_file = special_root / "design.json"
            if name == "symlink_file":
                special_file.symlink_to(plant_path)
            elif name == "directory_file":
                special_file.mkdir()
            else:
                os.mkfifo(special_file)
            assert not grader.evaluate(special_root)["valid"], name
            assert not public.evaluate(special_root)["valid"], name
            records.append({"name": name, "ok": True})
        linked_directory = temporary_path / "linked_directory"
        linked_directory.symlink_to(plant_path.parent, target_is_directory=True)
        assert not grader.evaluate(linked_directory)["valid"]
        records.append({"name": "missing_and_symlink_directory", "ok": True})
        write_json(case_root / "design.json", design)
        poison_marker = temporary_path / "untrusted_code_was_executed"
        poison = f"from pathlib import Path\nPath({str(poison_marker)!r}).write_text('executed')\nraise RuntimeError('untrusted code executed')\n"
        for filename in ("evaluate.py", "json.py", "sitecustomize.py", "solution.py"):
            (case_root / filename).write_text(poison)
        cli_report_path = temporary_path / "cli_report.json"
        completed = subprocess.run([sys.executable, "-I", str(ROOT / "evaluator" / "evaluate.py"),
                                    str(case_root), "--report", str(cli_report_path)], cwd=case_root,
                                   capture_output=True, text=True, timeout=15, check=True)
        cli_report = json.loads(completed.stdout)
        assert cli_report == json.loads(cli_report_path.read_text()) and cli_report["passed"]
        assert not poison_marker.exists()
        records.append({"name": "cli_report_and_untrusted_code_nonexecution", "ok": True})
        protected = subprocess.run([sys.executable, "-I", str(ROOT / "evaluator" / "evaluate.py"),
                                    str(case_root), "--report", str(case_root / "design.json")],
                                   capture_output=True, text=True, timeout=15)
        assert protected.returncode != 0 and json.loads((case_root / "design.json").read_text()) == design
        records.append({"name": "report_cannot_overwrite_design", "ok": True})
    indices = np.arange(512)
    plus_indices = (indices[:, None] + indices[None, :]) % 512
    minus_indices = (indices[:, None] - indices[None, :]) % 512
    generator = np.random.default_rng(91827)
    for trial in range(32):
        trial_values = generator.integers(0, 3, size=512, dtype=np.int64)
        source = 0 if trial < 2 else int(generator.integers(512))
        destination = (256 if trial == 0 else 511) if trial < 2 else int(generator.integers(512))
        delta = baseline.swap_delta(trial_values, source, destination, plus_indices, minus_indices)
        before = np.array(dense_correlation(trial_values.tolist()), dtype=np.int64)
        trial_values[source], trial_values[destination] = trial_values[destination], trial_values[source]
        after = np.array(dense_correlation(trial_values.tolist()), dtype=np.int64)
        assert np.array_equal(delta, after - before)
    records.append({"name": "32_independent_incremental_delta_tests_including_half_period", "ok": True})
    assert (HIDDEN / "target.json").read_bytes() == target_payload
    assert (ROOT / "participant" / "input" / "target.json").read_bytes() == target_payload
    public_json_files = list((ROOT / "participant").rglob("*.json"))
    for public_file in public_json_files:
        content = json.loads(public_file.read_text())
        if isinstance(content, dict) and "a" in content:
            assert content["a"] != values, "planted array copied into participant bundle"
    for source_path in ROOT.rglob("*.py"):
        compile(source_path.read_text(), str(source_path), "exec")
    result = {"audit_type": "independent arithmetic implementation plus static-artifact adversarial tests",
              "independent_agent_review": False, "passed": True, "checks": records,
              "named_checks": len(records), "all_lags_enforcement_checks": 512,
              "incremental_delta_checks": 32, "physics": physics,
              "target_sha256": manifest["target_sha256"], "planted_report": planted_report,
              "runtime_seconds": time.perf_counter() - started}
    write_json(HIDDEN / "author_audit.json", result)
    return result


if __name__ == "__main__":
    summary = run_tests()
    print(json.dumps({"passed": summary["passed"], "named_checks": summary["named_checks"],
                      "all_lags_enforcement_checks": summary["all_lags_enforcement_checks"],
                      "runtime_seconds": summary["runtime_seconds"]}))
