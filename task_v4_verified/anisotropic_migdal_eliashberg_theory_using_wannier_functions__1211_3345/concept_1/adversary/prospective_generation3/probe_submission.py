"""Private pool probe using the unchanged hardened candidate runner and scorer."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import tempfile
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"
sys.dont_write_bytecode = True
import numpy as np

SIDECAR = Path(__file__).resolve().parent
ROOT = SIDECAR.parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
import evaluate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--cases", type=Path, default=SIDECAR / "cases")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cpu-seconds", type=int, default=12)
    parser.add_argument("--case-id", action="append", default=[])
    arguments = parser.parse_args()
    output_directory = arguments.output.resolve()
    assert output_directory.is_relative_to(SIDECAR)
    output_directory.mkdir(parents=True, exist_ok=False)
    temporary = output_directory / "scratch"
    temporary.mkdir()
    tempfile.tempdir = str(temporary)
    started = time.process_time()
    started_wall = time.monotonic()
    child_start = resource.getrusage(resource.RUSAGE_CHILDREN)
    records = []
    for directory in sorted(arguments.cases.iterdir()):
        if not (directory / "instance.npz").is_file():
            continue
        if arguments.case_id and directory.name not in arguments.case_id:
            continue
        with np.load(directory / "instance.npz", allow_pickle=False) as archive:
            instance = {key: archive[key] for key in evaluate.INPUT_KEYS}
        output, execution = evaluate.run_candidate(arguments.submission.resolve(), instance, cpu_seconds=arguments.cpu_seconds)
        record = {"case_id": directory.name, "execution": execution,
                  "reference_available": (directory / "reference.npz").is_file(), "accepted": False}
        if output is not None:
            np.savez_compressed(output_directory / (directory.name + "_output.npz"), **output)
            if record["reference_available"]:
                with np.load(directory / "reference.npz", allow_pickle=False) as archive:
                    reference = archive["delta"]
                record["quality"] = evaluate.metrics(instance, output["delta"], output["z"], reference)
                record["accepted"] = evaluate.accepted(record["quality"])
            else:
                record["residual_only"] = evaluate.metrics(instance, output["delta"], output["z"], output["delta"])
        records.append(record)
        (output_directory / "progress.json").write_text(json.dumps(records, indent=2) + "\n")
        print(json.dumps(record), flush=True)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    protocol = json.loads((SIDECAR / "protocol.json").read_text())
    mismatches = [name for name, expected in protocol["active_sealed_files"].items()
                  if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected]
    assert not mismatches, mismatches
    report = {"submission": str(arguments.submission.resolve()),
              "solver_sha256": hashlib.sha256((arguments.submission / "solve.py").read_bytes()).hexdigest(),
              "policy_sha256": hashlib.sha256((ROOT / "evaluator/hidden/policy.json").read_bytes()).hexdigest(),
              "resources": {"cpu_seconds": arguments.cpu_seconds, "memory_mb": 2048, "threads": 1, "wall_seconds": 1800},
              "same_target_resource_test": arguments.cpu_seconds == 12,
              "cases": records, "accepted_count": sum(record["accepted"] for record in records),
              "case_count": len(records), "candidate_cpu_seconds_total": sum(record["execution"]["cpu_seconds"] for record in records),
              "candidate_cpu_seconds_max": max(record["execution"]["cpu_seconds"] for record in records),
              "aggregate_cpu_seconds": time.process_time() - started + children.ru_utime + children.ru_stime - child_start.ru_utime - child_start.ru_stime,
              "wall_seconds": time.monotonic() - started_wall,
              "active_seal_unchanged": True, "active_sealed_files_verified": len(protocol["active_sealed_files"]),
              "prospective_probe_only": True, "generation_promoted": False}
    (output_directory / "evaluation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "cases"}), flush=True)


if __name__ == "__main__":
    main()
