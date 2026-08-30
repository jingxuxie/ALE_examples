import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import sys
import time

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                 "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS", "OMP_THREAD_LIMIT"):
    os.environ[variable] = "1"

PAPER = Path(__file__).resolve().parents[1]
GENERATION = PAPER / "concept_1/generations/generation_2"
ARTIFACTS = GENERATION / "adversary"
sys.path.insert(0, str(GENERATION / "participant/workspace"))
sys.path.insert(0, str(GENERATION / "evaluator"))

import numpy as np

from generators import FAMILIES, sample_fields
from physics import observables


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_records(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def create_artifact(path, payload):
    content = payload if isinstance(payload, str) else json.dumps(payload, indent=2, allow_nan=False) + "\n"
    if path.exists():
        if path.read_text() != content:
            raise RuntimeError(f"Refusing to overwrite existing artifact: {path.name}")
        return
    pending = path.with_name(path.name + ".pending")
    with pending.open("w") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.link(pending, path)
    pending.unlink()


def canonical(fields):
    values = np.asarray(fields, dtype=float)
    values = values - values.mean()
    return min(tuple(np.round(np.roll(orientation, shift), 11))
               for orientation in (values, -values, values[::-1], -values[::-1])
               for shift in range(len(values)))


def exclusions():
    paths = sorted((GENERATION / "participant/input").glob("*.jsonl"))
    paths.append(GENERATION / "evaluator/hidden/test.jsonl")
    seen, counts, hashes = set(), Counter(), {}
    for path in paths:
        hashes[str(path.relative_to(GENERATION))] = sha256(path)
        for case in read_records(path):
            if "fields" not in case:
                raise ValueError(f"Unexpected public/hidden record schema: {path.name}")
            seen.add(canonical(case["fields"]))
            counts[str(len(case["fields"]))] += 1
    for name in ("evaluator/physics.py", "evaluator/targets.json", "participant/workspace/generators.py"):
        hashes[name] = sha256(GENERATION / name)
    targets = json.loads((GENERATION / "evaluator/targets.json").read_text())
    if not targets["frozen"] or targets["target_length"] != 14:
        raise ValueError("Generation-two targets must already be frozen for L14")
    return seen, dict(counts), hashes


def validate_result(result, expected):
    for key in ("id", "L", "family", "fields", "batch"):
        if result[key] != expected[key]:
            raise ValueError("Checkpoint result does not match its planned case")
    if result["dimension"] != 3432 or not math.isfinite(result["f"]) or not 0 <= result["f"] <= 1:
        raise ValueError("Invalid exact L14 target")
    if not math.isfinite(result["min_gap"]) or result["min_gap"] <= 1e-12:
        raise ValueError("Invalid central spectral gap")


def resume_checkpoint(path, expected):
    completed = {}
    if not path.exists():
        return completed
    with path.open("rb+") as stream:
        while True:
            offset = stream.tell()
            line = stream.readline()
            if not line:
                break
            try:
                result = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                if stream.read(1):
                    raise ValueError("Corrupt nonfinal checkpoint record")
                stream.seek(offset)
                stream.truncate()
                break
            identity = result["id"]
            if identity not in expected or identity in completed:
                raise ValueError("Unknown or repeated checkpoint ID")
            validate_result(result, expected[identity])
            completed[identity] = result
            if not line.endswith(b"\n"):
                stream.write(b"\n")
    return completed


def simulate(case):
    started = time.monotonic()
    result = observables(case["fields"])
    output = dict(case, f=result["f"], min_gap=result["min_gap"],
                  dimension=result["dimension"], simulation_seconds=time.monotonic() - started)
    validate_result(output, case)
    return output


def prepare_plan(seen, counts, hashes):
    seed_path = ARTIFACTS / "replication_seed.json"
    plan_path = ARTIFACTS / "replication_plan.json"
    if seed_path.exists():
        seed_record = json.loads(seed_path.read_text())
        if seed_record["source_sha256"] != hashes:
            raise ValueError("Frozen sources changed since replication seed allocation")
    else:
        seed_record = {"created_utc": datetime.now(timezone.utc).isoformat(),
                       "batch_seeds": [secrets.randbits(128), secrets.randbits(128)],
                       "ordering_seed": secrets.randbits(128), "source_sha256": hashes,
                       "excluded_records_by_length": counts, "excluded_unique_symmetry_classes": len(seen),
                       "sampling_law": "Unmodified published generation-two L14 family generators and amplitude mixture",
                       "participant_visible": False}
        create_artifact(seed_path, seed_record)
    if plan_path.exists():
        plan = json.loads(plan_path.read_text())
        if plan["seed_sha256"] != sha256(seed_path):
            raise ValueError("Replication plan and seed archive differ")
        cases = plan["cases"]
    else:
        cases = []
        rejected = 0
        for batch, seed in enumerate(seed_record["batch_seeds"]):
            rng = np.random.default_rng(seed)
            for family in FAMILIES:
                for sample_index in range(80):
                    while True:
                        fields = sample_fields(rng, 14, family)
                        signature = canonical(fields)
                        if signature not in seen:
                            seen.add(signature)
                            break
                        rejected += 1
                    cases.append({"L": 14, "family": family, "fields": fields, "batch": batch})
        np.random.default_rng(seed_record["ordering_seed"]).shuffle(cases)
        cases = [dict(case, id=f"case_{index:05d}") for index, case in enumerate(cases)]
        plan = {"seed_sha256": sha256(seed_path), "cases": cases,
                "symmetry_collision_rejections": rejected,
                "ordering": "Global independent shuffle before neutral ID assignment; each batch remains stratified"}
        create_artifact(plan_path, plan)
        return plan, seed_record
    for case in cases:
        signature = canonical(case["fields"])
        if signature in seen:
            raise ValueError("Existing plan contains excluded or symmetry-duplicate fields")
        seen.add(signature)
    return plan, seed_record


def run(workers):
    available = set(os.sched_getaffinity(0))
    cpus = sorted(available.intersection(range(4, 20)))
    if not cpus:
        cpus = sorted(available.difference(range(4)))[:16]
    if not cpus:
        raise RuntimeError("No creator CPUs outside inference CPUs 0-3 are available")
    os.sched_setaffinity(0, cpus)
    workers = min(workers, len(cpus))
    manifest_path = ARTIFACTS / "replication_manifest.json"
    bank_path = ARTIFACTS / "replication_bank.jsonl"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if not manifest["complete"] or sha256(bank_path) != manifest["bank_sha256"]:
            raise ValueError("Existing completed replication artifact is invalid; refusing to overwrite")
        print(json.dumps({"already_complete": True, "records": manifest["records"],
                          "bank": str(bank_path), "bank_sha256": manifest["bank_sha256"]}), flush=True)
        return
    started = time.monotonic()
    seen, counts, hashes = exclusions()
    plan, seed_record = prepare_plan(seen, counts, hashes)
    cases = plan["cases"]
    if len(cases) != 640 or Counter((case["batch"], case["family"]) for case in cases) != Counter(
            {(batch, family): 80 for batch in (0, 1) for family in FAMILIES}):
        raise ValueError("Replication plan must contain two balanced 320-case batches")
    expected = {case["id"]: case for case in cases}
    if len(expected) != 640:
        raise ValueError("Duplicate planned IDs")
    checkpoint = ARTIFACTS / "replication_checkpoint.jsonl"
    completed = resume_checkpoint(checkpoint, expected)
    initial_count = len(completed)
    remaining = [case for case in cases if case["id"] not in completed]
    print(json.dumps({"started_utc": datetime.now(timezone.utc).isoformat(), "remaining": len(remaining),
                      "workers": workers, "creator_cpus": cpus, "blas_threads_per_worker": 1,
                      "inference_cpus_0_3_spared": True}), flush=True)
    with checkpoint.open("a") as stream, ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(simulate, case) for case in remaining]
        for future in as_completed(futures):
            result = future.result()
            completed[result["id"]] = result
            stream.write(json.dumps(result, allow_nan=False, separators=(",", ":")) + "\n")
            stream.flush()
            if len(completed) % 32 == 0:
                elapsed = time.monotonic() - started
                produced = len(completed) - initial_count
                eta = (640 - len(completed)) * elapsed / max(produced, 1)
                print(json.dumps({"completed": len(completed), "total": 640,
                                  "elapsed_seconds": round(elapsed, 1), "eta_seconds": round(eta, 1),
                                  "utc": datetime.now(timezone.utc).isoformat()}), flush=True)
    records = [{key: completed[case["id"]][key] for key in ("id", "L", "family", "fields", "batch", "f", "min_gap")}
               for case in cases]
    content = "".join(json.dumps(record, allow_nan=False, separators=(",", ":")) + "\n" for record in records)
    create_artifact(bank_path, content)
    batches = {}
    for batch in (0, 1):
        selected = [case for case in records if case["batch"] == batch]
        batches[str(batch)] = {"records": len(selected), "family_counts": dict(Counter(case["family"] for case in selected))}
    families = {}
    for family in FAMILIES:
        values = np.asarray([case["f"] for case in records if case["family"] == family])
        families[family] = {"records": len(values), "f_min": float(values.min()),
                            "f_max": float(values.max()), "f_mean": float(values.mean()), "f_std": float(values.std())}
    manifest = {"complete": True, "created_utc": seed_record["created_utc"],
                "completed_utc": datetime.now(timezone.utc).isoformat(), "concept": "concept_1",
                "generation": 2, "ratchet": 1, "purpose": "Independent private champion replication stress",
                "participant_visible": False, "records": 640, "length": 14,
                "bank_sha256": sha256(bank_path), "seed_sha256": sha256(ARTIFACTS / "replication_seed.json"),
                "plan_sha256": sha256(ARTIFACTS / "replication_plan.json"),
                "checkpoint_sha256": sha256(checkpoint), "builder_sha256": sha256(Path(__file__)),
                "source_sha256": hashes, "excluded_records_by_length": counts,
                "excluded_unique_symmetry_classes": seed_record["excluded_unique_symmetry_classes"],
                "cross_source_and_within_replication_symmetry_duplicates": 0,
                "ordering": plan["ordering"], "batches": batches, "families": families,
                "workers_last_session": workers, "creator_cpus_last_session": cpus,
                "blas_threads_per_worker": 1, "last_session_seconds": time.monotonic() - started,
                "minimum_field_separation": min(float(np.min(np.diff(np.sort(case["fields"])))) for case in records),
                "minimum_central_spectral_gap": min(case["min_gap"] for case in records),
                "exact_physics": {"dimension": 3432, "central_ranks_zero_based": [1144, 2288],
                                  "observable": "Pal-Huse Eq. 6 mean of eigenstate ratios", "dtype": "float64", "driver": "evr"},
                "fresh_agents_launched": False, "submissions_inspected_or_scored": False}
    create_artifact(manifest_path, manifest)
    print(json.dumps({"ready": True, "records": 640, "manifest": str(manifest_path),
                      "bank_sha256": manifest["bank_sha256"]}), flush=True)


def main():
    parser = argparse.ArgumentParser(description="Build or resume the private, disjoint 640-case L14 replication bank.")
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    if not 1 <= args.workers <= 16:
        parser.error("--workers must be between 1 and 16")
    with (ARTIFACTS / "replication_build.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("A replication builder already holds the lock")
        run(args.workers)


if __name__ == "__main__":
    main()
