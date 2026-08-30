import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import concurrent.futures
import datetime
import json
import math
import multiprocessing
from pathlib import Path
import time

import numpy as np

import continue_search as engine

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "two_root"


def save(name, document):
    path = OUTPUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, allow_nan=False) + "\n")


def main():
    os.sched_setaffinity(0, set(engine.CORES))
    started = time.monotonic()
    ending = datetime.datetime.fromisoformat("2026-08-28T22:36:55+00:00")
    deadline = started + max(0, (ending - datetime.datetime.now(datetime.timezone.utc)).total_seconds())
    base = json.loads((HERE / "seeds/v_2/witness.json").read_text())
    core, free = base["order"][:12], base["order"][12:]
    bonds = np.asarray(base["bonds"])
    candidates = []
    diagnostics = []
    for mask in range(1, 2**11):
        if time.monotonic() >= deadline - 120:
            break
        second_group = {core[position + 1] for position in range(11) if mask & (1 << position)}
        first_group = set(core) - second_group
        if min(len(first_group), len(second_group)) < 2:
            continue
        cut = sum(int(coupling) for coupling, (first, second) in zip(bonds, engine.verify.EDGES)
                  if first in core and second in core and ((first in first_group) != (second in first_group)))
        fields = []
        for site in free:
            fields.append(sum(int(coupling) for coupling, (first, second) in zip(bonds, engine.verify.EDGES)
                              if (first == site and second in first_group) or (second == site and first in first_group)))
        if cut != sum(abs(value) for value in fields) or max(abs(value) for value in fields) > 1:
            continue
        first_root = core[0]
        second_root = next(site for site in core if site in second_group)
        order = [first_root, second_root] + [site for site in core if site not in (first_root, second_root)] + free
        weights = np.zeros((16, 16))
        log_ratio = -2 * cut + sum(math.log(math.cosh(2 * value)) for value in fields)
        weights[1, 0] = -log_ratio
        if abs(weights[1, 0]) >= engine.verify.BOUND:
            continue
        for position in range(2, 12):
            weights[position, 0 if order[position] in first_group else 1] = engine.verify.BOUND - 1e-9
        for position, field in enumerate(fields, start=12):
            weights[position, 0] = 2 * field
            weights[position, 1] = -2 * field
        document = dict(base, beta=1.0, order=order, weights=weights.tolist())
        document, sector = engine.landscape.best_sector(document)
        report = engine.verify.evaluate(document)
        identifier = len(candidates)
        candidates.append((report["core_score"], identifier, document))
        diagnostics.append({"candidate": identifier, "partition_mask": mask, "cut": cut, "fields": fields,
                            "group_sizes": [len(first_group), len(second_group)], "log_phase_ratio": log_ratio,
                            "score": report["core_score"], "metrics": report["metrics"]})
        save(f"screen/{identifier:03d}/witness.json", document)
        save(f"screen/{identifier:03d}/independent_report.json", report)
    save("screen.json", diagnostics)
    print(json.dumps({"two_root_screened": len(candidates), "top_scores": [item[0] for item in sorted(candidates, reverse=True)[:5]]}), flush=True)
    context = multiprocessing.get_context("fork")
    event = context.Event()
    executor = concurrent.futures.ProcessPoolExecutor(max_workers=2, mp_context=context, initializer=engine.initialize, initargs=(event,))
    pending = {}
    queue = sorted(candidates, reverse=True)
    records = []
    best_score = -1.0
    best = None

    def retain(result):
        nonlocal best_score, best
        identifier = result["trial_id"]
        document, report = result.pop("witness"), result.pop("report")
        save(f"trials/{identifier:03d}/witness.json", document)
        save(f"trials/{identifier:03d}/independent_report.json", report)
        result.update(score=report["core_score"], metrics=report["metrics"], passed=report["passed"])
        records.append(result)
        if report["core_score"] > best_score:
            save("best/witness.json", document)
            best = engine.official(OUTPUT / "best")
            best_score = best["core_score"]
            print(json.dumps({"two_root_best_score": best_score, "passed": best["passed"], "metrics": best["metrics"]}), flush=True)
        save("trials.json", records)

    try:
        while time.monotonic() < deadline and (queue or pending) and not (best and best["passed"]):
            while len(pending) < 2 and queue:
                unused, identifier, document = queue.pop(0)
                job = {"trial_id": identifier, "family": "two_correlated_backbone_roots", "document": document,
                       "seed": 202608282232 + identifier, "deadline": deadline, "seconds": 80, "mode": "variance"}
                save(f"trials/{identifier:03d}/job.json", job)
                pending[executor.submit(engine.run_job, job)] = identifier
            finished, unused = concurrent.futures.wait(pending, timeout=1, return_when=concurrent.futures.FIRST_COMPLETED)
            for future in finished:
                identifier = pending.pop(future)
                try:
                    retain(future.result())
                except Exception as error:
                    records.append({"trial_id": identifier, "error": repr(error)})
    finally:
        event.set()
        executor.shutdown(wait=True, cancel_futures=True)
        for future, identifier in pending.items():
            if not future.cancelled():
                try:
                    retain(future.result())
                except Exception as error:
                    records.append({"trial_id": identifier, "error": repr(error)})
    save("trials.json", records)
    state = {"started_utc": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=time.monotonic() - started)).isoformat(),
             "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "elapsed_seconds": time.monotonic() - started,
             "screened_partitions": len(candidates), "completed_trials": len(records), "best_score": best_score,
             "passed": bool(best and best["passed"]), "attainability": "witnessed" if best and best["passed"] else "unknown",
             "scope": "binary torus; two degenerate backbone orientations; exact thermal phase odds and bounded free-spin root conditionals, followed by unrestricted coupled row refinement"}
    save("run.json", state)
    print(json.dumps(state, indent=2), flush=True)


if __name__ == "__main__":
    main()
