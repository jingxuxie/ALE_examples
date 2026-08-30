"""Isolated exact-fresh-solver sweep; extended runs are explicitly not scored passes."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import tempfile
import time

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"
import numpy as np

PENDING = Path(__file__).resolve().parent
ROOT = PENDING.parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
import evaluate
from materials import make
from verification import direct_rows, metrics


def usage():
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    return time.process_time() + children.ru_utime + children.ru_stime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", nargs="*")
    parser.add_argument("--cpu-ceiling", type=int, default=1200)
    arguments = parser.parse_args()
    evaluate.POLICY = dict(evaluate.POLICY, output_bytes_max=32 * 1024 ** 2)
    (PENDING / "scratch").mkdir(exist_ok=True)
    tempfile.tempdir = str(PENDING / "scratch")
    records = []
    for specification in json.loads((PENDING / "probe_plan.json").read_text())["specifications"]:
        if arguments.cases and specification["case_id"] not in arguments.cases:
            continue
        if usage() > arguments.cpu_ceiling - 150:
            break
        directory = PENDING / "probes" / specification["case_id"]
        directory.mkdir(parents=True, exist_ok=True)
        started = usage()
        instance, metadata = make(specification)
        np.savez_compressed(directory / "instance.npz", **instance)
        metadata["instance_sha256"] = hashlib.sha256((directory / "instance.npz").read_bytes()).hexdigest()
        (directory / "parameters.json").write_text(json.dumps(metadata, indent=2) + "\n")
        print(json.dumps({"case_id": specification["case_id"], "phase": "generated", "aggregate_cpu_seconds": usage()}), flush=True)
        output, execution = evaluate.run_candidate(ROOT / "champions" / "generation_1", instance)
        measurement = {"case_id": specification["case_id"], "family": specification["family"],
                       "standard_12_cpu_execution": execution, "generation_cpu_seconds": usage() - started - execution["cpu_seconds"]}
        primary = output
        if primary is None:
            primary, diagnostic = evaluate.run_candidate(ROOT / "champions" / "generation_1", instance, cpu_seconds=96)
            measurement["extended_96_cpu_execution"] = diagnostic
        else:
            measurement["extended_96_cpu_execution"] = None
        if primary is None:
            measurement["reference_valid"] = False
            measurement["failure_cluster"] = "execution_or_memory_failure_even_with_extended_CPU"
            (directory / "measurement.json").write_text(json.dumps(measurement, indent=2) + "\n")
            records.append(measurement)
            print(json.dumps(measurement), flush=True)
            continue
        primary_metrics = metrics(instance, primary["delta"], primary["z"], primary["delta"])
        second_instance = dict(instance, initial_delta=2.7 * instance["initial_delta"])
        secondary, second_execution = evaluate.run_candidate(ROOT / "champions" / "generation_1", second_instance, cpu_seconds=96)
        measurement["second_start_execution"] = second_execution
        if secondary is None:
            measurement["reference_valid"] = False
        else:
            second_metrics = metrics(instance, secondary["delta"], secondary["z"], primary["delta"])
            primary_direct = direct_rows(instance, primary["delta"], primary["z"])
            second_direct = direct_rows(instance, secondary["delta"], secondary["z"])
            amplitude = float(np.max(primary["delta"][:, 0]) / (np.pi * float(instance["temperature"])))
            valid = (primary_metrics["gap_residual"] < 5e-11 and primary_metrics["z_residual"] < 5e-11
                     and second_metrics["gap_residual"] < 5e-11 and second_metrics["z_residual"] < 5e-11
                     and second_metrics["branch_error"] < 2e-6 and primary_metrics["sign_correct"]
                     and second_metrics["sign_correct"] and amplitude > 1e-4
                     and primary_direct["gap_residual"] < 5e-11 and primary_direct["z_residual"] < 5e-11
                     and second_direct["gap_residual"] < 5e-11 and second_direct["z_residual"] < 5e-11)
            certificate = {"valid": bool(valid), "case_id": specification["case_id"],
                           "instance_sha256": metadata["instance_sha256"], "primary_all_frequency": primary_metrics,
                           "second_start_all_frequency": second_metrics, "primary_direct_rows": primary_direct,
                           "second_start_direct_rows": second_direct, "nonzero_amplitude_over_piT": amplitude,
                           "independent_verifier": "full_signed_zero_padded_linear_convolution_plus_direct_rows",
                           "initial_factors": [1.0, 2.7], "offline_extended_budget_is_not_a_12_second_witness": True}
            if valid:
                np.savez_compressed(directory / "reference.npz", **primary)
                certificate["reference_sha256"] = hashlib.sha256((directory / "reference.npz").read_bytes()).hexdigest()
            (directory / "certificate.json").write_text(json.dumps(certificate, indent=2) + "\n")
            measurement["reference_valid"] = bool(valid)
        measurement["primary_quality"] = primary_metrics
        measurement["failure_cluster"] = "CPU_limit" if output is None else ("none" if evaluate.accepted(primary_metrics) else "quality")
        diagnostic = measurement["extended_96_cpu_execution"]
        measurement["resource_failure_well_outside_12_cpu"] = bool(output is None and diagnostic and diagnostic["cpu_seconds"] >= 24 and primary is not None)
        measurement["total_probe_cpu_seconds"] = usage() - started
        records.append(measurement)
        (directory / "measurement.json").write_text(json.dumps(measurement, indent=2) + "\n")
        print(json.dumps(measurement), flush=True)
        (PENDING / "probe_report.json").write_text(json.dumps({"active": False, "records": records,
                                                               "aggregate_cpu_seconds": usage()}, indent=2) + "\n")


if __name__ == "__main__":
    main()
