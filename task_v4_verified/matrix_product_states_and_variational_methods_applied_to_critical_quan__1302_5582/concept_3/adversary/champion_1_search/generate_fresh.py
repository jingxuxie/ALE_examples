import os
import sys

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import secrets
import time

import numpy as np


SIDECAR = Path(__file__).resolve().parent
CONCEPT = SIDECAR.parents[1]
sys.path.insert(0, str(CONCEPT / "evaluator/hidden"))
import teacher


FAMILIES = ("single_L2", "single_L3", "crossover_L2", "crossover_L3", "double_L2", "double_L3")
REGIMES = {"single": (0.35, 3.5), "crossover": (-1.4, 0.35), "double": (-4.2, -1.4)}
BATCHES = ("iid_0", "iid_1", "iid_2", "edge_0", "edge_1")


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def sample(generator, lower, upper, edge, logarithmic=False):
    if logarithmic:
        lower, upper = np.log(lower), np.log(upper)
    fraction = generator.uniform()
    if edge:
        fraction = 0.04 * fraction if generator.uniform() < 0.5 else 1.0 - 0.04 * fraction
    value = lower + fraction * (upper - lower)
    return float(np.exp(value) if logarithmic else value)


def generate_one(job):
    batch, family, ordinal, seed = job
    generator = np.random.default_rng(seed)
    regime, site_string = family.split("_L")
    edge = batch.startswith("edge")
    rejected = []
    for attempt in range(100):
        parameters = {
            "sites": int(site_string),
            "r": sample(generator, *REGIMES[regime], edge),
            "j": sample(generator, 0.12, 1.0, edge),
            "scale": sample(generator, 0.6, 1.6, edge, True),
            "omega": sample(generator, 0.30, 2.4, edge, True)
        }
        targets, certificate = teacher.certify(parameters)
        if targets is None:
            rejected.append({"parameters": parameters, "certificate": certificate})
            continue
        identifier = hashlib.sha256(("independent-audit-" + str(seed)).encode()).hexdigest()[:24]
        case = teacher.public_case(identifier, family, parameters)
        return {"batch": batch, "ordinal": ordinal, "case": case, "targets": targets,
                "certificate": certificate, "rejected": rejected}
    raise RuntimeError("No admitted fresh draw after 100 independent attempts")


def publish(batch, records):
    records = sorted(records, key=lambda record: record["case"]["id"])
    destination = SIDECAR / "private" / "batches" / batch
    write_json(destination / "labels.json", {"schema_version": 1, "predictions": [
        {"id": record["case"]["id"], "targets": record["targets"]} for record in records]})
    write_json(destination / "certificates.json", {"records": [
        {"id": record["case"]["id"], "certificate": record["certificate"]} for record in records]})
    write_json(destination / "inputs.json", {"schema_version": 1, "cases": [record["case"] for record in records]})
    print(json.dumps({"batch_ready": batch, "certified": len(records)}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    arguments = parser.parse_args()
    private = SIDECAR / "private"
    ledger_path = private / "fresh_seeds.json"
    hashes = {str(path.relative_to(CONCEPT)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in (CONCEPT / "participant").rglob("*") if path.is_file()}
    if not (private / "original_participant_hashes.json").exists():
        write_json(private / "original_participant_hashes.json", hashes)
    else:
        assert json.loads((private / "original_participant_hashes.json").read_text()) == hashes
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text())
    else:
        ledger = {"plan_sha256": hashlib.sha256((SIDECAR / "search_plan.json").read_bytes()).hexdigest(),
                  "teacher_sha256": hashlib.sha256((CONCEPT / "evaluator/hidden/teacher.py").read_bytes()).hexdigest(),
                  "jobs": [[batch, family, ordinal, secrets.randbits(128)] for batch in BATCHES
                           for family in FAMILIES for ordinal in range(12)]}
        write_json(ledger_path, ledger)
    assert ledger["plan_sha256"] == hashlib.sha256((SIDECAR / "search_plan.json").read_bytes()).hexdigest()
    assert ledger["teacher_sha256"] == hashlib.sha256((CONCEPT / "evaluator/hidden/teacher.py").read_bytes()).hexdigest()
    cache = private / "cache"
    cache.mkdir(exist_ok=True)
    collected = {batch: [] for batch in BATCHES}
    pending = []
    for job in ledger["jobs"]:
        path = cache / ("%s_%s_%02d.json" % tuple(job[:3]))
        if path.exists():
            collected[job[0]].append(json.loads(path.read_text()))
        else:
            pending.append(job)
    published = set()
    for batch in BATCHES:
        if len(collected[batch]) == 72:
            publish(batch, collected[batch])
            published.add(batch)
    started = time.monotonic()
    with concurrent.futures.ProcessPoolExecutor(max_workers=arguments.workers) as executor:
        futures = {executor.submit(generate_one, job): job for job in pending}
        for future in concurrent.futures.as_completed(futures):
            job = futures[future]
            result = future.result()
            write_json(cache / ("%s_%s_%02d.json" % tuple(job[:3])), result)
            collected[job[0]].append(result)
            completed = sum(len(records) for records in collected.values())
            if len(collected[job[0]]) == 72 and job[0] not in published:
                publish(job[0], collected[job[0]])
                published.add(job[0])
            if completed % 36 == 0:
                print(json.dumps({"completed": completed, "total": 360,
                                  "elapsed_seconds": round(time.monotonic() - started, 2)}), flush=True)
    all_records = [record for records in collected.values() for record in records]
    report = {"count": len(all_records), "batches": {batch: len(records) for batch, records in collected.items()},
              "rejected_candidates": sum(len(record["rejected"]) for record in all_records),
              "max_cutoff_log_change": max(float(np.max(record["certificate"]["last_two_cutoff_log_changes"]))
                                            for record in all_records),
              "max_basis_log_change": max(max(record["certificate"]["independent_basis_log_change"])
                                           for record in all_records),
              "max_residual_roundoff_gap_ratio": max(max(record["certificate"]["history"][-1]["residual_roundoff_gap_ratio"])
                                                     for record in all_records),
              "teacher_truth_extrapolated": False,
              "conditional_on_original_numerical_admission": True}
    write_json(private / "generation_summary.json", report)
    print(json.dumps(report, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
