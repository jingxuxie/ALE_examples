"""Privileged finite calibration-drift audit; never modifies the frozen task."""

import os
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import datetime
import hashlib
import importlib.util
import itertools
import json
import multiprocessing
from pathlib import Path
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RESOURCES = ROOT / "evaluator" / "resources"


def load_module(name):
    specification = importlib.util.spec_from_file_location("generation_1_" + name, RESOURCES / (name + ".py"))
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


ENGINE = load_module("simulator")
REFERENCE = load_module("reference")
PROTOCOL = load_module("protocol")
SPEC = json.loads((RESOURCES / "target.json").read_text())
SCALES = (0.0001, 0.00025, 0.0005, 0.001, 0.002)
SEED = 148872026


def directions():
    records = []
    for index, direction in enumerate(itertools.product((-1.0, 1.0), repeat=6)):
        records.append(("corners", f"corner_{index:02d}", list(direction)))
    random = np.random.default_rng(SEED)
    for index in range(12):
        records.append(("random", f"random_{index:02d}", random.uniform(-1, 1, 6).tolist()))
    for knot in range(6):
        for sign in (-1, 1):
            direction = np.zeros(6)
            direction[knot] = sign
            records.append(("structured", f"knot_{knot}_{sign:+d}", direction.tolist()))
    for sign in (-1, 1):
        records.append(("structured", f"alternating_{sign:+d}", [float(sign * (-1) ** index) for index in range(6)]))
    return records


def simulate_case(job):
    champion, witness, epsilon, suite, name, direction = job
    started = time.monotonic()
    shifted = dict(witness, knots=(np.asarray(witness["knots"]) + epsilon * np.asarray(direction)).tolist())
    result = {"champion": champion, "epsilon": epsilon, "suite": suite, "name": name,
              "direction": direction, "witness": shifted, "families": {}, "valid": False}
    try:
        families = PROTOCOL.waveforms(shifted, SPEC)
    except ValueError as error:
        result.update(passed=False, reason=str(error), elapsed_seconds=time.monotonic() - started)
        return result
    result["valid"] = True
    result["constraints"] = {"minimum_angle": float(min(np.min(angles) for angles in families.values())),
                             "maximum_angle": float(max(np.max(angles) for angles in families.values())),
                             "maximum_slew": float(max(np.max(np.abs(np.diff(angles))) for angles in families.values()))}
    for family, angles in families.items():
        truth = REFERENCE.zz1(REFERENCE.exact_state(angles))
        estimates, diagnostics = [], {}
        for chi in SPEC["chis"]:
            state, diagnostic = ENGINE.mps_state(angles, chi)
            estimates.append(REFERENCE.zz1(state))
            diagnostics[str(chi)] = diagnostic
        record = PROTOCOL.metrics(truth, estimates, SPEC)
        spread_fail = record["spread"] > SPEC["spread_max"]
        error_fail = record["error"] < SPEC["error_min"]
        record["failure_type"] = "both" if spread_fail and error_fail else "spread_only" if spread_fail else "error_only" if error_fail else "pass"
        record["limiting_pair"] = "4_8" if abs(estimates[1] - estimates[0]) >= abs(estimates[2] - estimates[1]) else "8_16"
        record["diagnostics"] = diagnostics
        result["families"][family] = record
    result["passed"] = all(record["passed"] for record in result["families"].values())
    result["minimum_error"] = min(record["error"] for record in result["families"].values())
    result["maximum_spread"] = max(record["spread"] for record in result["families"].values())
    result["worst_family_score"] = min(record["score"] for record in result["families"].values())
    result["elapsed_seconds"] = time.monotonic() - started
    return result


def summarize(records):
    groups = {}
    for record in records:
        key = f"{record['champion']}|{record['epsilon']:.7f}|{record['suite']}"
        group = groups.setdefault(key, {"champion": record["champion"], "epsilon": record["epsilon"],
                                        "suite": record["suite"], "cases": 0, "valid": 0, "passed": 0,
                                        "failing_families": Counter(), "limiting_pairs": Counter(),
                                        "maximum_spread": 0.0, "minimum_error": 2.0,
                                        "worst_family_score": 100.0, "strongest_spread_case": None})
        group["cases"] += 1
        group["valid"] += int(record["valid"])
        group["passed"] += int(record["passed"])
        if not record["valid"]:
            continue
        group["minimum_error"] = min(group["minimum_error"], record["minimum_error"])
        group["worst_family_score"] = min(group["worst_family_score"], record["worst_family_score"])
        for family, item in record["families"].items():
            if not item["passed"]:
                group["failing_families"][item["failure_type"]] += 1
                group["limiting_pairs"][item["limiting_pair"]] += 1
            if item["spread"] > group["maximum_spread"]:
                group["maximum_spread"] = item["spread"]
                group["strongest_spread_case"] = {"name": record["name"], "family": family,
                                                   "error": item["error"], "spread": item["spread"],
                                                   "direction": record["direction"], "estimates": item["estimates"],
                                                   "exact": item["exact"]}
    return list(groups.values())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    options = parser.parse_args()
    if not 1 <= options.workers <= 4:
        parser.error("use one to four single-threaded workers")
    witnesses = {"fresh": json.loads((ROOT / "champions" / "generation_1" / "witness.json").read_text()),
                 "builder": json.loads((ROOT / "champions" / "builder" / "witness.json").read_text())}
    manifest = json.loads((ROOT / "freeze_manifest.json").read_text())
    changes = [name for name, digest in manifest["files"].items() if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
    if changes:
        raise RuntimeError("frozen files changed: " + repr(changes))
    plan = {"started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "scales": SCALES,
            "random_seed": SEED, "directions_per_scale_per_champion": len(directions()),
            "families_per_case": 5, "workers": options.workers, "blas_threads_per_worker": 1,
            "original_target_sha256": manifest["target_sha256"], "witnesses": witnesses,
            "definition": "Add epsilon*direction independently to the six knots, then apply each original global offset/tilt family. No threshold or circuit changes."}
    (HERE / "sweep_plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    jobs = [(champion, witness, 0.0, "baseline", "unchanged", [0.0] * 6) for champion, witness in witnesses.items()]
    for epsilon in SCALES:
        for suite, name, direction in directions():
            for champion, witness in witnesses.items():
                jobs.append((champion, witness, epsilon, suite, name, direction))
    records = []
    started = time.monotonic()
    with (HERE / "sweep.jsonl").open("w") as stream:
        with ProcessPoolExecutor(max_workers=options.workers, mp_context=multiprocessing.get_context("fork")) as pool:
            for record in pool.map(simulate_case, jobs, chunksize=1):
                records.append(record)
                stream.write(json.dumps(record, allow_nan=False) + "\n")
                stream.flush()
                if len(records) % 20 == 0 or len(records) == len(jobs):
                    progress = {"completed": len(records), "total": len(jobs), "elapsed_seconds": time.monotonic() - started,
                                "last_scale": record["epsilon"], "groups": summarize(records)}
                    (HERE / "progress.json").write_text(json.dumps(progress, indent=2) + "\n")
                    print(json.dumps({key: progress[key] for key in ("completed", "total", "elapsed_seconds", "last_scale")}), flush=True)
    report = {"complete": True, "cases": len(records), "physical_waveforms": sum(len(record["families"]) for record in records),
              "elapsed_seconds": time.monotonic() - started, "groups": summarize(records)}
    (HERE / "summary.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
