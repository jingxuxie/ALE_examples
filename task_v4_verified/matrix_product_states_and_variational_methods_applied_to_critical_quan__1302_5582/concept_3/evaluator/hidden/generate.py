import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import secrets
import time

import numpy as np

from teacher import certify, public_case


ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / "evaluator" / "hidden"
REGIMES = {"single": (0.35, 3.5), "crossover": (-1.4, 0.35), "double": (-4.2, -1.4)}


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def generate_one(job):
    split, family, ordinal, seed = job
    regime, site_string = family.split("_L")
    generator = np.random.default_rng(seed)
    rejected = []
    for candidate in range(100):
        parameters = {
            "sites": int(site_string),
            "r": float(generator.uniform(*REGIMES[regime])),
            "j": float(generator.uniform(0.12, 1.0)),
            "scale": float(np.exp(generator.uniform(np.log(0.6), np.log(1.6)))),
            "omega": float(np.exp(generator.uniform(np.log(0.30), np.log(2.4))))
        }
        targets, certificate = certify(parameters)
        if targets is None:
            rejected.append({"parameters": parameters, "details": certificate})
            continue
        case_id = hashlib.sha256(str(seed).encode() + b"opaque-case-id").hexdigest()[:20]
        case = public_case(case_id, family, parameters)
        return {"split": split, "family": family, "ordinal": ordinal, "case": case,
                "targets": targets, "certificate": certificate, "rejected_candidates": rejected}
    raise RuntimeError("No certifiable candidate after 100 draws")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--pilot", action="store_true")
    arguments = parser.parse_args()
    contract_path = PRIVATE / "target_contract.json"
    contract = json.loads(contract_path.read_text())
    contract_digest = hashlib.sha256(contract_path.read_bytes()).hexdigest()
    ledger_path = PRIVATE / ("pilot_seeds.json" if arguments.pilot else "generation_seeds.json")
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text())
        if ledger["contract_sha256"] != contract_digest:
            raise RuntimeError("Frozen target changed")
    else:
        jobs = []
        for split, count in contract["counts_per_family"].items():
            if arguments.pilot and split != "train":
                continue
            for family in contract["families"]:
                for ordinal in range(1 if arguments.pilot else count):
                    jobs.append([split, family, ordinal, secrets.randbits(128)])
        ledger = {"contract_sha256": contract_digest, "jobs": jobs}
        write_json(ledger_path, ledger)
    cache = PRIVATE / ("pilot_cache" if arguments.pilot else "teacher_cache")
    cache.mkdir(exist_ok=True)
    jobs = ledger["jobs"]
    pending = []
    for job in jobs:
        filename = cache / ("%s_%s_%03d.json" % tuple(job[:3]))
        if not filename.exists():
            pending.append(job)
    started = time.monotonic()
    completed = len(jobs) - len(pending)
    with concurrent.futures.ProcessPoolExecutor(max_workers=arguments.workers) as executor:
        futures = {executor.submit(generate_one, job): job for job in pending}
        for future in concurrent.futures.as_completed(futures):
            job = futures[future]
            result = future.result()
            write_json(cache / ("%s_%s_%03d.json" % tuple(job[:3])), result)
            completed += 1
            if arguments.pilot or completed % 24 == 0 or completed == len(jobs):
                print(json.dumps({"completed": completed, "total": len(jobs),
                                  "elapsed_seconds": round(time.monotonic() - started, 1),
                                  "last_cutoff": result["certificate"]["label_cutoff"]}), flush=True)
    if arguments.pilot:
        return
    records = [json.loads((cache / ("%s_%s_%03d.json" % tuple(job[:3]))).read_text()) for job in jobs]
    all_certificates = []
    for split in ("train", "validation", "hidden"):
        selected = sorted((record for record in records if record["split"] == split),
                          key=lambda record: record["case"]["id"])
        cases = [record["case"] for record in selected]
        labels = [{"id": record["case"]["id"], "targets": record["targets"]} for record in selected]
        if split == "train":
            training = [dict(case, targets=label["targets"]) for case, label in zip(cases, labels)]
            write_json(ROOT / "participant/input/train.json", {"schema_version": 1, "cases": training})
        else:
            destination = ROOT / "participant/input" if split == "validation" else PRIVATE
            prefix = "validation" if split == "validation" else "test"
            write_json(destination / (prefix + "_inputs.json"), {"schema_version": 1, "cases": cases})
            write_json(destination / (prefix + "_labels.json"), {"schema_version": 1, "predictions": labels})
        for record in selected:
            all_certificates.append(dict(record["certificate"], id=record["case"]["id"],
                                         split=split, family=record["family"]))
    write_json(PRIVATE / "certificates.json", {"schema_version": 1, "certificates": all_certificates})
    summary = {
        "contract_sha256": contract_digest,
        "counts": {split: sum(record["split"] == split for record in records)
                   for split in ("train", "validation", "hidden")},
        "rejected_candidates": sum(len(record["rejected_candidates"]) for record in records),
        "teacher_solve_seconds": sum(sum(item["seconds"] for item in certificate["history"])
                                     + certificate["independent_basis"]["seconds"]
                                     for certificate in all_certificates),
        "label_cutoffs": {str(cutoff): sum(certificate["label_cutoff"] == cutoff
                                          for certificate in all_certificates)
                          for cutoff in sorted(set(certificate["label_cutoff"] for certificate in all_certificates))},
        "max_cutoff_log_change": max(np.max(certificate["last_two_cutoff_log_changes"])
                                      for certificate in all_certificates),
        "max_basis_log_change": max(max(certificate["independent_basis_log_change"])
                                     for certificate in all_certificates),
        "max_residual_roundoff_gap_ratio": max(max(item["residual_roundoff_gap_ratio"])
            for certificate in all_certificates for item in
            (certificate["history"][-1], certificate["independent_basis"])),
        "max_state_residual": max(float(np.max(item["state_residuals_dimensionless"]))
            for certificate in all_certificates for item in
            (certificate["history"][-1], certificate["independent_basis"])),
        "target_ranges": {target: [min(record["targets"][target] for record in records),
                                    max(record["targets"][target] for record in records)]
                          for target in contract["targets"]},
        "rigorous_infinite_cutoff_bound": False,
        "truth_extrapolated": False,
        "numpy_version": np.__version__
    }
    write_json(PRIVATE / "teacher_summary.json", summary)
    print(json.dumps(summary, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
