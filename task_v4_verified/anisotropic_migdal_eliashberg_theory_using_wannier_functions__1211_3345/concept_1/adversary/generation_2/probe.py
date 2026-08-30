"""Generate physical cases, evaluate actual v3, and independently certify branches."""

import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"
sys.dont_write_bytecode = True
import numpy as np
from materials import make

PENDING = Path(__file__).resolve().parent
ROOT = PENDING.parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
import evaluate


def cpu():
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    return time.process_time() + children.ru_utime + children.ru_stime


def main():
    started = cpu()
    plan = json.loads((PENDING / "probe_plan.json").read_text())
    (PENDING / "scratch").mkdir(exist_ok=True)
    tempfile.tempdir = str(PENDING / "scratch")
    results = []
    for specification in plan["cases"]:
        if cpu() - started > plan["search_cpu_ceiling_seconds"] - 120:
            break
        directory = PENDING / "cases" / specification["case_id"]
        directory.mkdir(parents=True)
        generation_started = cpu()
        instance, metadata, modes = make(specification)
        np.savez_compressed(directory / "instance.npz", **instance)
        np.savez_compressed(directory / "private_initial_modes.npz", modes=modes)
        metadata["instance_sha256"] = hashlib.sha256((directory / "instance.npz").read_bytes()).hexdigest()
        (directory / "parameters.json").write_text(json.dumps(metadata, indent=2) + "\n")
        print(json.dumps({"case_id": specification["case_id"], "phase": "generated",
                          "linear_eigenvalue": metadata["linear_eigenvalue"],
                          "generation_cpu_seconds": cpu() - generation_started}), flush=True)
        output, execution = evaluate.run_candidate(ROOT / "champions" / "generation_2", instance)
        record = {"case_id": specification["case_id"], "family": specification["family"], "execution": execution}
        if output is not None:
            np.savez_compressed(directory / "actual_v3_output.npz", **output)
            record["self_reference_metrics"] = evaluate.metrics(instance, output["delta"], output["z"], output["delta"])
            record["actual_low_gap_max_over_piT"] = float(np.max(output["delta"][:, 0]) / (np.pi * float(instance["temperature"])))
        command = [sys.executable, "-B", str(PENDING / "certify.py"), "--case", str(directory), "--cpu-seconds", "50"]
        with (directory / "reference.log").open("wb") as log:
            worker = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log, timeout=1800)
        record["reference_worker_returncode"] = worker.returncode
        certificate_path = directory / "certificate.json"
        if certificate_path.exists():
            certificate = json.loads(certificate_path.read_text())
            record["reference_valid"] = certificate["valid"]
            record["cross_start_error"] = certificate["second_start_all_frequency"]["branch_error"]
            if certificate["valid"] and output is not None:
                with np.load(directory / "reference.npz", allow_pickle=False) as archive:
                    reference = archive["delta"]
                record["quality"] = evaluate.metrics(instance, output["delta"], output["z"], reference)
                record["actual_v3_accepted"] = evaluate.accepted(record["quality"])
        record["aggregate_cpu_seconds"] = cpu() - started
        (directory / "measurement.json").write_text(json.dumps(record, indent=2) + "\n")
        results.append(record)
        (PENDING / "probe_report.json").write_text(json.dumps({"cases": results, "aggregate_cpu_seconds": cpu() - started}, indent=2) + "\n")
        print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
