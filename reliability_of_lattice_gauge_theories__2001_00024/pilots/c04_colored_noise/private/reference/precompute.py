import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

PILOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PILOT / "private"))

from build_cases import reserved_cases
from engine import risk, solve, weak_solve
from scoring import FLOORS, raw_errors, score_result, summarize


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def precompute():
    started = time.perf_counter()
    shutil.copyfile(PILOT / "private/reference/engine.py", PILOT / "private/weak_baseline/engine.py")
    all_cases = reserved_cases()
    for split, reserved_set in all_cases.items():
        strong_records, weak_records = [], []
        for reserved in reserved_set:
            case = reserved["case"]
            filename = case["case_id"] + ".json"
            write_json(PILOT / "private/challenge_pool" / split / filename, reserved)
            timer = time.perf_counter()
            reference = solve(case)
            reference_seconds = time.perf_counter() - timer
            timer = time.perf_counter()
            weak = weak_solve(case)
            weak_seconds = time.perf_counter() - timer
            weak_errors, messages = raw_errors(case, weak, reference)
            if messages:
                raise RuntimeError(messages)
            label = dict(case_sha256=canonical_hash(case), reference=reference, weak=weak,
                         anchors={name: max(FLOORS[name], error) for name, error in weak_errors.items()},
                         reference_seconds=reference_seconds, weak_seconds=weak_seconds,
                         risks={identifier: risk(case, prediction) for identifier, prediction
                                in reference["predictions"].items()},
                         provenance="New benchmark-author secular reimplementation; not official author code")
            write_json(PILOT / "private/reference/outputs" / split / filename, label)
            for output, seconds, records in ((reference, reference_seconds, strong_records),
                                             (weak, weak_seconds, weak_records)):
                scored = score_result(case, output, label)
                scored.update(case_id=case["case_id"], family=reserved["family"], ok=True,
                              seconds=seconds, max_rss_kib=None, error=None)
                records.append(scored)
            print(f"{split} {reserved['family']} {case['case_id']} beta={reference['bath']['beta']} "
                  f"best={reference['selected_action']} ref={reference_seconds:.3f}s "
                  f"weak={weak_records[-1]['core']:.4f}", flush=True)
        for name, records in (("reference_precompute", strong_records), ("weak_precompute", weak_records)):
            report = summarize(records)
            report["validation_scope"] = "Trusted author precompute, not an isolated participant run"
            write_json(PILOT / "private/validation" / f"{name}_{split}.json", report)
    write_json(PILOT / "participant/input/example_case.json", all_cases["screening"][0]["case"])
    print(f"Precomputation elapsed: {time.perf_counter() - started:.2f}s", flush=True)


def freeze():
    files = [path for path in PILOT.rglob("*") if path.is_file()
             and "__pycache__" not in path.parts and path.name != "freeze.json"
             and "attempt" not in path.parts and not any(part.startswith(".evaluation-") for part in path.parts)]
    write_json(PILOT / "private/freeze.json", dict(
        protocol_version=1, generated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        hashes={str(path.relative_to(PILOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(files)},
        counts=dict(screening=9, challenge=6, confirmation=3), participant_attempts=0,
        confirmation_status="Reserved; author checks only, never participant tuning"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze-only", action="store_true")
    arguments = parser.parse_args()
    if arguments.freeze_only:
        freeze()
    else:
        precompute()
