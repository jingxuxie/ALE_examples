import argparse
import hashlib
import json
import math
import os
import re
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import mpmath as mp
import numpy as np
from scipy.optimize import linear_sum_assignment


ROOT = Path(__file__).resolve().parents[1]
HIDDEN = ROOT / "evaluator" / "hidden"
SANDBOX = Path(__file__).resolve().parents[2] / "authoring" / "sandbox.py"
CORE_THRESHOLD = 0.90
WORST_THRESHOLD = 0.80
CASE_SECONDS = 30.0
SUITE_SECONDS = 240.0
OUTPUT_BYTES = 1024 * 1024
MEMORY_BYTES = 1024 ** 3
NUMBER = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")


class InvalidOutput(ValueError):
    pass


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidOutput("duplicate_json_key")
        result[key] = value
    return result


def reject_constant(value):
    raise InvalidOutput("nonfinite_json_number")


def load_output(raw):
    if len(raw) > OUTPUT_BYTES:
        raise InvalidOutput("output_too_large")
    try:
        return json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        raise InvalidOutput("malformed_json:" + str(error)[:100]) from error


def numeric(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise InvalidOutput("invalid_number_type")
    representation = str(value)
    if len(representation) > 2048 or not NUMBER.fullmatch(representation):
        raise InvalidOutput("invalid_number")
    exponent = re.search(r"[eE]([+-]?\d+)$", representation)
    if exponent and (len(exponent.group(1).lstrip("+-")) > 5 or abs(int(exponent.group(1))) > 10000):
        raise InvalidOutput("number_exponent_out_of_range")
    try:
        converted = mp.mpf(representation)
    except ValueError as error:
        raise InvalidOutput("invalid_number") from error
    if not mp.isfinite(converted) or abs(converted) > mp.mpf("1e1000"):
        raise InvalidOutput("number_out_of_range")
    return converted


def packed_norm(packed):
    return mp.sqrt(packed[0] ** 2 + 2 * packed[1] ** 2 + packed[2] ** 2)


def chebyshev_value(coefficients, position):
    following = [mp.mpf(0)] * 3
    after = [mp.mpf(0)] * 3
    for packed in reversed(coefficients[1:]):
        current = [2 * position * following[column] - after[column] + mp.mpf(packed[column]) for column in range(3)]
        after, following = following, current
    return [position * following[column] - after[column] + mp.mpf(coefficients[0][column]) for column in range(3)]


def trace_product(left, right):
    return left[0] * right[0] + 2 * left[1] * right[1] + left[2] * right[2]


def null_residual(matrix, projector):
    products = [matrix[0] * projector[0] + matrix[1] * projector[1],
                matrix[0] * projector[1] + matrix[1] * projector[2],
                matrix[1] * projector[0] + matrix[2] * projector[1],
                matrix[1] * projector[1] + matrix[2] * projector[2]]
    norm = packed_norm(matrix)
    if norm == 0:
        return mp.inf
    return mp.sqrt(mp.fsum(value ** 2 for value in products)) / norm


def parse_atoms(output, case):
    if not isinstance(output, dict) or set(output) != {"version", "atoms"}:
        raise InvalidOutput("wrong_top_level_fields")
    if type(output["version"]) is not int or output["version"] != 1:
        raise InvalidOutput("wrong_version")
    if not isinstance(output["atoms"], list) or len(output["atoms"]) > 256:
        raise InvalidOutput("invalid_atoms_list")
    blocks = {block["id"]: block for block in case["blocks"]}
    atoms = []
    for entry in output["atoms"]:
        if not isinstance(entry, dict) or set(entry) != {"block", "x", "projector", "weight"}:
            raise InvalidOutput("wrong_atom_fields")
        if not isinstance(entry["block"], str) or entry["block"] not in blocks:
            raise InvalidOutput("unknown_block")
        if not isinstance(entry["projector"], list) or len(entry["projector"]) != 3:
            raise InvalidOutput("wrong_projector_shape")
        projector = list(map(numeric, entry["projector"]))
        weight, physical = numeric(entry["weight"]), numeric(entry["x"])
        if weight <= 0:
            raise InvalidOutput("nonpositive_weight")
        trace = projector[0] + projector[2]
        difference = [projector[0] ** 2 + projector[1] ** 2 - projector[0],
                      projector[1] * (trace - 1), projector[2] ** 2 + projector[1] ** 2 - projector[2]]
        minimum = (trace - mp.sqrt((projector[0] - projector[2]) ** 2 + 4 * projector[1] ** 2)) / 2
        if abs(trace - 1) > mp.mpf("1e-6") or packed_norm(difference) > mp.mpf("5e-6") or minimum < -mp.mpf("1e-8"):
            raise InvalidOutput("nonphysical_projector")
        block = blocks[entry["block"]]
        position = (physical - mp.mpf(block["origin"])) / mp.mpf(block["scale"])
        radius = 1 if block["kind"] == "interval" else 0
        if abs(position) > radius + mp.mpf("2e-14"):
            raise InvalidOutput("out_of_domain")
        atoms.append({"block": entry["block"], "t": position, "projector": projector, "weight": weight})
    return atoms


def failed(reason, runtime=0.0):
    return {"score": 0.0, "location_f1": 0.0, "direction_f1": 0.0, "weight_f1": 0.0,
            "closure": 0, "moment_residual": None, "protocol_valid": False,
            "reason": reason, "runtime_seconds": runtime}


def score_case(case, witness, output, runtime=0.0):
    with mp.workdps(290):
        try:
            atoms = parse_atoms(output, case)
        except (InvalidOutput, ValueError, TypeError, OverflowError) as error:
            return failed(str(error), runtime)
        truths = witness["features"]
        blocks = {block["id"]: block for block in case["blocks"]}
        counts = [0, 0, 0]
        for block_id, block in blocks.items():
            expected = [truth for truth in truths if truth["block"] == block_id]
            predicted = [atom for atom in atoms if atom["block"] == block_id]
            if not expected or not predicted:
                continue
            positions = [mp.mpf(truth["t"]) for truth in expected]
            tolerances = []
            for index, position in enumerate(positions):
                neighbors = [abs(position - other) for other_index, other in enumerate(positions) if index != other_index]
                tolerances.append(min(mp.mpf("2e-8"), min(neighbors) / 40) if neighbors else mp.mpf("2e-8"))
            costs = np.full((len(expected), len(predicted)), 1e6)
            for row, position in enumerate(positions):
                for column, atom in enumerate(predicted):
                    relative = abs(position - atom["t"]) / tolerances[row]
                    if relative <= 1:
                        costs[row, column] = float(relative)
            matched_rows, matched_columns = linear_sum_assignment(costs)
            for row, column in zip(matched_rows, matched_columns):
                if costs[row, column] > 1:
                    continue
                counts[0] += 1
                atom, truth = predicted[column], expected[row]
                error = packed_norm([value - mp.mpf(target) for value, target in zip(atom["projector"], truth["projector"])])
                residual = null_residual(chebyshev_value(block["matrix"], atom["t"]), atom["projector"])
                if error <= mp.mpf("2e-6") and residual <= mp.mpf("2e-8"):
                    counts[1] += 1
                    if abs(atom["weight"] / mp.mpf(truth["weight"]) - 1) <= mp.mpf("2e-4"):
                        counts[2] += 1
        residuals = []
        for row, target_text in enumerate(case["rhs"]):
            target = mp.mpf(target_text)
            predicted = mp.fsum(atom["weight"] * trace_product(
                chebyshev_value(blocks[atom["block"]]["moments"][row], atom["t"]), atom["projector"])
                for atom in atoms)
            residuals.append(abs(predicted - target) / max(1, abs(target)))
        residual = max(residuals)
        closure = int(bool(atoms) and residual <= mp.mpf("1e-8"))
        denominator = len(truths) + len(atoms)
        metrics = [2 * count / denominator for count in counts]
        score = 0.3 * sum(metrics) + 0.1 * closure
        return {"score": score, "location_f1": metrics[0], "direction_f1": metrics[1], "weight_f1": metrics[2],
                "closure": closure, "moment_residual": mp.nstr(residual, 12), "expected_count": len(truths),
                "returned_count": len(atoms), "protocol_valid": True,
                "reason": "ok" if score >= 1 - 1e-12 else "incomplete_or_inaccurate_spectrum",
                "runtime_seconds": runtime}


def load_suite():
    manifest = json.loads((HIDDEN / "manifest.json").read_text())
    suite = []
    for record in manifest["cases"]:
        raw = (ROOT / record["input"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != record["sha256"]:
            raise ValueError("challenge_checksum_mismatch")
        witness = json.loads((ROOT / record["witness"]).read_text())
        suite.append((record, raw, json.loads(raw), witness))
    return suite


def aggregate(results):
    family_names = sorted({result["family"] for result in results})
    families = {family: sum(result["score"] for result in results if result["family"] == family)
                / sum(result["family"] == family for result in results) for family in family_names}
    core = sum(families.values()) / len(families) if families else 0.0
    worst = min(families.values()) if families else 0.0
    runtime = sum(result["runtime_seconds"] for result in results)
    failures = sum(not result["protocol_valid"] for result in results)
    reasons = []
    if core + 1e-12 < CORE_THRESHOLD:
        reasons.append("core_below_0.90")
    if worst + 1e-12 < WORST_THRESHOLD:
        reasons.append("worst_family_below_0.80")
    if failures:
        reasons.append("protocol_failures")
    if runtime > SUITE_SECONDS:
        reasons.append("suite_runtime_exceeded")
    return {"version": 1, "core": core, "worst_family": worst, "runtime_seconds": runtime,
            "passed": not reasons, "reason": ";".join(reasons) if reasons else "thresholds_met",
            "protocol_failures": failures, "families": families, "cases": results}


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES, MEMORY_BYTES))
    resource.setrlimit(resource.RLIMIT_CPU, (32, 32))
    resource.setrlimit(resource.RLIMIT_FSIZE, (OUTPUT_BYTES, OUTPUT_BYTES))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def run_candidate(submission, raw, timeout):
    runs = HIDDEN / "runs"
    runs.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="case_", dir=runs) as directory:
        staging = Path(directory)
        workspace = staging / "workspace"
        shutil.copytree(submission.parent, workspace, symlinks=True, ignore=shutil.ignore_patterns("__pycache__", ".git"))
        scratch = staging / "scratch"
        scratch.mkdir()
        environment = {key: value for key, value in os.environ.items() if key in ("PATH", "LD_LIBRARY_PATH", "LANG", "LC_ALL")}
        environment.update({"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0", "HOME": str(staging),
                            "TMPDIR": str(staging)})
        with (staging / "stdout").open("w+b") as stdout, (staging / "stderr").open("w+b") as stderr:
            started = time.monotonic()
            command = [sys.executable, str(SANDBOX), "--submission", str(workspace),
                       "--participant", str(ROOT / "participant"), "--scratch", str(scratch),
                       "--entry", submission.name, "--seconds", str(timeout), "--memory-mib", "1024"]
            process = subprocess.Popen(command, stdin=subprocess.PIPE,
                                       stdout=stdout, stderr=stderr, cwd=scratch, env=environment,
                                       start_new_session=True)
            failure = None
            try:
                process.communicate(raw, timeout=timeout)
            except subprocess.TimeoutExpired:
                failure = "timeout"
            finally:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
            elapsed = time.monotonic() - started
            if failure:
                return None, failed(failure, elapsed)
            if process.returncode != 0:
                return None, failed("nonzero_exit:" + str(process.returncode), elapsed)
            stdout.seek(0)
            output_raw = stdout.read(OUTPUT_BYTES + 1)
            stderr.seek(0)
            if len(output_raw) >= OUTPUT_BYTES or len(stderr.read(OUTPUT_BYTES + 1)) >= OUTPUT_BYTES:
                return None, failed("output_limit", elapsed)
            try:
                output = load_output(output_raw)
            except InvalidOutput as error:
                return None, failed(str(error), elapsed)
            return output, {"runtime_seconds": elapsed}


def evaluate_submission(submission):
    suite = load_suite()
    results = []
    spent = 0.0
    for record, raw, case, witness in suite:
        remaining = SUITE_SECONDS - spent
        if remaining <= 0:
            result = failed("suite_budget_exhausted")
        else:
            output, execution = run_candidate(submission, raw, min(CASE_SECONDS, remaining))
            result = execution if output is None else score_case(case, witness, output, execution["runtime_seconds"])
            spent += result["runtime_seconds"]
        result.update({"id": record["id"], "family": record["family"]})
        results.append(result)
    return aggregate(results)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, default=ROOT / "participant" / "workspace")
    parser.add_argument("--entry", default="solve.py")
    parser.add_argument("--report", type=Path)
    arguments = parser.parse_args()
    submission = arguments.submission.resolve()
    if submission.is_dir():
        submission = (submission / arguments.entry).resolve()
    if not submission.is_file() or not submission.is_relative_to(ROOT):
        parser.error("submission must be a Python entry point under concept_1")
    if arguments.report and not arguments.report.resolve().is_relative_to(HIDDEN):
        parser.error("reports are private and must be written under concept_1/evaluator/hidden")
    report = evaluate_submission(submission)
    if arguments.report:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, allow_nan=False))


if __name__ == "__main__":
    main()
