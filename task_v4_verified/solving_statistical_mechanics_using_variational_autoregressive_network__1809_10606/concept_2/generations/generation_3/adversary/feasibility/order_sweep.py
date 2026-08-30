import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import datetime
import hashlib
import json
import multiprocessing
from pathlib import Path
import time

import numpy as np
from scipy.special import logsumexp

import kernel
import portfolio

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "order_sweep"


def save(name, document):
    path = OUTPUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, allow_nan=False) + "\n")


def main():
    os.sched_setaffinity(0, {sorted(os.sched_getaffinity(0))[:4][-1]})
    started = time.monotonic()
    absolute_deadline = datetime.datetime.fromisoformat("2026-08-28T21:36:50+00:00")
    deadline = started + max(0, (absolute_deadline - datetime.datetime.now(datetime.timezone.utc)).total_seconds())
    generator = np.random.default_rng(202608282132)
    portfolio.STOP = multiprocessing.Event()
    pool = json.loads((HERE / "basin_pool.json").read_text())
    models = json.loads((HERE / "models.json").read_text())
    selected = [row for row in pool if row["basin"]["type"] == "ground_component_plus_single_flips"]
    selected.extend(row for row in pool if len(models[row["model_id"]]["antipodal_ground_component_sizes"]) > 1 and row not in selected)
    save("run.json", {"seed": 202608282132, "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      "deadline_utc": absolute_deadline.isoformat(), "one_cpu": list(os.sched_getaffinity(0)),
                      "method": "additional causal-order screening and gradient-penalized refinement on newly sampled disconnected ground-component models",
                      "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    fits = []
    for blueprint in selected:
        if time.monotonic() >= deadline - 120:
            break
        for variant in (2, 3, 4):
            order = portfolio.order_for(variant, generator)
            identifier = len(fits)
            try:
                weights, diagnostics = portfolio.fit_rows(blueprint, order, min(deadline - 100, time.monotonic() + 15))
            except TimeoutError:
                break
            document = {"schema_version": 1, "bonds": blueprint["bonds"], "beta": blueprint["beta"], "order": order,
                        "weights": weights.tolist(), "pattern": blueprint["pattern"], "radius": blueprint["radius"]}
            energy = -(kernel.FEATURES @ np.asarray(document["bonds"]))
            target = np.exp(-document["beta"] * energy - logsumexp(-document["beta"] * energy))
            spins = kernel.HALF[:, order]
            logits = spins @ weights.T
            probability = 2 * np.exp(-np.logaddexp(0, -spins * logits).sum(axis=1))
            sector = portfolio.choose_sector(portfolio.sector_arrays(target), portfolio.sector_arrays(probability))
            if sector is not None:
                document.update(pattern=kernel.SPINS[sector[3]].astype(int).tolist(), radius=sector[2])
            report = kernel.PHYSICS.evaluate_document(document, kernel.SPEC)
            record = {"fit_id": identifier, "model_id": blueprint["model_id"], "pool_id": blueprint["pool_id"],
                      "variant": variant, "order": order, "score": report["core_score"], "metrics": report["metrics"],
                      "fitting": diagnostics, "elapsed_seconds": time.monotonic() - started}
            fits.append(record)
            save(f"fits/{identifier:03d}/witness.json", document)
            save(f"fits/{identifier:03d}/exact_report.json", report)
            save("fits.json", fits)
    ranked = sorted(fits, key=lambda row: row["score"], reverse=True)
    best_score = -1.0
    best_report = None
    results = []
    for fit in ranked:
        if time.monotonic() >= deadline - 5:
            break
        blueprint = pool[fit["pool_id"]]
        job = {"trial_id": len(results), "blueprint": blueprint, "order": fit["order"], "mode": 2, "deadline": deadline}
        try:
            result = portfolio.run_job(job)
        except Exception as error:
            results.append({"fit_id": fit["fit_id"], "error": str(error)})
            save("trials.json", results)
            continue
        identifier = result["trial_id"]
        report = result.pop("best_report")
        document = result.pop("best_witness")
        for label in ("fitted", "final"):
            save(f"trials/{identifier:03d}/{label}_witness.json", result.pop(label + "_witness"))
            save(f"trials/{identifier:03d}/{label}_report.json", result.pop(label + "_report"))
        save(f"trials/{identifier:03d}/witness.json", document)
        save(f"trials/{identifier:03d}/exact_report.json", report)
        result.update(fit_id=fit["fit_id"], score=report["core_score"], passed=report["passed"], metrics=report["metrics"])
        results.append(result)
        save("trials.json", results)
        if report["core_score"] > best_score:
            save("best/witness.json", document)
            best_report = portfolio.official(OUTPUT / "best")
            best_score = best_report["core_score"]
            print(json.dumps({"order_sweep_best_score": best_score, "model_id": blueprint["model_id"],
                              "passed": best_report["passed"], "metrics": best_report["metrics"]}), flush=True)
        if best_report and best_report["passed"]:
            break
    save("summary.json", {"seed": 202608282132, "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                          "elapsed_seconds": time.monotonic() - started, "fitted_orders": len(fits), "refined_orders": len(results),
                          "distinct_models_fitted": len({row["model_id"] for row in fits}), "best_score": best_score,
                          "passed": bool(best_report and best_report["passed"]),
                          "achievability": "witnessed" if best_report and best_report["passed"] else "unknown"})


if __name__ == "__main__":
    main()
