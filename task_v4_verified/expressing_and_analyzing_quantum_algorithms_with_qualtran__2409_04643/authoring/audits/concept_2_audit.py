"""Independent generation-time audit using saved fixtures, never active attempts."""

import ast
import copy
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
import time
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True

import mpmath as mp
import numpy as np


TASK_ROOT = Path(__file__).resolve().parents[2]
CONCEPT_ROOT = TASK_ROOT / "concept_2"
SOURCE_ROOT = TASK_ROOT / "authoring/sources/Qualtran"
REPORT_PATH = Path(__file__).resolve().with_suffix(".json")
PINNED_COMMIT = "096a2d009059faee0cfae462c3d59cb055300eb9"
CONFIGURATIONS = [(resolution, gauge) for resolution in (4096, 8192, 16384) for gauge in (0, 1)]
SOURCE_FILES = (
    "qualtran/bloqs/basic_gates/su2_rotation.py",
    "qualtran/bloqs/qsp/fft_qsp.py",
    "qualtran/bloqs/qsp/generalized_qsp.py",
)
SOURCE_FIXTURES = (
    "participant/baseline",
    *(f"adversary/compact_stress/degree_{degree}" for degree in range(8, 13)),
    "champions/generation_1",
    "champions/generation_2",
)
REPLAY_FIXTURES = (
    ("baseline", "participant/baseline", None, "evaluator/hidden/baseline_score.json"),
    (
        "saved_degree12",
        "adversary/second_champion_stress/degree_12_seed_639405",
        None,
        "adversary/second_champion_stress/degree_12_seed_639405/score.json",
    ),
    ("generation1", "champions/generation_1", 1, "champions/generation_1/validation_report.json"),
    ("generation2", "champions/generation_2", 2, "champions/generation_2/report.json"),
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def relative(path):
    return str(path.relative_to(TASK_ROOT))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def load_fixture(checker, directory):
    data = json.loads((CONCEPT_ROOT / directory / "counterexample.json").read_text())
    return checker.coefficients(data["P"]), checker.coefficients(data["H"])


def transformed_polynomial(polynomial, gauge):
    transformed = polynomial.copy()
    if gauge:
        transformed *= np.exp(1j * (0.3125 + 0.2718281828459045 * np.arange(len(polynomial))))
    return transformed


def frozen_assets():
    summaries = []
    paths = set()
    current_method = (CONCEPT_ROOT / "evaluator/hidden/target_method.py").read_bytes()
    for generation in (1, 2, 3):
        manifest_path = CONCEPT_ROOT / f"adversary/generation_{generation}_freeze.json"
        manifest = json.loads(manifest_path.read_text())
        root = CONCEPT_ROOT if generation == 3 else CONCEPT_ROOT / f"adversary/generations/generation_{generation}"
        mismatches = [name for name, expected in manifest["sha256"].items() if digest(root / name) != expected]
        check(not mismatches, f"Generation {generation} frozen hash mismatch: {mismatches}")
        check((root / "evaluator/hidden/target_method.py").read_bytes() == current_method,
              f"Generation {generation} target method differs from current extraction")
        check((root / "participant/workspace/checker.py").read_bytes()
              == (root / "evaluator/hidden/checker.py").read_bytes(),
              f"Generation {generation} public/hidden checker mismatch")
        paths.add(manifest_path)
        paths.update(root / name for name in manifest["sha256"])
        summaries.append({"generation": generation, "files_checked": len(manifest["sha256"]), "mismatches": mismatches})
    return summaries, paths


def rational_residual(first, second, target=Fraction(1)):
    arrays = [[(Fraction(float(value.real)), Fraction(float(value.imag))) for value in array]
              for array in (first, second)]
    result = Fraction(0)
    for lag in range(max(map(len, arrays))):
        real_sum = Fraction(0)
        imag_sum = Fraction(0)
        for array in arrays:
            for index in range(len(array) - lag):
                upper_real, upper_imag = array[index + lag]
                lower_real, lower_imag = array[index]
                real_sum += upper_real * lower_real + upper_imag * lower_imag
                imag_sum += upper_imag * lower_real - upper_real * lower_imag
        result += abs(real_sum - target) if lag == 0 else 2 * (abs(real_sum) + abs(imag_sum))
    return result


class TrackingNumpy:
    def __init__(self):
        self.branch_hits = 0
        self.branch_checks = 0

    def __getattr__(self, name):
        return getattr(np, name)

    def isclose(self, *arguments, **keywords):
        result = np.isclose(*arguments, **keywords)
        self.branch_checks += 1
        self.branch_hits += int(bool(result))
        return result


def upstream_functions():
    tracking = TrackingNumpy()
    environment = {"np": tracking, "sympy": SimpleNamespace(Expr=type("SymbolicExpression", (), {}))}

    def extract(filename, name):
        path = SOURCE_ROOT / filename
        tree = ast.parse(path.read_text())
        function = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)
        function.decorator_list = []
        module = ast.Module(body=[
            ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), function
        ], type_ignores=[])
        exec(compile(ast.fix_missing_locations(module), str(path), "exec"), environment)
        return environment[name]

    rotation = extract(SOURCE_FILES[0], "rotation_matrix")

    class Rotation:
        def __init__(self, theta, phi, lambd):
            self.theta, self.phi, self.lambd, self.global_shift = theta, phi, lambd, 0

        @property
        def rotation_matrix(self):
            return rotation(self)

    environment["SU2RotationGate"] = Rotation
    fft = extract(SOURCE_FILES[1], "fft_complementary_polynomial")
    phases = extract(SOURCE_FILES[2], "qsp_phase_factors")
    return tracking, Rotation, fft, phases


def audit_source_and_certificates(checker, method):
    tracking, rotation_class, upstream_fft, upstream_phases = upstream_functions()
    source_checks = 0
    certificate_checks = 0
    minimum_margin = float("inf")
    records = []
    for directory in SOURCE_FIXTURES:
        polynomial, certificate = load_fixture(checker, directory)
        contraction = rational_residual(polynomial, certificate, Fraction(16, 25))
        check(contraction == checker.exact_residual(polynomial, certificate, Fraction(16, 25)),
              f"Independent contraction arithmetic disagrees: {directory}")
        check(contraction <= Fraction(1, 10**12), f"Saved contraction certificate invalid: {directory}")
        certificate_checks += 1
        for resolution, gauge in CONFIGURATIONS:
            transformed = transformed_polynomial(polynomial, gauge)
            expected = upstream_fft(transformed, tolerance=0, num_modes=resolution)
            actual = method.fft_complementary_polynomial(transformed, tolerance=0, num_modes=resolution)
            check(np.array_equal(expected, actual), f"Upstream FFT mismatch: {directory}, {resolution}, {gauge}")
            expected_angles = upstream_phases(transformed, expected)
            actual_angles = method.qsp_phase_factors(transformed, actual)
            check(all(np.array_equal(left, right) for left, right in zip(expected_angles, actual_angles)),
                  f"Upstream phase mismatch: {directory}, {resolution}, {gauge}")
            check(np.all(np.isfinite(actual)) and all(np.all(np.isfinite(angle)) for angle in actual_angles),
                  f"Nonfinite actual complement or angles: {directory}, {resolution}, {gauge}")
            completion = rational_residual(transformed, actual)
            check(completion == checker.exact_residual(transformed, actual), "Independent completion arithmetic disagrees")
            check(completion <= Fraction(1, 10**12), "Saved fixture completion certificate invalid")
            certificate_checks += 1
            state = np.array([transformed, actual])
            margins = []
            for stage in reversed(range(len(transformed))):
                leading, other = state[:, stage]
                margins.extend((float(abs(other)), float(abs(leading * np.conj(other)))))
                if stage:
                    rotation = rotation_class(actual_angles[0][stage], actual_angles[1][stage], 0).rotation_matrix
                    state = rotation.conj().T @ state
                    state = np.array([state[0, 1:stage + 1], state[1, :stage]])
            margin = min(margins)
            check(margin == method.phase_guard_margin(transformed, actual, *actual_angles[:2]), "Guard replay disagrees")
            check(math.isfinite(margin) and margin >= 1e-8, "Saved fixture phase guard invalid")
            minimum_margin = min(minimum_margin, margin)
            source_checks += 1
            records.append({"fixture": directory, "degree": len(polynomial) - 1, "num_modes": resolution,
                            "gauge": gauge, "completion_residual_bound": float(completion),
                            "phase_guard_margin": margin, "complement_and_angles_finite": True})
    for first, second in (
        (np.array([0.5, 0.5]), np.array([0.5, -0.5])),
        (np.array([complex(2**-1074, -2**-1074), 0.125j]), np.array([0.5])),
    ):
        check(rational_residual(first, second) == checker.exact_residual(first, second), "Edge-case certificate mismatch")
        certificate_checks += 1
    check(tracking.branch_hits == 0, "An upstream near-zero phase branch was entered")
    return {"upstream_bitwise_cases": source_checks, "independent_fraction_certificate_checks": certificate_checks,
            "upstream_guard_branch_checks": tracking.branch_checks, "upstream_guard_branch_hits": tracking.branch_hits,
            "smallest_tested_guard_margin": minimum_margin, "actual_finite_route_records": records}


def independent_circle_error(polynomial, complement, angles):
    with mp.workdps(120):
        theta, phi, lambd = angles
        rotations = []
        for index in range(len(theta)):
            angle = mp.mpf(float(theta[index]))
            phase = mp.mpf(float(phi[index]))
            initial = mp.mpf(float(lambd)) if index == 0 else mp.mpf(0)
            rotations.append(mp.matrix([
                [mp.exp(mp.j * (initial + phase)) * mp.cos(angle), mp.exp(mp.j * phase) * mp.sin(angle)],
                [mp.exp(mp.j * initial) * mp.sin(angle), -mp.cos(angle)],
            ]))
        coefficients = [[mp.mpc(float(value.real), float(value.imag)) for value in array]
                        for array in (polynomial, complement)]
        samples = []
        sample_count = 2 * len(polynomial) + 1
        for index in range(sample_count):
            point = mp.exp(2 * mp.pi * mp.j * index / sample_count)
            state = rotations[0] * mp.matrix([1, 0])
            for rotation in rotations[1:]:
                state = rotation * mp.matrix([point * state[0], state[1]])
            target = [mp.polyval(list(reversed(array)), point) for array in coefficients]
            samples.append((target, state))
        overlap = mp.fsum(mp.conj(target[component]) * state[component]
                         for target, state in samples for component in (0, 1))
        phase = overlap / abs(overlap) if overlap else mp.mpc(1)
        residual = mp.fsum(abs(state[component] - phase * target[component])**2
                           for target, state in samples for component in (0, 1)) / sample_count
        block_residual = mp.fsum(abs(state[0] - phase * target[0])**2 for target, state in samples) / sample_count
        return float(mp.sqrt(residual)), float(mp.sqrt(block_residual))


def audit_finite_records(report, label):
    records = report["configurations"]
    check([(record["num_modes"], record["gauge"]) for record in records] == CONFIGURATIONS,
          f"Incorrect six configurations: {label}")
    fields = ("num_modes", "gauge", "completion_residual_bound", "phase_guard_margin", "rms_error", "top_block_error")
    nonfinite = []
    for index, record in enumerate(records):
        for field in fields:
            value = record[field]
            if type(value) not in (int, float) or not math.isfinite(value):
                nonfinite.append(f"configurations[{index}].{field}")
        check(type(record["completion_valid"]) is bool and type(record["guard_valid"]) is bool,
              f"Invalid configuration flags: {label}")
    check(not nonfinite, f"Nonfinite actual records in {label}: {nonfinite}")
    return {"report": label, "records_checked": len(records), "numeric_fields_checked": len(records) * len(fields),
            "nonfinite_locations": nonfinite, "all_records_finite": True}


def audit_replays_and_reconstruction(checker, method):
    fixtures = []
    finite_reports = []
    precision_checks = 0
    circle_checks = 0
    maximum_precision_difference = 0.0
    maximum_circle_difference = 0.0
    for name, directory, generation, stored_path in REPLAY_FIXTURES:
        current = checker.evaluate(CONCEPT_ROOT / directory)
        if generation is None:
            result = current
            check(result["admissible"] and not result["passed"], f"Unexpected saved current-domain fixture score: {name}")
            scoring_generation = 3
        else:
            path = CONCEPT_ROOT / f"adversary/generations/generation_{generation}/evaluator/hidden/checker.py"
            archive = load_module(f"audit_archive_checker_{generation}", path)
            result = archive.evaluate(CONCEPT_ROOT / directory)
            check(result["passed"], f"Archived generation {generation} champion no longer passes its original evaluator")
            check(not current["input_valid"] and not current["passed"] and "degree" in current["reason"],
                  f"Archived generation {generation} champion was not rejected by the current degree gate")
            scoring_generation = generation
        stored = json.loads((CONCEPT_ROOT / stored_path).read_text())
        finite_reports.append(audit_finite_records(result, f"computed_saved_fixture:{directory}"))
        finite_reports.append(audit_finite_records(stored, f"stored_report:{stored_path}"))
        polynomial, certificate = load_fixture(checker, directory)
        for resolution, gauge in CONFIGURATIONS:
            transformed = transformed_polynomial(polynomial, gauge)
            complement = method.fft_complementary_polynomial(transformed, tolerance=0, num_modes=resolution)
            angles = method.qsp_phase_factors(transformed, complement)
            ordinary = checker.reconstructed_error(transformed, complement, angles, digits=80)
            extended = checker.reconstructed_error(transformed, complement, angles, digits=120)
            check(all(math.isfinite(value) for value in ordinary + extended), "Nonfinite actual reconstructed error")
            difference = max(abs(left - right) for left, right in zip(ordinary, extended))
            maximum_precision_difference = max(maximum_precision_difference, difference)
            check(difference < 1e-14, "80/120-digit reconstruction disagreement")
            precision_checks += 1
            if (resolution, gauge) in ((4096, 0), (16384, 1)):
                independent = independent_circle_error(transformed, complement, angles)
                check(all(math.isfinite(value) for value in independent), "Nonfinite independent matrix-product error")
                difference = max(abs(left - right) for left, right in zip(extended, independent))
                maximum_circle_difference = max(maximum_circle_difference, difference)
                check(difference < 1e-14, "Independent matrix-product integration disagrees")
                circle_checks += 1
        fixtures.append({"name": name, "artifact": f"concept_2/{directory}/counterexample.json",
                         "degree": len(polynomial) - 1, "scoring_generation": scoring_generation,
                         "inside_current_degree_domain": 8 <= len(polynomial) - 1 <= 12,
                         "minimum_rms_error": result["minimum_rms_error"], "original_domain_evaluation": result,
                         "current_domain_evaluation": current, "demonstrates_current_domain_solvability": False})
    simple = np.array([0.5 + 0j, 0.5 + 0j])
    complement = np.array([0.5 + 0j, -0.5 + 0j])
    angles = method.qsp_phase_factors(simple, complement)
    ordinary = checker.reconstructed_error(simple, complement, angles)[0]
    common_gauge = checker.reconstructed_error(1j * simple, 1j * complement, angles)[0]
    relative_gauge = checker.reconstructed_error(simple, 1j * complement, angles)[0]
    check(ordinary < 1e-14 and common_gauge < 1e-14, "Common-phase invariance fails")
    check(abs(relative_gauge - float(mp.sqrt(2 - mp.sqrt(2)))) < 1e-14, "Joint-column relative-phase test fails")
    return {"fixtures": fixtures, "actual_record_finite_audit": {
                "reports": finite_reports, "records_checked": sum(report["records_checked"] for report in finite_reports),
                "numeric_fields_checked": sum(report["numeric_fields_checked"] for report in finite_reports),
                "nonfinite_records_found": False, "active_attempts_read_or_scored": False},
            "direct_80_vs_120_digit_checks": precision_checks, "maximum_precision_difference": maximum_precision_difference,
            "independent_120_digit_matrix_circle_checks": circle_checks, "maximum_circle_difference": maximum_circle_difference,
            "comparison_precision": "Reported errors are compared after conversion to binary64, as in the evaluator.",
            "quadrature_scope": "2*(degree+1)+1 roots of unity integrate polynomial overlaps and squared errors without aliasing; arithmetic uses 120 digits.",
            "phase_invariance": {"ordinary_error": ordinary, "common_phase_error": common_gauge,
                                 "relative_column_phase_error": relative_gauge}}


class MemoryArtifact:
    def __init__(self, text, linked=False, exists=True, size=None):
        self.text, self.linked, self.exists, self.size = text, linked, exists, size

    def is_symlink(self):
        return self.linked

    def is_file(self):
        return self.exists

    def stat(self):
        return SimpleNamespace(st_size=len(self.text.encode()) if self.size is None else self.size)

    def read_text(self):
        return self.text


class MemorySubmission:
    def __init__(self, artifact):
        self.artifact = artifact

    def __truediv__(self, filename):
        check(filename == "counterexample.json", "Unexpected in-memory artifact path")
        return self.artifact


def audit_parser_and_faults(checker):
    baseline_text = (CONCEPT_ROOT / "participant/baseline/counterexample.json").read_text()
    baseline = json.loads(baseline_text)

    def evaluate_text(text, **options):
        return checker.evaluate(MemorySubmission(MemoryArtifact(text, **options)))

    mutations = {}
    for name in ("boolean", "missing", "extra", "mismatch", "zero_leading", "bad_certificate", "bad_component",
                 "too_little_energy", "insufficient_complexity"):
        data = copy.deepcopy(baseline)
        if name == "boolean":
            data["P"][0][0] = True
        elif name == "missing":
            del data["H"]
        elif name == "extra":
            data["other"] = 0
        elif name == "mismatch":
            data["H"].pop()
        elif name == "zero_leading":
            data["P"][-1] = [0, 0]
        elif name == "bad_certificate":
            data["H"][0][0] += 1e-5
        elif name == "bad_component":
            data["P"][0][0] = 2.01
        elif name == "too_little_energy":
            data["P"] = [[real * 0.01, imag * 0.01] for real, imag in data["P"]]
        elif name == "insufficient_complexity":
            data["P"] = [[abs(complex(real, imag)), 0] for real, imag in data["P"]]
        mutations[name] = json.dumps(data)
    mutations.update({"duplicate": '{"P":[],"P":[],"H":[]}', "nan": '{"P":[[NaN,0]],"H":[]}',
                      "infinity": '{"P":[[Infinity,0]],"H":[]}', "negative_infinity": '{"P":[[-Infinity,0]],"H":[]}',
                      "overflow_literal": '{"P":[[1e999,0]],"H":[]}', "wrong_root": "[]", "truncated_json": '{"P":'})
    rejections = []
    for name, text in mutations.items():
        result = evaluate_text(text)
        check(not result["input_valid"] and not result["passed"], f"Malformed input was accepted: {name}")
        rejections.append({"case": name, "reason": result["reason"]})
    for options in ({"linked": True}, {"exists": False}, {"size": 65537}):
        result = evaluate_text(baseline_text, **options)
        check(not result["input_valid"] and not result["passed"], f"Artifact metadata rejection fails: {options}")
        rejections.append({"case": options, "reason": result["reason"]})
    original_reconstruction = checker.reconstructed_error
    observed_digits = []

    def trace_digits(polynomial, complement, angles, digits=80):
        observed_digits.append(digits)
        return original_reconstruction(polynomial, complement, angles, digits=digits)

    try:
        checker.reconstructed_error = trace_digits
        checker.audit_pair(checker.coefficients(baseline["P"]), digits=120)
    finally:
        checker.reconstructed_error = original_reconstruction
    check(observed_digits == [120] * 6, "audit_pair does not forward its requested precision")
    original_audit = checker.audit_pair
    records = original_audit(checker.coefficients(baseline["P"]))
    for record in records:
        record["rms_error"] = 0.06
    try:
        checker.audit_pair = lambda polynomial: copy.deepcopy(records)
        check(evaluate_text(baseline_text)["passed"], "All-six passing-record aggregation fails")
        for index in range(6):
            records[index]["rms_error"] = 0.049
            result = evaluate_text(baseline_text)
            check(not result["passed"] and abs(result["core_score"] - 0.98) < 1e-15, "A failing configuration was ignored")
            records[index]["rms_error"] = 0.06
            for field in ("completion_valid", "guard_valid"):
                records[index][field] = False
                result = evaluate_text(baseline_text)
                check(not result["passed"] and result["core_score"] == 0, "An invalid configuration was ignored")
                records[index][field] = True
        records[-1]["rms_error"] = float("nan")
        injected = evaluate_text(baseline_text)
    finally:
        checker.audit_pair = original_audit
    return {"malformed_input_rejections": len(rejections), "rejections": rejections,
            "artifact_metadata_checks_use_in_memory_stubs": True, "six_configuration_failure_checks": 18,
            "precision_forwarding": {"requested_digits": 120, "observed_digits": observed_digits},
            "fault_injected_nan": {"injection_site": "checker.audit_pair return value, in memory only",
                                   "other_configuration_errors": 0.06, "record_index": 5, "injected_error": "NaN",
                                   "passed": injected["passed"], "core_score": injected["core_score"],
                                   "minimum_rms_error": injected["minimum_rms_error"],
                                   "valid_artifact_exploit_demonstrated": False,
                                   "distinction": "This synthetic internal fault is not produced by a submitted polynomial. Actual saved-fixture records, complements, and angles are audited separately for finiteness."}}


def main():
    started = time.monotonic()
    report = {"audit_kind": "independent_generation_time_numerical_evaluator_audit",
              "started_utc": datetime.now(timezone.utc).isoformat(), "status": "running",
              "write_paths": [relative(Path(__file__).resolve()), relative(REPORT_PATH)],
              "searches_executed": False, "active_attempts_read_or_scored": False,
              "fresh_agent_performance_assessed": False,
              "environment": {"python": sys.version, "numpy": np.__version__, "mpmath": mp.__version__},
              "script_sha256": digest(Path(__file__).resolve())}
    monitored = set()
    before = {}
    succeeded = False
    try:
        report["freeze_before"], monitored = frozen_assets()
        monitored.update(SOURCE_ROOT / filename for filename in SOURCE_FILES)
        monitored.update(CONCEPT_ROOT / directory / "counterexample.json" for directory in SOURCE_FIXTURES)
        for name, directory, generation, stored_path in REPLAY_FIXTURES:
            monitored.add(CONCEPT_ROOT / directory / "counterexample.json")
            monitored.add(CONCEPT_ROOT / stored_path)
        before = {relative(path): digest(path) for path in sorted(monitored)}
        commit = subprocess.run(["git", "-C", str(SOURCE_ROOT), "rev-parse", "HEAD"],
                                check=True, capture_output=True, text=True).stdout.strip()
        check(commit == PINNED_COMMIT, f"Unexpected upstream commit: {commit}")
        report["source_commit"] = commit
        sys.path.insert(0, str(CONCEPT_ROOT / "evaluator/hidden"))
        checker = load_module("independent_concept_2_checker", CONCEPT_ROOT / "evaluator/hidden/checker.py")
        method = sys.modules["target_method"]
        check(checker.CONFIGURATIONS == CONFIGURATIONS, "Current evaluator configurations differ from the six specified cases")
        report["source_and_certificate_checks"] = audit_source_and_certificates(checker, method)
        report["replay_and_reconstruction_checks"] = audit_replays_and_reconstruction(checker, method)
        report["parser_and_scoring_checks"] = audit_parser_and_faults(checker)
        report["freeze_after"], remaining = frozen_assets()
        check(remaining <= monitored, "Unexpected frozen asset inventory change")
        after = {relative(path): digest(path) for path in sorted(monitored)}
        changed = [path for path, expected in before.items() if after[path] != expected]
        check(not changed, f"Audited inputs changed during the audit: {changed}")
        report["input_integrity"] = {"files_checked": len(before), "sha256": before, "changed_paths": changed,
                                     "all_monitored_inputs_unchanged": True}
        gap = report["parser_and_scoring_checks"]["fault_injected_nan"]["passed"]
        report["findings"] = [{"severity": "low", "kind": "latent_nonfinite_aggregation_gap",
                               "observed_under_fault_injection": gap,
                               "paths": ["concept_2/evaluator/hidden/checker.py:94", "concept_2/evaluator/hidden/checker.py:132"],
                               "valid_artifact_exploit_demonstrated": False,
                               "finite_route_observation": "All audited actual complements, angles, and configuration-record numeric fields were finite."}]
        report["witness_scope"] = {
            "current_degree_range": [8, 12], "generation_1_degree_range": [32, 48], "generation_2_degree_range": [8, 14],
            "archived_champions_pass_original_domain_and_fail_current_degree_gate": True,
            "current_domain_solvability": "not_demonstrated_by_audited_fixtures",
            "impossibility_proved": False,
            "scope_paths": ["concept_2/participant/workspace/interface.md:11", "concept_2/adversary/ratchet_generation_3.md:17"],
        }
        report["limits"] = [
            "No candidate searches, active-attempt scoring, or fresh-agent performance assessment were performed.",
            "Exact rational certificate checks are distinct from high-precision transcendental reconstruction, which is not interval-certified.",
            "Source parity covers the pinned extracted FFT/phase/rotation route, not the default root constructor, full-package execution, or every Qualtran route.",
            "The metric concerns the joint first column modulo one common phase; top-block error uses that same joint-optimal phase.",
            "Parser and artifact metadata fault tests use in-memory stubs, not filesystem-race or process-isolation tests.",
            "Historical and larger-degree successes do not prove current degree-8-through-12 solvability; saved failures do not prove impossibility.",
            "Private stale provenance wording is left for main to correct; this script does not read or change that concurrently maintained document.",
        ]
        report["independent_checks_passed"] = True
        report["status"] = "completed_with_findings" if gap else "completed"
        succeeded = True
    except Exception as error:
        report["status"] = "failed"
        report["independent_checks_passed"] = False
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
    report["completed_utc"] = datetime.now(timezone.utc).isoformat()
    report["runtime_seconds"] = time.monotonic() - started
    REPORT_PATH.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"], "report": relative(REPORT_PATH),
                      "runtime_seconds": report["runtime_seconds"], "failure": report.get("failure")}, indent=2))
    return 0 if succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
