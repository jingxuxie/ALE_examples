import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

import numpy as np


PRIVATE = Path(__file__).resolve().parent
ROOT = PRIVATE.parent
TIMEOUT = 120
MAX_OUTPUT_BYTES = 16 * 1024 * 1024


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("nonfinite JSON constant")


def read_json(path):
    return json.loads(path.read_text(), object_pairs_hook=strict_object, parse_constant=reject_constant)


def rms(values):
    array = np.asarray(values, dtype=float)
    largest = float(np.max(np.abs(array))) if array.size else 0.0
    return largest * float(np.sqrt(np.mean((array / largest)**2))) if largest else 0.0


def component_arrays(case, output):
    if case["family"] == "fourier":
        diagonal = [index for index, channel in enumerate(case["channels"]) if channel["sites"][0] == channel["sites"][1]]
        offdiagonal = [index for index, channel in enumerate(case["channels"]) if channel["sites"][0] != channel["sites"][1]]
        times = np.asarray(output["g_tau"], dtype=float)
        return {
            "diagonal_tau": times[diagonal],
            "offdiagonal_tau": times[offdiagonal],
            "roundtrip_iw": np.asarray(output["iw_roundtrip"], dtype=float),
        }
    return {key: np.asarray(value, dtype=float) for key, value in output.items()}


def errors_for(case, prediction, expected):
    observed = component_arrays(case, prediction)
    target = component_arrays(case, expected)
    errors = {}
    for key in target:
        normalization = max(1.0, rms(target[key]))
        with np.errstate(over="ignore", invalid="ignore"):
            error = rms(observed[key] / normalization - target[key] / normalization)
        errors[key] = min(error, 1e300) if math.isfinite(error) else 1e300
    return errors


def validate_output(output, expected):
    if not isinstance(output, dict):
        raise ValueError("output must be a JSON object")
    cleaned = {}
    for key, target in expected.items():
        if key not in output:
            raise ValueError("missing output field: " + key)
        pending = [output[key]]
        while pending:
            item = pending.pop()
            if isinstance(item, list):
                pending.extend(item)
            elif isinstance(item, bool) or not isinstance(item, (int, float)):
                raise ValueError("nonnumeric output: " + key)
        array = np.asarray(output[key])
        if array.dtype.kind not in "fiu" or array.shape != np.asarray(target).shape:
            raise ValueError("nonnumeric value or wrong shape: " + key)
        if not np.isfinite(array).all():
            raise ValueError("nonfinite output: " + key)
        cleaned[key] = array.tolist()
    return cleaned


def run_case(submission, record, timeout=TIMEOUT):
    case = read_json(PRIVATE / record["input"])
    expected = read_json(PRIVATE / record["reference"])
    result = {
        "id": record["id"], "family": record["family"], "score": 0.0,
        "component_scores": {key: 0.0 for key in record["scales"]},
        "errors": {key: None for key in record["scales"]},
        "times": {"wall_seconds": 0.0, "limit_seconds": timeout, "max_rss_kib": None},
        "status": "error",
    }
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="dmft-run-", dir=ROOT) as directory:
        work = Path(directory)
        try:
            if not submission.is_file():
                raise ValueError("submission is not a regular file")
            (work / "solve.py").write_bytes(submission.read_bytes())
            (work / "input.json").write_text(json.dumps(case, allow_nan=False))
            command = [sys.executable, "-I", "solve.py", "--input", "input.json", "--output", "output.json"]
            wrapper = os.environ.get("ALPS_EVAL_WRAPPER")
            if wrapper:
                command = [sys.executable, wrapper, "--participant", str(ROOT / "participant"),
                           "--submission", str(submission), "--work", str(work),
                           "--timeout", str(timeout), "--"] + command
            environment = {
                "PATH": os.defpath, "HOME": str(work), "TMPDIR": str(work),
                "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
                "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                "LC_ALL": "C.UTF-8",
            }
            process = subprocess.Popen(command, cwd=work, env=environment,
                                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL, start_new_session=True)
            try:
                returncode = process.wait(timeout=timeout + (10 if wrapper else 0))
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise ValueError("case exceeded wall-time limit")
            finally:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            resource_path = work / "_resource.json"
            if resource_path.is_file():
                try:
                    resource = read_json(resource_path)
                    if not isinstance(resource, dict):
                        raise ValueError("resource metadata must be an object")
                    for key in ("seconds", "max_rss_kib"):
                        value = resource.get(key)
                        if isinstance(value, (int, float)) and math.isfinite(value) and value >= 0:
                            result["times"]["resource_seconds" if key == "seconds" else key] = value
                except (ValueError, OSError, TypeError):
                    pass
            if returncode:
                raise ValueError("submission or wrapper exited with status " + str(returncode))
            output_path = work / "output.json"
            if not output_path.is_file() or output_path.is_symlink():
                raise ValueError("output file missing or not regular")
            if output_path.stat().st_size > MAX_OUTPUT_BYTES:
                raise ValueError("output exceeds size limit")
            prediction = validate_output(read_json(output_path), expected)
            result["errors"] = errors_for(case, prediction, expected)
            result["component_scores"] = {
                key: 1 / (1 + error / record["scales"][key]) for key, error in result["errors"].items()
            }
            result["score"] = float(np.mean(list(result["component_scores"].values())))
            result["status"] = "ok"
        except (OSError, ValueError, TypeError, OverflowError, KeyError, RecursionError) as error:
            result["failure"] = str(error)[:240]
        result["times"]["wall_seconds"] = time.monotonic() - started
    return result


def evaluate(submission, split):
    manifest = read_json(PRIVATE / "reference" / "manifest.json")
    cases = [run_case(submission, record) for record in manifest[split]]
    families = {}
    for family in sorted({case["family"] for case in cases}):
        members = [case for case in cases if case["family"] == family]
        families[family] = {
            "score": float(np.mean([case["score"] for case in members])),
            "count": len(members),
            "component_scores": {
                key: float(np.mean([case["component_scores"][key] for case in members]))
                for key in members[0]["component_scores"]
            },
        }
    return {
        "split": split,
        "mean_core_score": float(np.mean([case["score"] for case in cases])),
        "worst_family_score": min(family["score"] for family in families.values()),
        "families": families, "cases": cases,
        "times": {"total_wall_seconds": sum(case["times"]["wall_seconds"] for case in cases)},
        "execution": "external_wrapper" if os.environ.get("ALPS_EVAL_WRAPPER") else "isolated_files_only",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--split", required=True, choices=("core", "challenge"))
    parser.add_argument("--report", required=True, type=Path)
    arguments = parser.parse_args()
    report = evaluate(arguments.submission.resolve(), arguments.split)
    arguments.report.parent.mkdir(parents=True, exist_ok=True)
    arguments.report.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
