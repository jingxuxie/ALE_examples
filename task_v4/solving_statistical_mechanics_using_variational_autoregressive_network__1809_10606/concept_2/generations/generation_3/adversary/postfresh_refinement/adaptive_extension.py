import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import concurrent.futures
import datetime
import hashlib
import heapq
import json
import multiprocessing
from pathlib import Path
import time

import numpy as np

import continue_search as engine

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "extension"


def save(name, document):
    path = OUTPUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, allow_nan=False) + "\n")


def main():
    os.sched_setaffinity(0, set(engine.CORES))
    started = time.monotonic()
    ending = datetime.datetime.fromisoformat("2026-08-28T22:43:25+00:00")
    deadline = started + max(0, (ending - datetime.datetime.now(datetime.timezone.utc)).total_seconds())
    generator = np.random.default_rng(202608282237)
    while "finished_utc" not in json.loads((HERE / "adaptive/run.json").read_text()):
        time.sleep(1)
    initial = json.loads((HERE / "adaptive/best/witness.json").read_text())
    save("best/witness.json", initial)
    best = engine.official(OUTPUT / "best")
    state = {"seed": 202608282237, "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "deadline_utc": ending.isoformat(), "workers": 4, "affinity": engine.CORES,
             "best_score": best["core_score"], "passed": best["passed"], "completed_trials": 0,
             "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             "method": "remaining authorized search time: adaptive order compositions and parent reassignment; revisit orders after a meaningful seed improvement; hard stop within 20 minutes of numerical search"}
    save("run.json", state)
    queue = []
    seen = {}
    counter = 0

    def expand(document, quality, parent):
        nonlocal counter
        variants = []
        for position in generator.permutation(np.arange(1, 16)):
            order = list(document["order"])
            order[position - 1], order[position] = order[position], order[position - 1]
            variants.append(("composed_adjacent_swap", document, order, int(position)))
        for row in (2, 3, 6, 7, 8, 10):
            weights = np.asarray(document["weights"]).copy()
            if row <= 1 or np.max(np.abs(weights[row])) < engine.verify.BOUND - .01:
                continue
            old_parent = int(np.argmax(np.abs(weights[row])))
            for new_parent in generator.choice(row, size=min(row, 2), replace=False):
                if new_parent == old_parent:
                    continue
                weights = np.asarray(document["weights"]).copy()
                sign = float(np.sign(weights[row, old_parent]))
                weights[row] = 0
                weights[row, new_parent] = sign * (engine.verify.BOUND - 1e-9)
                variant = dict(document, weights=weights.tolist())
                variants.append(("saturated_parent_reassignment", variant, document["order"], (row, int(new_parent))))
        for family, seed_document, order, variation in variants:
            identity = (tuple(seed_document["bonds"]), tuple(order), family, str(variation) if family != "composed_adjacent_swap" else "")
            if identity in seen and quality <= seen[identity] + .002:
                continue
            seen[identity] = quality
            job = {"trial_id": counter, "family": family, "document": seed_document, "order": order,
                   "seed": int(generator.integers(0, 2**31)), "deadline": deadline, "seconds": 70, "parent": parent}
            heapq.heappush(queue, (-quality, counter, job))
            counter += 1

    expand(initial, best["core_score"], "initial_private_best")
    context = multiprocessing.get_context("fork")
    event = context.Event()
    executor = concurrent.futures.ProcessPoolExecutor(max_workers=4, mp_context=context, initializer=engine.initialize, initargs=(event,))
    pending = {}
    records = []
    last_external = best["core_score"]

    def retain(result):
        report = result.pop("report")
        document = result.pop("witness")
        identifier = result["trial_id"]
        save(f"trials/{identifier:04d}/witness.json", document)
        save(f"trials/{identifier:04d}/independent_report.json", report)
        result.update(score=report["core_score"], passed=report["passed"], metrics=report["metrics"])
        records.append(result)
        state["completed_trials"] = len(records)
        if report["core_score"] > state["best_score"] + 1e-7 or report["passed"]:
            checked = engine.official(OUTPUT / f"trials/{identifier:04d}")
            if checked["core_score"] > state["best_score"] or checked["passed"]:
                save("best/witness.json", document)
                save("adaptive/best/official_report.json", checked)
                state.update(best_score=checked["core_score"], passed=checked["passed"], best_trial=identifier)
                print(json.dumps({"adaptive_elapsed_seconds": time.monotonic() - started, "trial": identifier,
                                  "score": checked["core_score"], "passed": checked["passed"], "metrics": checked["metrics"]}), flush=True)
                expand(document, checked["core_score"], identifier)
        save("trials.json", records)
        save("run.json", state)

    try:
        while time.monotonic() < deadline and not state["passed"] and (queue or pending):
            external = json.loads((HERE / "adaptive/best/official_report.json").read_text())
            if external["passed"]:
                break
            if external["core_score"] > last_external + 1e-7:
                document = json.loads((HERE / "adaptive/best/witness.json").read_text())
                expand(document, external["core_score"], "new_main_private_best")
                last_external = external["core_score"]
            while len(pending) < 4 and queue:
                unused, identifier, job = heapq.heappop(queue)
                save(f"trials/{identifier:04d}/job.json", job)
                pending[executor.submit(engine.run_job, job)] = identifier
            finished, unused = concurrent.futures.wait(pending, timeout=1, return_when=concurrent.futures.FIRST_COMPLETED)
            for future in finished:
                identifier = pending.pop(future)
                try:
                    retain(future.result())
                except Exception as error:
                    records.append({"trial_id": identifier, "error": repr(error)})
                if state["passed"]:
                    event.set()
                    break
    finally:
        event.set()
        executor.shutdown(wait=True, cancel_futures=True)
        for future, identifier in pending.items():
            if not future.cancelled():
                try:
                    retain(future.result())
                except Exception as error:
                    records.append({"trial_id": identifier, "error": repr(error)})
    checked = engine.official(OUTPUT / "best")
    state.update(finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), elapsed_seconds=time.monotonic() - started,
                 passed=checked["passed"], attainability="witnessed" if checked["passed"] else "unknown",
                 best_metrics=checked["metrics"], unvisited_variants=len(queue), variants_generated=counter)
    save("trials.json", records)
    save("run.json", state)
    print(json.dumps(state, indent=2), flush=True)


if __name__ == "__main__":
    main()
