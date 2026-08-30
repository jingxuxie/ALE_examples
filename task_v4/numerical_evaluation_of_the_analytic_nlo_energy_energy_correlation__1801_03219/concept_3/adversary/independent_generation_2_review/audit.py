from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time


sys.dont_write_bytecode = True
OUTPUT = Path(__file__).resolve().parent
ROOT = OUTPUT.parents[1]
FIXTURES = OUTPUT / "fixtures"
STARTED = time.perf_counter()


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def load_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot():
    return {str(path.relative_to(ROOT)): digest(path)
            for directory in (ROOT / "participant", ROOT / "evaluator")
            for path in sorted(directory.rglob("*")) if path.is_file()}


def encode(values, version=1):
    return json.dumps({"schema_version": version, "a": values}, separators=(",", ":")).encode()


def exact_lag_sums(values):
    return [sum(weight * values[(position + lag) % len(values)]
                for position, weight in enumerate(values)) for lag in range(len(values))]


def full_histograms(values):
    full_values = values + values
    occupied = [(position, weight) for position, weight in enumerate(full_values) if weight]
    directed = [0] * len(full_values)
    angular = [0] * (len(values) + 1)
    for left_index, (left_position, left_weight) in enumerate(occupied):
        directed[0] += left_weight ** 2
        angular[0] += left_weight ** 2
        for right_position, right_weight in occupied[left_index + 1:]:
            separation = right_position - left_position
            product = left_weight * right_weight
            directed[separation] += product
            directed[len(full_values) - separation] += product
            angular[min(separation, len(full_values) - separation)] += 2 * product
    return directed, angular


before = snapshot()
manifest = json.loads((ROOT / "evaluator/hidden/frozen_manifest.json").read_text())
target = json.loads((ROOT / "evaluator/hidden/target.json").read_text())
plant_path = ROOT / "evaluator/hidden/planted/design.json"
plant_bytes = plant_path.read_bytes()
plant = json.loads(plant_bytes)
values = plant["a"]
expected = target["cyclic_autocorrelation"]
assert target["generation"] == 2
assert target["pair_count"] == 4096 and target["direction_count"] == 8192
assert digest(ROOT / "evaluator/hidden/target.json") == manifest["target_sha256"]
assert digest(ROOT / "participant/input/target.json") == manifest["target_sha256"]
assert digest(ROOT / "evaluator/validator.py") == manifest["validator_sha256"]
assert digest(ROOT / "participant/check.py") == manifest["validator_sha256"]
assert digest(plant_path) == manifest["planted_sha256"]
assert (ROOT / "participant/input/target.sha256").read_text().split()[0] == manifest["target_sha256"]
assert set(plant) == {"schema_version", "a"}
assert type(plant["schema_version"]) is int and plant["schema_version"] == 1
assert len(values) == 4096 and all(type(value) is int for value in values)
assert Counter(values) == {0: 3328, 1: 512, 2: 256}
assert sum(values) == 1024 and sum(value ** 2 for value in values) == 1536
assert all(not (values[position] and values[(position + 1) % 4096]) for position in range(4096))
assert target["counts"] == {"0": 3328, "1": 512, "2": 256}
assert target["energy_integer_sum"] == 1024 and target["min_empty_between_occupied"] == 1
assert target["allowed_values"] == [0, 1, 2] and target["schema_version"] == 1
assert target["max_submission_bytes"] == 131072 and len(plant_bytes) <= 131072
assert target["attempt_time_limit_seconds"] == 3600
assert target["lag_families"] == [[0, 1024], [1024, 2048], [2048, 3072], [3072, 4096]]
assert target["family_intervals"] == "half-open"
independent = exact_lag_sums(values)
assert independent == expected and len(expected) == 4096
assert all(type(value) is int for value in expected)
assert expected[0] == 1536 and expected[1] == expected[-1] == 0
assert sum(expected) == 1048576
assert all(expected[lag] == expected[-lag] for lag in range(4096))
directed, angular = full_histograms(values)
assert directed == [2 * expected[separation % 4096] for separation in range(8192)]
assert angular == [2 * expected[0]] + [4 * expected[lag] for lag in range(1, 4096)] + [2 * expected[0]]
assert Fraction(sum(values + values), 2048) == 1
assert Fraction(sum(directed), 4194304) == Fraction(sum(angular), 4194304) == 1
assert directed[0] == directed[4096] == angular[0] == angular[4096] == 3072
physics = {"independent_method": "dense native-integer lag sums; separate unordered full-direction pairs with doubled off-diagonal contributions",
           "grader_arithmetic_reused": False, "floating_point_used": False,
           "lags_exactly_checked": 4096, "directed_bins_exactly_checked": 8192,
           "angular_bins_exactly_checked": 4097, "full_nonzero_ordered_pairs": 1536 ** 2,
           "counts": {str(value): values.count(value) for value in (0, 1, 2)},
           "integer_energy_sum": 1024, "integer_square_sum": 1536,
           "correlation_sum": sum(expected), "lag_2048": expected[2048],
           "directed_numerator_sum": sum(directed), "angular_numerator_sum": sum(angular),
           "full_denominator": 4194304, "directed_mass": "c[d % 4096] / 2097152",
           "endpoint_mass_each": "3/4096", "interior_mass": "c[b % 4096] / 1048576",
           "energy_normalization": "1", "directed_normalization": "1", "angular_normalization": "1",
           "masslessness_and_momentum": "Exact symbolic: p_d=E_d*u_d, u_(d+4096)=-u_d, E_(d+4096)=E_d."}
save_json(OUTPUT / "physics.json", physics)
print("Independent physics: all 4096 lags, 8192 directed bins, 4097 angular bins exact.", flush=True)

grader = load_module("independent_review_grader", ROOT / "evaluator/evaluate.py")
public = load_module("independent_review_public", ROOT / "participant/check.py")
trusted, frozen_target, loaded_manifest = grader.load_context()
assert frozen_target == target and loaded_manifest == manifest
records = []
FIXTURES.mkdir()


def check_path(name, path, valid, passed):
    private_report = grader.evaluate(path)
    public_report = public.evaluate(path, target)
    comparable_private = {key: value for key, value in private_report.items()
                          if key not in ("target_sha256", "generation", "runtime_seconds")}
    comparable_public = {key: value for key, value in public_report.items() if key != "runtime_seconds"}
    assert comparable_private == comparable_public, name
    assert private_report["valid"] is valid and private_report["passed"] is passed, (name, private_report)
    assert private_report["configuration_error"] is False, name
    assert private_report["core_score"] == private_report["worst_family_score"] == float(passed), name
    assert private_report["runtime_score"] == private_report["resource_score"] == float(valid), name
    records.append({"name": name, "expected_behavior_observed": True,
                    "public_private_agree": True, "report": private_report})
    return private_report


def check_payload(name, payload, valid=False, passed=False):
    directory = FIXTURES / name
    directory.mkdir()
    (directory / "design.json").write_bytes(payload)
    return check_path(name, directory, valid, passed)


planted_report = check_path("original_planted_read_only", plant_path, True, True)
save_json(OUTPUT / "planted.private.json", planted_report)
check_payload("planted_copy", plant_bytes, True, True)
for shift in (1, 1024, 2048, 4095):
    check_payload(f"rotation_{shift}", encode(values[shift:] + values[:shift]), True, True)
check_payload("reflection", encode(values[::-1]), True, True)
compact = encode(values)
check_payload("exact_byte_cap", compact + b" " * (131072 - len(compact)), True, True)
check_payload("one_byte_over_cap", compact + b" " * (131073 - len(compact)))
check_payload("trailing_json_whitespace", compact + b" \r\n\t", True, True)
check_payload("escaped_key", compact.replace(b'"a":', b'"\\u0061":'), True, True)
positions = {value: values.index(value) for value in (0, 1, 2)}
tokens = list(map(str, values))


def replace_token(token, position):
    modified = tokens.copy()
    modified[position] = token
    return ('{"schema_version":1,"a":[' + ",".join(modified) + "]}").encode()


check_payload("integer_negative_zero", replace_token("-0", positions[0]), True, True)
for name, token, original in (
        ("boolean_false", "false", 0), ("boolean_true", "true", 1),
        ("float_zero", "0.0", 0), ("float_one", "1.0", 1), ("float_two", "2.0", 2),
        ("exponent_one", "1e0", 1), ("underflow_to_zero", "1e-9999", 0),
        ("negative_float_zero", "-0.0", 0), ("overflow_exponent", "1e9999", 0),
        ("string_entry", '"1"', 1), ("null_entry", "null", 0),
        ("object_entry", "{}", 0), ("nested_list_entry", "[]", 0),
        ("negative_integer", "-1", 1), ("out_of_range_integer", "3", 2),
        ("nan_constant", "NaN", 0), ("positive_infinity", "Infinity", 0),
        ("negative_infinity", "-Infinity", 0), ("leading_zero", "00", 0),
        ("leading_plus", "+0", 0), ("twelve_digit_integer", "9" * 12, 0),
        ("thirteen_digit_integer", "9" * 13, 0), ("giant_integer", "9" * 5000, 0)):
    check_payload(name, replace_token(token, positions[original]))
for name, version in (("boolean_version", True), ("float_version", 1.0), ("wrong_version", 2),
                      ("string_version", "1"), ("null_version", None)):
    check_payload(name, encode(values, version))
for name, payload in (
        ("short_array", encode(values[:-1])), ("long_array", encode(values + [0])),
        ("wrong_counts", replace_token("0", positions[1])),
        ("array_is_object", b'{"schema_version":1,"a":{}}'),
        ("missing_version", json.dumps({"a": values}).encode()),
        ("missing_array", b'{"schema_version":1}'), ("top_level_array", b'[]'),
        ("top_level_null", b'null'), ("top_level_integer", b'1'),
        ("extra_key", compact[:-1] + b',"core_score":1}'),
        ("duplicate_array", compact[:-1] + b',"a":[]}'),
        ("duplicate_version", compact[:-1] + b',"schema_version":1}'),
        ("escaped_duplicate_array", compact[:-1] + b',"\\u0061":[]}'),
        ("trailing_json_object", compact + b'{}'), ("trailing_code", compact + b'\nprint(1)'),
        ("trailing_nul", compact + b'\x00'), ("comment", b'/*comment*/' + compact),
        ("invalid_utf8", b'\xff'), ("utf8_bom", b'\xef\xbb\xbf' + compact),
        ("empty_file", b''), ("deep_nesting", b'[' * 3000 + b'0' + b']' * 3000),
        ("unpaired_surrogate_key", compact[:-1] + b',"\\ud800":0}')):
    check_payload(name, payload)

adjacent = values.copy()
adjacent[(positions[1] + 1) % 4096], adjacent[positions[2]] = adjacent[positions[2]], 0
check_payload("interior_adjacency", encode(adjacent))
wrap = [0] * 4096
wrap[0] = wrap[-1] = 1
for position in range(2, 1022, 2):
    wrap[position] = 1
for position in range(1022, 1534, 2):
    wrap[position] = 2
assert Counter(wrap) == Counter(values)
check_payload("wraparound_adjacency", encode(wrap))
swapped = values.copy()
swapped[positions[1]], swapped[positions[2]] = swapped[positions[2]], swapped[positions[1]]
mutant_report = check_payload("count_spacing_preserving_label_swap", encode(swapped), True, False)
mutant_correlations = exact_lag_sums(swapped)
differences = [actual - wanted for actual, wanted in zip(mutant_correlations, expected)]
assert mutant_report["l1_error"] == sum(map(abs, differences))
assert mutant_report["squared_error"] == sum(value ** 2 for value in differences)
mutant_directed, mutant_angular = full_histograms(swapped)
folded_distance = Fraction(sum(abs(actual - wanted) for actual, wanted in zip(mutant_angular, angular)), 4194304)
assert folded_distance == Fraction(sum(map(abs, differences)), 1048576)
assert mutant_report["eec_l1_error"] == float(folded_distance)

for name in ("file_symlink", "directory_instead_of_file", "fifo", "missing_file", "symlink_loop"):
    directory = FIXTURES / name
    directory.mkdir()
    candidate = directory / "design.json"
    if name == "file_symlink":
        candidate.symlink_to(FIXTURES / "planted_copy/design.json")
    elif name == "directory_instead_of_file":
        candidate.mkdir()
    elif name == "fifo":
        os.mkfifo(candidate)
    elif name == "symlink_loop":
        candidate.symlink_to("design.json")
    check_path(name, directory, False, False)
linked_directory = FIXTURES / "directory_symlink"
linked_directory.symlink_to(FIXTURES / "planted_copy", target_is_directory=True)
check_path("directory_symlink", linked_directory, False, False)
wrong_name = FIXTURES / "wrong_name.json"
wrong_name.write_bytes(compact)
check_path("wrong_filename", wrong_name, False, False)
check_path("missing_submission", FIXTURES / "not_created", False, False)

decoy = FIXTURES / "submitted_helpers_ignored"
decoy.mkdir()
(decoy / "design.json").write_bytes(encode(swapped))
save_json(decoy / "target.json", {"cyclic_autocorrelation": mutant_correlations})
for name in ("validator.py", "evaluate.py", "check.py", "json.py", "sitecustomize.py", "design.py"):
    (decoy / name).write_text("raise RuntimeError('submitted helper executed')\n")
check_path("submitted_target_and_helpers_ignored", decoy, True, False)
save_json(OUTPUT / "artifact_probes.json", records)
print(f"Artifact probes: {len(records)} public/private comparisons agree.", flush=True)

family_names = [f"lags_{start}_{start + 1023}" for start in range(0, 4096, 1024)]
score_checks = 0
for lag in range(4096):
    for change in (-1, 1):
        changed = expected.copy()
        changed[lag] += change
        report = trusted.score_correlation(changed, expected)
        assert report["passed"] is False and report["core_score"] == report["worst_family_score"] == 0
        assert report["matched_lags"] == 4095 and report["mismatched_lags"] == 1
        assert report["l1_error"] == report["squared_error"] == report["max_abs_error"] == 1
        assert report["eec_l1_error"] == 1 / 1048576
        assert report["family_scores"] == {name: float(index != lag // 1024) for index, name in enumerate(family_names)}
        score_checks += 1
all_wrong = trusted.score_correlation([value + 1 for value in expected], expected)
assert all_wrong["matched_lags"] == 0 and all_wrong["mismatched_lags"] == 4096
assert all(score == 0 for score in all_wrong["family_scores"].values())
print(f"Exact scoring probes: {score_checks} single-lag +/-1 changes rejected.", flush=True)

cli_records = []


def run_cli(name, driver, submission, report_path=None):
    command = [sys.executable, "-I", "-B", str(ROOT / driver), str(submission)]
    if report_path is not None:
        command += ["--report", str(report_path)]
    completed = subprocess.run(command, cwd=decoy, capture_output=True, text=True, timeout=10)
    try:
        output_report = json.loads(completed.stdout)
    except ValueError:
        output_report = None
    record = {"name": name, "driver": driver, "returncode": completed.returncode,
              "stdout_report": output_report, "stderr": completed.stderr,
              "report_file_exists": report_path.exists() if report_path is not None else None}
    cli_records.append(record)
    return record


findings = []
for driver, label in (("evaluator/evaluate.py", "private"), ("participant/check.py", "public")):
    normal_report = OUTPUT / f"planted.{label}.cli.json"
    normal = run_cli(f"{label}_planted", driver, FIXTURES / "planted_copy", normal_report)
    assert normal["returncode"] == 0 and normal["stdout_report"]["passed"] is True
    assert json.loads(normal_report.read_text()) == normal["stdout_report"]
    ignored = run_cli(f"{label}_helpers_ignored", driver, decoy)
    assert ignored["returncode"] == 0 and ignored["stdout_report"]["valid"] is True
    assert ignored["stdout_report"]["passed"] is False
    rejected = run_cli(f"{label}_ordinary_invalid", driver, FIXTURES / "boolean_false")
    assert rejected["returncode"] == 0 and rejected["stdout_report"]["valid"] is False
    loop_without_report = run_cli(f"{label}_loop_without_report", driver, FIXTURES / "symlink_loop")
    assert loop_without_report["returncode"] == 0 and loop_without_report["stdout_report"]["valid"] is False
    loop_with_report = run_cli(f"{label}_loop_with_report", driver, FIXTURES / "symlink_loop", OUTPUT / f"loop.{label}.json")
    protected = run_cli(f"{label}_direct_overwrite_guard", driver, FIXTURES / "planted_copy", FIXTURES / "planted_copy/design.json")
    assert protected["returncode"] == 2 and (FIXTURES / "planted_copy/design.json").read_bytes() == plant_bytes
    hardlink_directory = FIXTURES / f"hardlink_report_{label}"
    hardlink_directory.mkdir()
    hardlink_design = hardlink_directory / "design.json"
    hardlink_design.write_bytes(compact)
    hardlink_report = hardlink_directory / "report.json"
    os.link(hardlink_design, hardlink_report)
    hardlink = run_cli(f"{label}_hardlink_report_alias", driver, hardlink_directory, hardlink_report)
    hardlink["artifact_overwritten"] = hardlink_design.read_bytes() != compact
    assert loop_with_report["returncode"] == 1 and loop_with_report["stdout_report"] is None
    assert "RuntimeError: Symlink loop" in loop_with_report["stderr"]
    assert hardlink["returncode"] == 0 and hardlink["stdout_report"]["passed"] is True
    assert hardlink["artifact_overwritten"] is True

findings.append({"id": "CLI_SYMLINK_LOOP_REPORT", "severity": "low", "blocking": False,
                 "locations": ["evaluator/evaluate.py:55", "participant/check.py:162"],
                 "summary": "With --report, a self-referential design.json symlink raises uncaught RuntimeError in Path.resolve before artifact validation; exit 1, no failure JSON. Without --report it rejects normally.",
                 "impact": "Ordinary-invalid reporting robustness discrepancy, not an acceptance or exactness bypass. Main should treat nonzero/missing report as failure.",
                 "recommendation": "Catch path-resolution failures and emit ordinary invalid-artifact JSON; never accept a failed evaluator process."})
findings.append({"id": "CLI_HARDLINK_REPORT_ALIAS", "severity": "low", "blocking": False,
                 "locations": ["evaluator/evaluate.py:55", "evaluator/evaluate.py:61", "participant/check.py:162", "participant/check.py:167"],
                 "summary": "The report overwrite guard compares resolved path strings, not file identity. A report path hardlinked to design.json overwrites that artifact after successful grading.",
                 "impact": "Requires control of the report destination or its inode. It does not turn a mismatching artifact into an exact witness; output-path integrity concern only.",
                 "recommendation": "Keep reports in trusted separate directories and reject same-inode report/artifact aliases."})
save_json(OUTPUT / "cli_probes.json", cli_records)
after = snapshot()
assert before == after, "Existing participant/evaluator files changed during review"
save_json(OUTPUT / "protected_file_hashes.json", {"unchanged": True, "files": before})
result = {"schema_version": 1, "concept": "concept_3", "generation": 2,
          "evaluator_valid": True, "blocking_concerns": [], "verdict": "valid_with_nonblocking_cli_robustness_findings",
          "independent_agent_review": True, "author_staging_audit_reused_as_evidence": False,
          "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
          "target_sha256": manifest["target_sha256"], "validator_sha256": manifest["validator_sha256"],
          "planted_sha256": manifest["planted_sha256"], "frozen_at_utc": manifest["frozen_at_utc"],
          "physics": physics, "planted_report": planted_report,
          "validation": {"public_private_source_identical": True, "public_private_target_identical": True,
                         "artifact_probe_count": len(records), "artifact_probes_all_expected": True,
                         "public_private_report_discrepancies": 0, "cli_probe_count": len(cli_records),
                         "single_lag_plus_minus_one_checks": score_checks, "all_lag_mismatch_check": True,
                         "exact_eec_l1_diagnostic_crosscheck": True,
                         "structural_counts_spacing_constraints_exact": True,
                         "false_acceptance_or_tolerance_bypass_found": False,
                         "unknown_acceptance_constraints_found": [], "task_infeasibility_evidence_found": False,
                         "integer_negative_zero": "Accepted as JSON integer value zero; harmless semantic normalization, not a numeric tolerance."},
          "findings": findings,
          "limitations": ["Hardness, tournament outcomes, and the one-hour external attempt budget are not independently assessed here.",
                          "Evaluator/private-target/report-directory isolation must be enforced by the main runner; same-user permissions are not isolation.",
                          "Frozen hashes and generation provenance were checked, but pre-attempt chronological integrity is not independently established from attempts.",
                          "No race-condition stress test or unbounded fuzzing was performed; report-path findings are bounded local reproductions."],
          "scope": {"active_attempts_read_or_interacted_with": False, "attempts_or_champions_read": False,
                    "subagents_launched": 0, "web_research_performed": False, "solver_runs": 0,
                    "author_staging_code_executed": False, "existing_participant_evaluator_hashes_unchanged": True,
                    "writes_confined_to": str(OUTPUT.relative_to(ROOT)),
                    "python_bytecode_writes_disabled": True},
          "evidence": ["audit.py", "physics.json", "planted.private.json", "artifact_probes.json", "cli_probes.json", "protected_file_hashes.json"],
          "runtime_seconds": time.perf_counter() - STARTED}
save_json(OUTPUT / "result.json", result)
print(json.dumps({"evaluator_valid": True, "blocking_concerns": [], "artifact_probes": len(records),
                  "single_lag_probes": score_checks, "cli_probes": len(cli_records),
                  "nonblocking_findings": len(findings), "runtime_seconds": result["runtime_seconds"]}), flush=True)
