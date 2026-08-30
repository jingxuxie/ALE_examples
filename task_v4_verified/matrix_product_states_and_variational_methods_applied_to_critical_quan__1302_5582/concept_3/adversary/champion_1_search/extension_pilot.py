import os
import sys

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import concurrent.futures
import hashlib
from pathlib import Path
import secrets
import shutil
import time

import numpy as np

from benchlib import SIDECAR, prepare, read, run_isolated, score, write
from extension_teacher import generate_case, native_spectrum


def seed_cases():
    ledger_path = SIDECAR / "private/extension_seeds.json"
    if ledger_path.exists():
        return read(ledger_path)["cases"]
    seed = secrets.randbits(128)
    generator = np.random.default_rng(seed)
    cases = []
    for sites, mass, coupling, inhomogeneous in ((4, -2.7, 0.95, False), (5, -2.3, 0.9, False), (6, -2.45, 0.85, True)):
        mass += generator.uniform(-0.04, 0.04)
        coupling += generator.uniform(-0.015, 0.015)
        case = {"id": hashlib.sha256((str(seed) + "-extension-" + str(sites)).encode()).hexdigest()[:24],
                "sites": sites, "mu2": float(mass), "lambda": 6.0, "kappa": float(coupling),
                "family": "double_L%d_%s" % (sites, "inhomogeneous" if inhomogeneous else "homogeneous"),
                "boundary": "open"}
        if inhomogeneous:
            case["mu2_by_site"] = (mass + generator.uniform(-0.25, 0.25, sites)).tolist()
            case["lambda_by_site"] = (6 * np.exp(generator.uniform(-0.2, 0.2, sites))).tolist()
            case["kappa_by_bond"] = (coupling * np.exp(generator.uniform(-0.15, 0.15, sites - 1))).tolist()
        cases.append(case)
    write(ledger_path, {"seed": seed, "cases": cases,
                       "plan_sha256": hashlib.sha256((SIDECAR / "extension_plan.json").read_bytes()).hexdigest()})
    return cases


def generate():
    cases = seed_cases()
    pending = [case for case in cases if not (SIDECAR / "private/extensions" / (case["id"] + ".json")).exists()]
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(generate_case, case): case for case in pending}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            write(SIDECAR / "private/extensions" / (result["case"]["id"] + ".json"), result)
            print({"reference_ready": result["case"]["sites"], "accepted": result["certificate"]["accepted"]}, flush=True)
    first = read(SIDECAR / "private/extensions" / (cases[0]["id"] + ".json"))
    crosscheck_path = SIDECAR / "private/native_fock_crosscheck.json"
    if first["certificate"]["accepted"] and not crosscheck_path.exists():
        records = [native_spectrum(first["case"], cutoff, 2.0) for cutoff in (16, 20, 24)]
        labels = first["certificate"]["label"]["targets"]
        discrepancies = {target: float(abs(np.log(records[-1]["signed_gaps"][target] / labels[target]))) for target in labels}
        write(crosscheck_path, {"case_id": first["case"]["id"], "records": records,
                               "compressed_vs_native_log_errors": discrepancies,
                               "max_log_error": max(discrepancies.values()),
                               "full_fock_validation_only_one_L4_case": True})
        print({"native_fock_crosscheck": max(discrepancies.values())}, flush=True)
    write(SIDECAR / "private/extension_generation_complete.json", {"complete": True})


def benchmark():
    original, limits = prepare()
    cases = seed_cases()
    deadline = time.monotonic() + 3600
    results = []
    for case in cases:
        path = SIDECAR / "private/extensions" / (case["id"] + ".json")
        while not path.exists():
            if time.monotonic() > deadline:
                raise RuntimeError("Extension teacher did not finish")
            time.sleep(2)
        reference = read(path)
        if not reference["certificate"]["accepted"]:
            results.append({"sites": case["sites"], "status": "uncertified_not_scored", "reason": reference["certificate"]["reason"]})
            continue
        inputs = {"schema_version": 1, "cases": [reference["case"]]}
        labels = {"schema_version": 1, "predictions": [reference["certificate"]["label"]]}
        for count in (4, 6, 8, 16):
            submission = SIDECAR / "control_submissions" / ("states_%d" % count)
            submission.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SIDECAR / "direct_control.py", submission / "predict.py")
            write(submission / "control.json", {"count": count})
            payload, timing = run_isolated(submission, inputs, limits)
            result = {"sites": case["sites"], "inhomogeneous": "mu2_by_site" in case,
                      "retained_local_states": count, "timing": timing,
                      "literal_champion_schema_error_counted": False}
            if payload is not None:
                result["metrics"] = score(payload, inputs, labels)
            results.append(result)
            write(SIDECAR / "extension_results.json", {"pilot_only": True, "runs": results,
                    "original_target_changed": False, "agent_launches": 0})
            print({"sites": case["sites"], "count": count, "timing": {key: value for key, value in timing.items() if key != "solver_diagnostics"},
                   "max_log_error": result.get("metrics", {}).get("max_log_error")}, flush=True)
    write(SIDECAR / "extension_results.json", {"complete": True, "pilot_only": True, "runs": results,
                    "original_target_changed": False, "agent_launches": 0})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("generate", "benchmark"))
    arguments = parser.parse_args()
    generate() if arguments.mode == "generate" else benchmark()


if __name__ == "__main__":
    main()
