"""Trusted data-only evaluator. Never imports or executes submission code."""

import os
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import argparse
import hashlib
import importlib.util
import json
import stat
import sys
import time
from pathlib import Path


sys.dont_write_bytecode = True
RESOURCES = Path(__file__).resolve().parent / "resources"


def trusted_module(name):
    specification = importlib.util.spec_from_file_location("trusted_" + name, RESOURCES / (name + ".py"))
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def read_witness(directory):
    path = directory / "witness.json"
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > 16384:
            raise ValueError("witness must be a regular file of at most 16384 bytes")
        data = stream.read(16385)
    if len(data) > 16384:
        raise ValueError("witness too large")
    return json.loads(data.decode("utf-8"), object_pairs_hook=unique_object)


def evaluate(directory):
    started = time.monotonic()
    result = {"valid": False, "passed": False, "core_score": 0.0,
              "worst_family_score": 0.0, "resource_score": 0.0, "families": {}}
    try:
        target_bytes = (RESOURCES / "target.json").read_bytes()
        target_hash = hashlib.sha256(target_bytes).hexdigest()
        if target_hash != (RESOURCES / "target.sha256").read_text().strip():
            raise RuntimeError("trusted target integrity failure")
        spec = json.loads(target_bytes)
        protocol = trusted_module("protocol")
        witness = read_witness(directory)
        families = protocol.waveforms(witness, spec)
        engine = trusted_module("simulator")
        reference = trusted_module("reference")
        result.update(valid=True, target_sha256=target_hash, depth=witness["depth"],
                      resource_score=100.0 * spec["depth_min"] / witness["depth"],
                      resource_units=len(families) * witness["depth"] * len(spec["chis"]),
                      chis=spec["chis"], thresholds={"error_min": spec["error_min"], "spread_max": spec["spread_max"]})
        for family, angles in families.items():
            truth_state = reference.exact_state(angles)
            truth = reference.zz1(truth_state)
            estimates, diagnostics = [], {}
            for chi in spec["chis"]:
                state, diagnostic = engine.mps_state(angles, chi)
                estimates.append(reference.zz1(state))
                diagnostics[str(chi)] = diagnostic
            record = protocol.metrics(truth, estimates, spec)
            record["diagnostics"] = diagnostics
            result["families"][family] = record
        result["core_score"] = result["families"]["nominal"]["score"]
        result["worst_family_score"] = min(record["score"] for record in result["families"].values())
        result["passed"] = all(record["passed"] for record in result["families"].values())
        result["reason"] = "robust false-convergence witness" if result["passed"] else "valid waveform; at least one family misses error or spread threshold"
    except (ValueError, OSError, TypeError, OverflowError, RecursionError) as error:
        result.update(valid=False, passed=False, core_score=0.0, worst_family_score=0.0,
                      resource_score=0.0, reason="invalid submission: " + str(error))
    except Exception as error:
        result.update(valid=False, passed=False, core_score=0.0, worst_family_score=0.0,
                      resource_score=0.0, reason="checker failure: " + type(error).__name__ + ": " + str(error))
    result["elapsed_seconds"] = time.monotonic() - started
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    result = evaluate(options.submission)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: result[key] for key in ("valid", "passed", "core_score", "worst_family_score", "resource_score", "reason")}))


if __name__ == "__main__":
    main()
