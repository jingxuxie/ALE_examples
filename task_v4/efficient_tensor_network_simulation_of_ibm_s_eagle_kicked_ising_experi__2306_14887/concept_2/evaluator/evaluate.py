"""Trusted data-only evaluator. Never imports or executes submission code."""

import os
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import argparse
import hashlib
import importlib.util
import json
import multiprocessing
import stat
import sys
import time
from pathlib import Path


sys.dont_write_bytecode = True
RESOURCES = Path(__file__).resolve().parent / "resources"


def trusted_module(name):
    specification = importlib.util.spec_from_file_location("trusted_" + name, RESOURCES / (name + ".py"))
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
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


def evaluate(directory, workers=4):
    started = time.monotonic()
    result = {"valid": False, "passed": False, "core_score": 0.0,
              "worst_family_score": 0.0, "resource_score": 0.0, "families": {}, "evaluation_complete": False}
    try:
        target_bytes = (RESOURCES / "target.json").read_bytes()
        target_hash = hashlib.sha256(target_bytes).hexdigest()
        if target_hash != (RESOURCES / "target.sha256").read_text().strip():
            raise RuntimeError("trusted target integrity failure")
        spec = json.loads(target_bytes)
        if type(workers) is not int or not 1 <= workers <= spec["checker_workers"]:
            raise ValueError("workers must be an integer from one to four")
        protocol = trusted_module("protocol")
        witness = read_witness(directory)
        families = protocol.waveforms(witness, spec)
        if len(families) != spec["family_count"]:
            raise RuntimeError("trusted suite size mismatch")
        worker = trusted_module("worker")
        result.update(valid=True, target_sha256=target_hash, depth=witness["depth"],
                      resource_score=100.0 * spec["depth_min"] / witness["depth"],
                      resource_units=len(families) * witness["depth"] * len(spec["chis"]),
                      chis=spec["chis"], family_count=len(families), workers=workers,
                      runtime_budget_seconds=spec["checker_timeout_seconds"],
                      thresholds={"error_min": spec["error_min"], "spread_max": spec["spread_max"]})
        pool = multiprocessing.get_context("fork").Pool(processes=workers)
        try:
            pending = pool.imap_unordered(worker.evaluate_waveform, families.items(), chunksize=1)
            for _ in families:
                remaining = spec["checker_timeout_seconds"] - (time.monotonic() - started)
                if remaining <= 0:
                    raise multiprocessing.TimeoutError("trusted evaluation time budget exceeded")
                family, record = pending.next(timeout=remaining)
                result["families"][family] = record
            pool.close()
        except BaseException:
            pool.terminate()
            raise
        finally:
            pool.join()
        result["families"] = {family: result["families"][family] for family in families}
        result["evaluation_complete"] = True
        result["core_score"] = result["families"]["nominal"]["score"]
        result["worst_family_score"] = min(record["score"] for record in result["families"].values())
        result["passed"] = all(record["passed"] for record in result["families"].values())
        result["reason"] = "robust false-convergence witness across all 325 waveforms" if result["passed"] else "valid waveform; at least one of 325 families misses error or spread threshold"
    except multiprocessing.TimeoutError:
        result.update(passed=False, core_score=0.0, worst_family_score=0.0, resource_score=0.0,
                      reason="trusted evaluation exceeded the 600-second time budget")
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
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=4)
    options = parser.parse_args()
    result = evaluate(options.submission, options.workers)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: result[key] for key in ("valid", "passed", "core_score", "worst_family_score", "resource_score", "reason")}))


if __name__ == "__main__":
    main()
