"""Private, bounded active-constraint refinement of the archived fresh champion."""

import os
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import multiprocessing
from pathlib import Path
import subprocess
import sys
import time
import warnings

sys.dont_write_bytecode = True
import numpy as np
from scipy.optimize import linprog

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = json.loads((ROOT / "evaluator/resources/target.json").read_text())
WARMSTART = json.loads((ROOT / "champions/generation_1/witness.json").read_text())
RANDOM = np.random.default_rng(1488701)


def load_trusted(name):
    specification = importlib.util.spec_from_file_location("achievability_" + name, ROOT / "evaluator/resources" / (name + ".py"))
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


PROTOCOL = load_trusted("protocol")
WORKER = load_trusted("worker")


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def preservation_hashes():
    manifest = json.loads((ROOT / "freeze_manifest.json").read_text())
    paths = set(manifest["files"]) | {"status.json", "freeze_manifest.json", "BUILDER_REPORT.md"}
    paths.update(str(path.relative_to(ROOT)) for path in (ROOT / "champions/generation_1").rglob("*") if path.is_file())
    paths.add("generations/generation_0/archive_manifest.json")
    return {relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() for relative in sorted(paths)}


def make_witness(knots):
    return dict(WARMSTART, knots=np.asarray(knots, dtype=float).tolist())


def residuals(record):
    estimates = np.asarray(record["estimates"])
    differences = np.diff(estimates)
    return np.asarray([record["error"] / SPEC["error_min"] - 1.0,
                       1.0 - differences[0] / SPEC["spread_max"],
                       1.0 + differences[0] / SPEC["spread_max"],
                       1.0 - differences[1] / SPEC["spread_max"],
                       1.0 + differences[1] / SPEC["spread_max"]])


def merit(records):
    return float(min(np.min(residuals(record)) for record in records.values()))


def summary(records):
    return {"core_score": records["nominal"]["score"] if "nominal" in records else None,
            "worst_family_score": min(record["score"] for record in records.values()),
            "passed": all(record["passed"] for record in records.values()),
            "family_count": len(records), "minimum_residual": merit(records),
            "min_error": min(record["error"] for record in records.values()),
            "max_spread": max(record["spread"] for record in records.values()),
            "failed_waveforms": sum(not record["passed"] for record in records.values())}


def active_names(records, existing=()):
    chosen = set(existing)
    chosen.add("nominal")
    for coordinate in range(5):
        ordered = sorted(records, key=lambda name: residuals(records[name])[coordinate])
        chosen.update(ordered[:2])
    chosen.update(sorted(records, key=lambda name: np.min(residuals(records[name])))[:4])
    return sorted(chosen)


class Search:
    def __init__(self, pool, deadline):
        self.pool = pool
        self.deadline = deadline
        self.cache = {}
        self.candidates = set()
        self.waveform_count = 0
        self.full_suite_count = 0
        self.history = []
        self.started = time.monotonic()

    def event(self, kind, **values):
        event = {"kind": kind, "elapsed_seconds": time.monotonic() - self.started, **values}
        self.history.append(event)
        with (HERE / "history.jsonl").open("a") as stream:
            stream.write(json.dumps(event, allow_nan=False) + "\n")
        print(json.dumps(event, allow_nan=False), flush=True)

    def evaluate_batch(self, candidates, names):
        if time.monotonic() >= self.deadline:
            raise TimeoutError("private search deadline")
        jobs, keys, pending_keys = [], [], set()
        for knots in candidates:
            identity = tuple(float(value) for value in knots)
            self.candidates.add(identity)
            families = PROTOCOL.waveforms(make_witness(knots), SPEC)
            for name in names:
                key = (identity, name)
                if key not in self.cache and key not in pending_keys:
                    pending_keys.add(key)
                    jobs.append((name, families[name]))
                    keys.append(key)
        if jobs:
            results = self.pool.map(WORKER.evaluate_waveform, jobs, chunksize=1)
            for key, (_, record) in zip(keys, results):
                self.cache[key] = record
            self.waveform_count += len(jobs)
        return [{name: self.cache[(tuple(float(value) for value in knots), name)] for name in names} for knots in candidates]

    def full_suite(self, knots, label):
        names = list(PROTOCOL.waveforms(make_witness(knots), SPEC))
        records = self.evaluate_batch([knots], names)[0]
        self.full_suite_count += 1
        report = {"label": label, "witness": make_witness(knots), **summary(records), "families": records}
        write_json(HERE / "full_suites" / (label + ".json"), report)
        self.event("full_suite", label=label, **summary(records))
        return records


def search(seconds):
    before = preservation_hashes()
    write_json(HERE / "preservation_before.json", {"utc": datetime.now(timezone.utc).isoformat(), "hashes": before})
    freeze = json.loads((ROOT / "freeze_manifest.json").read_text())
    assert all(before[name] == expected for name, expected in freeze["files"].items())
    start = time.monotonic()
    deadline = start + seconds
    initial = np.asarray(WARMSTART["knots"], dtype=float)
    best = initial.copy()
    pool = multiprocessing.get_context("fork").Pool(4)
    experiment = Search(pool, deadline)
    best_records = None
    accepted = 0
    restarts = 0
    try:
        best_records = experiment.full_suite(initial, "initial")
        best_merit = merit(best_records)
        write_json(HERE / "best/witness.json", make_witness(best))
        current = best.copy()
        active = active_names(best_records)
        trust = 0.003
        failures = 0
        for iteration in range(80):
            if time.monotonic() > deadline - 70 or (best_records is not None and summary(best_records)["passed"]):
                break
            base_records = experiment.evaluate_batch([current], active)[0]
            base_vector = np.concatenate([residuals(base_records[name]) for name in active])
            derivative_step = 0.00004
            probes = [current + derivative_step * direction for direction in np.eye(6)]
            probe_records = experiment.evaluate_batch(probes, active)
            jacobian = np.column_stack([(np.concatenate([residuals(records[name]) for name in active]) - base_vector) / derivative_step for records in probe_records])
            matrix = np.column_stack([-jacobian, np.ones(len(base_vector))])
            objective = np.r_[np.zeros(6), -1.0]
            lower = np.maximum.reduce([np.full(6, -trust), initial - 0.035 - current, np.full(6, SPEC["knot_min"]) - current])
            upper = np.minimum.reduce([np.full(6, trust), initial + 0.035 - current, np.full(6, SPEC["knot_max"]) - current])
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                linear = linprog(objective, A_ub=matrix, b_ub=base_vector, bounds=list(zip(lower, upper)) + [(-5.0, 0.15)], method="highs-ds", options={"threads": 1})
            if not linear.success:
                experiment.event("linear_program_failed", iteration=iteration, message=linear.message)
                trust *= 0.5
                continue
            step = linear.x[:6]
            trial_knots = [current + fraction * step for fraction in [1.0, 0.5, 0.25]]
            trial_records = experiment.evaluate_batch(trial_knots, active)
            trial_merits = [merit(records) for records in trial_records]
            winner = int(np.argmax(trial_merits))
            improving = trial_merits[winner] > float(np.min(base_vector)) + 1e-6
            experiment.event("refinement", iteration=iteration, active_count=len(active), trust=trust, previous_merit=float(np.min(base_vector)), predicted_merit=float(linear.x[-1]), trial_merits=trial_merits, accepted=improving)
            if improving:
                current = trial_knots[winner]
                accepted += 1
                failures = 0
                trust = min(0.006, trust * (1.3 if winner == 0 else 0.75))
                if trial_merits[winner] > 0.0005 or accepted % 3 == 0:
                    records = experiment.full_suite(current, f"refinement_{iteration:02d}")
                    current_merit = merit(records)
                    active = active_names(records, active)
                    if current_merit > best_merit:
                        best, best_records, best_merit = current.copy(), records, current_merit
                        write_json(HERE / "best/witness.json", make_witness(best))
                        write_json(HERE / "best/search_score.json", {**summary(best_records), "families": best_records})
                        experiment.event("new_best", **summary(best_records))
                    if summary(records)["passed"]:
                        break
            else:
                failures += 1
                trust *= 0.5
            if failures >= 3 or trust < 0.00008:
                restarts += 1
                alternatives = [best + RANDOM.normal(0, 0.0015, 6) for _ in range(5)] + [best]
                alternative_records = experiment.evaluate_batch(alternatives, active)
                selected = int(np.argmax([merit(records) for records in alternative_records]))
                current = alternatives[selected].copy()
                trust, failures = 0.0015, 0
                experiment.event("restart", restart=restarts, selected=selected, active_merit=merit(alternative_records[selected]))
    except TimeoutError as error:
        experiment.event("deadline", reason=str(error))
    finally:
        pool.close()
        pool.join()
    search_seconds = time.monotonic() - start
    write_json(HERE / "best/witness.json", make_witness(best))
    command = [sys.executable, "-I", str(ROOT / "evaluator/evaluate.py"), "--submission", str(HERE / "best"), "--output", str(HERE / "best/trusted_score.json"), "--workers", "4"]
    graded = subprocess.run(command, cwd=HERE, text=True, capture_output=True, timeout=650, check=False)
    (HERE / "trusted_checker.log").write_text(graded.stdout + graded.stderr)
    trusted = json.loads((HERE / "best/trusted_score.json").read_text())
    after = preservation_hashes()
    changed = [name for name in before if after.get(name) != before[name]]
    write_json(HERE / "preservation_after.json", {"utc": datetime.now(timezone.utc).isoformat(), "hashes": after, "changed_files": changed, "unchanged": not changed})
    result = {"utc": datetime.now(timezone.utc).isoformat(), "method": "active-family sequential linear programming with trust region, finite differences and seeded local restarts", "warmstart": "champions/generation_1/witness.json", "seed": 1488701, "max_workers": 4, "blas_threads_per_worker": 1, "search_budget_seconds": seconds, "search_seconds": search_seconds, "total_seconds": time.monotonic() - start, "candidate_count": len(experiment.candidates), "waveform_evaluations": experiment.waveform_count, "mps_circuit_evaluations": 3 * experiment.waveform_count, "full_suite_evaluations": experiment.full_suite_count, "accepted_refinements": accepted, "restarts": restarts, "trusted_checker_waveforms": trusted.get("family_count"), "trusted_checker_seconds": trusted.get("elapsed_seconds"), "best_witness": "best/witness.json", "trusted_grade": "best/trusted_score.json", "core_score": trusted["core_score"], "worst_family_score": trusted["worst_family_score"], "resource_score": trusted["resource_score"], "valid": trusted["valid"], "passed": trusted["passed"], "reason": trusted["reason"], "frozen_assets_unchanged": not changed, "changed_files": changed, "no_active_v2_files_read": True, "model_calls": 0}
    write_json(HERE / "result.json", result)
    print(json.dumps(result, indent=2), flush=True)
    assert not changed
    assert graded.returncode == 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=600)
    options = parser.parse_args()
    search(options.seconds)


if __name__ == "__main__":
    main()
