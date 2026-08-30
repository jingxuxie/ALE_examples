import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import concurrent.futures
import datetime
import hashlib
import itertools
import json
import math
import multiprocessing
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE / "copied_v2"))
sys.dont_write_bytecode = True

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

import landscape
import refine
import search
import verify

CORES = sorted(os.sched_getaffinity(0))[:4]
BASE_PROBLEM = search.Problem
STOP = None
DEADLINE = math.inf
BEST = None
BEST_SCORE = -1.0
CALLS = 0


def save(name, document):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, allow_nan=False) + "\n")


def score(problem, metrics, derivatives):
    return min(1.0, metrics[3] / 3, metrics[0] / .4, .05 / max(metrics[1], 1e-100),
               .003 / max(float(np.max(np.abs(derivatives[0]))), 1e-100),
               .32 / max(abs(metrics[2] - problem.target_energy), 1e-100),
               problem.target_sector / .35, .001 / max(metrics[4], 1e-100))


class BoundedProblem(BASE_PROBLEM):
    def calculate(self, weights):
        global BEST, BEST_SCORE, CALLS
        if time.monotonic() >= DEADLINE or (STOP is not None and STOP.is_set()):
            raise TimeoutError("private search deadline or shared stop")
        metrics, derivatives = super().calculate(weights)
        CALLS += 1
        current_score = score(self, metrics, derivatives)
        row_norms = search.ROWS @ np.abs(weights)
        if current_score > BEST_SCORE and row_norms.max() <= verify.BOUND + 1e-12:
            candidate = self.pack(weights)
            BEST_SCORE = current_score
            BEST = candidate
        if current_score >= 1 and row_norms.max() <= verify.BOUND:
            raise RuntimeError("all native gates met; full official verification required")
        return metrics, derivatives


def official(directory):
    output = directory / "official_report.json"
    completed = subprocess.run([sys.executable, "-B", str(ROOT / "evaluator/evaluate.py"),
                                "--submission", str(directory), "--output", str(output)],
                               capture_output=True, text=True, timeout=125)
    if completed.returncode:
        raise RuntimeError(completed.stdout + completed.stderr)
    return json.loads(output.read_text())


def reorder(document, order):
    if order == document["order"]:
        return json.loads(json.dumps(document)), []
    problem = BASE_PROBLEM(document)
    old_weights = np.asarray(document["weights"])
    logits = search.SPINS @ old_weights.T
    probability = 2 * np.exp(-np.logaddexp(0, -search.SPINS * logits).sum(axis=1))
    spins = problem.physical[:, order]
    physical_weights = np.zeros((16, 16))
    physical_weights[np.ix_(document["order"], document["order"])] = old_weights
    weights = np.tril(physical_weights[np.ix_(order, order)], -1)
    old_positions = {site: position for position, site in enumerate(document["order"])}
    diagnostics = []
    for position in range(1, 16):
        site = order[position]
        if set(order[:position]) == set(document["order"][:old_positions[site]]):
            continue
        predictors = spins[:, :position]
        labels = (spins[:, position] + 1) / 2

        def objective(parameters):
            if time.monotonic() >= DEADLINE or STOP.is_set():
                raise TimeoutError("causal row-fit deadline")
            row = parameters[:position] - parameters[position:]
            linear = predictors @ row
            loss = float(probability @ (np.logaddexp(0, linear) - labels * linear))
            gradient = predictors.T @ (probability * (expit(linear) - labels))
            return loss, np.r_[gradient, -gradient]

        initial = weights[position, :position]
        result = minimize(objective, np.r_[np.maximum(initial, 0), np.maximum(-initial, 0)], jac=True,
                          method="SLSQP", bounds=[(0, verify.BOUND)] * (2 * position),
                          constraints=[{"type": "ineq", "fun": lambda values: verify.BOUND - 1e-9 - values.sum(),
                                        "jac": lambda values: -np.ones_like(values)}],
                          options={"maxiter": 65, "ftol": 2e-10})
        weights[position, :position] = result.x[:position] - result.x[position:]
        diagnostics.append({"row": position, "success": bool(result.success), "iterations": int(result.nit), "loss": float(result.fun)})
    weights[verify.LOWER] = search.project(weights[verify.LOWER], verify.BOUND - 1e-9)
    return dict(document, order=order, weights=weights.tolist()), diagnostics


def initialize(event):
    global STOP
    STOP = event
    identity = multiprocessing.current_process()._identity[0]
    os.sched_setaffinity(0, {CORES[(identity - 1) % len(CORES)]})
    search.Problem = BoundedProblem
    refine.Problem = BoundedProblem


def run_job(job):
    global DEADLINE, BEST, BEST_SCORE, CALLS
    started = time.monotonic()
    DEADLINE = min(job["deadline"], started + job.get("seconds", 95))
    BEST, BEST_SCORE, CALLS = None, -1.0, 0
    document = json.loads(json.dumps(job["document"]))
    generator = np.random.default_rng(job["seed"])
    phases = []
    fits = []
    try:
        document, fits = reorder(document, job.get("order", document["order"]))
        if job.get("noise", 0):
            weights = np.asarray(document["weights"])
            weights[verify.LOWER] = search.project(weights[verify.LOWER] + generator.normal(0, job["noise"], 120), verify.BOUND - 1e-9)
            document["weights"] = weights.tolist()
        document, sector = landscape.best_sector(document)
        initial = verify.evaluate(document)
        BEST, BEST_SCORE = json.loads(json.dumps(document)), initial["core_score"]
        mode = job.get("mode", "epigraph")
        if mode in ("variance", "gradvar"):
            document, result = search.optimize(document, objective=mode, iterations=70, constraints=True, verbosity=0)
            phases.append({"phase": mode, "success": bool(result.success), "iterations": int(result.nit), "message": str(result.message)})
            document, sector = landscape.best_sector(document)
        document, result = refine.refine(document, iterations=230, verbose=False)
        phases.append({"phase": "exact_hessian_epigraph", "success": bool(result.success), "iterations": int(result.nit), "objective": float(result.fun), "message": str(result.message)})
        document, sector = landscape.best_sector(document)
        report = verify.evaluate(document)
        if report["core_score"] > BEST_SCORE:
            BEST, BEST_SCORE = document, report["core_score"]
    except (TimeoutError, RuntimeError) as error:
        phases.append({"termination": str(error)})
    if BEST is None:
        BEST = document
    BEST, sector = landscape.best_sector(BEST)
    report = verify.evaluate(BEST)
    return {"trial_id": job["trial_id"], "family": job["family"], "seed": job["seed"],
            "elapsed_seconds": time.monotonic() - started, "native_calls": CALLS, "row_fits": fits,
            "phases": phases, "witness": BEST, "report": report}


def build_jobs(champion, generator, deadline):
    jobs = [{"family": "fixed_order_continuation", "document": champion}]
    order = champion["order"]
    for position in range(1, 15):
        changed = list(order)
        changed[position - 1], changed[position] = changed[position], changed[position - 1]
        jobs.append({"family": "adjacent_order_swap", "document": champion, "order": changed})
    for free_position in range(12, 16):
        for destination in (3, 6, 9, 11):
            changed = list(order)
            site = changed.pop(free_position)
            changed.insert(destination, site)
            jobs.append({"family": "free_spin_interleaving", "document": champion, "order": changed})
    for noise in (.03, .1, .3):
        jobs.append({"family": "coupled_weight_perturbation", "document": champion, "noise": noise})
    for beta in (1.015, 1.04, 1.1):
        jobs.append({"family": "beta_profile", "document": dict(champion, beta=beta)})
    old_first = json.loads((HERE / "seeds/v_1/witness.json").read_text())
    jobs.append({"family": "v1_continuation", "document": old_first})
    artifacts = []
    for path in sorted((HERE / "seeds/artifacts").glob("*.json")):
        document = json.loads(path.read_text())
        report = verify.evaluate(document)
        artifacts.append((report["core_score"], path.name, document))
    for unused, name, document in sorted(artifacts, reverse=True)[:6]:
        jobs.append({"family": "completed_alternative_" + name, "document": document})
    free_sites = order[-4:]
    incidence = [np.flatnonzero(np.any(verify.EDGES == site, axis=1)) for site in free_sites]
    geometries = []
    for index, choices in enumerate(itertools.product(range(1, 4), repeat=4)):
        if time.monotonic() >= deadline - 120:
            break
        bonds = np.asarray(champion["bonds"]).copy()
        for indices, choice in zip(incidence, choices):
            bonds[indices] = 1
            bonds[indices[0]] = bonds[indices[choice]] = -1
        if not 4 <= verify.frustrated(bonds) <= 12:
            continue
        if int((-verify.PRODUCTS @ bonds).min()) != -16:
            continue
        weights = np.asarray(champion["weights"]).copy()
        for position in range(12, 16):
            weights[position] = 0
            site = order[position]
            for edge, (first, second) in enumerate(verify.EDGES):
                if site in (first, second):
                    neighbor = second if first == site else first
                    previous = order.index(int(neighbor))
                    if previous < position:
                        weights[position, previous] = bonds[edge] * (verify.BOUND - 1e-9) / 4
        document = dict(champion, bonds=bonds.astype(int).tolist(), weights=weights.tolist())
        document, sector = landscape.best_sector(document)
        report = verify.evaluate(document)
        save(f"geometry_screen/{index:03d}/witness.json", document)
        save(f"geometry_screen/{index:03d}/report.json", report)
        geometries.append((report["core_score"], index, document))
    save("geometry_screen.json", [{"initial_score": item[0], "index": item[1], "bonds": item[2]["bonds"]} for item in sorted(geometries, reverse=True)])
    geometry_jobs = [{"family": "balanced_bond_geometry", "document": item[2], "geometry_index": item[1], "mode": "variance"} for item in sorted(geometries, reverse=True)[:22]]
    interleaved = []
    for position, job in enumerate(jobs):
        interleaved.append(job)
        if position % 2 == 1 and geometry_jobs:
            interleaved.append(geometry_jobs.pop(0))
    interleaved.extend(geometry_jobs)
    for index, job in enumerate(interleaved):
        job.update(trial_id=index, deadline=deadline, seed=int(generator.integers(0, 2**31)))
    save("job_queue.json", interleaved)
    return interleaved


def validate(champion):
    problem = BASE_PROBLEM(champion)
    weights = np.asarray(champion["weights"])[verify.LOWER]
    metrics, derivatives = problem.calculate(weights)
    reference = verify.evaluate(champion)
    expected = reference["metrics"]
    errors = [abs(metrics[0] - expected["reverse_kl"]), abs(metrics[1] - expected["reward_variance"]),
              abs(metrics[3] - expected["entropy"]), abs(metrics[4] - expected["proposal_sector_mass"]),
              abs(float(np.max(np.abs(derivatives[0]))) - expected["gradient_infinity"])]
    derivative_error = 0.0
    for coordinate in (0, 6, 58, 100):
        shift = np.zeros(120)
        shift[coordinate] = 2e-5
        plus = problem.calculate(weights + shift)[0].copy()
        minus = problem.calculate(weights - shift)[0].copy()
        derivative_error = max(derivative_error, float(np.max(np.abs((plus - minus) / 4e-5 - derivatives[:, coordinate]))))
    problem.calculate(weights)
    direction = np.random.default_rng(202608282217).normal(size=120)
    direction /= np.linalg.norm(direction)
    hessian_action = problem.hessian_vector(direction).copy()
    matrix = refine.hessian(problem, weights)
    hessian_error = float(np.max(np.abs(matrix @ direction - hessian_action)))
    record = {"maximum_metric_error": max(errors), "maximum_finite_difference_error": derivative_error,
              "hessian_action_error": hessian_error, "passed": max(errors) < 1e-9 and derivative_error < 1e-7 and hessian_error < 1e-8}
    save("validation.json", record)
    if not record["passed"]:
        raise RuntimeError("copied kernel validation failed")
    return record


def main():
    started = time.monotonic()
    os.sched_setaffinity(0, set(CORES))
    ending = datetime.datetime.fromisoformat("2026-08-28T22:37:00+00:00")
    deadline = started + max(0, (ending - datetime.datetime.now(datetime.timezone.utc)).total_seconds())
    release = json.loads((ROOT / "adversary/release_manifest.json").read_text())
    frozen_before = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in release["sha256"]}
    champion = json.loads((HERE / "seeds/v_2/witness.json").read_text())
    validation = validate(champion)
    save("best/witness.json", champion)
    best = official(HERE / "best")
    official(HERE / "seeds/v_1")
    official(HERE / "seeds/v_2")
    provenance = {}
    for path in (HERE / "copied_v2").iterdir():
        if path.suffix == ".so":
            continue
        original = ROOT / "attempts/v_2" / path.name
        provenance[str(path.relative_to(HERE))] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                                  "original_sha256": hashlib.sha256(original.read_bytes()).hexdigest()}
    save("source_provenance.json", provenance)
    state = {"seed": 202608282217, "request_started_utc": "2026-08-28T22:17:32+00:00",
             "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "deadline_utc": ending.isoformat(),
             "workers": len(CORES), "affinity": CORES, "best_score": best["core_score"], "passed": best["passed"],
             "attainability": "unknown", "completed_trials": 0, "validation": validation,
             "source_hashes": {str(path.relative_to(HERE)): hashlib.sha256(path.read_bytes()).hexdigest() for path in HERE.rglob("*") if path.is_file() and path.suffix in (".py", ".cpp", ".so")}}
    save("run.json", state)
    generator = np.random.default_rng(state["seed"])
    jobs = build_jobs(champion, generator, deadline)
    context = multiprocessing.get_context("fork")
    event = context.Event()
    executor = concurrent.futures.ProcessPoolExecutor(max_workers=len(CORES), mp_context=context, initializer=initialize, initargs=(event,))
    pending = {}
    records = []
    next_job = 0

    def retain(result):
        document = result.pop("witness")
        report = result.pop("report")
        identifier = result["trial_id"]
        save(f"trials/{identifier:04d}/witness.json", document)
        save(f"trials/{identifier:04d}/independent_report.json", report)
        result.update(score=report["core_score"], passed=report["passed"], metrics=report["metrics"])
        records.append(result)
        state["completed_trials"] = len(records)
        if report["core_score"] > state["best_score"] or report["passed"]:
            trial_report = official(HERE / f"trials/{identifier:04d}")
            if trial_report["core_score"] > state["best_score"] or trial_report["passed"]:
                save("best/witness.json", document)
                save("best/official_report.json", trial_report)
                state.update(best_score=trial_report["core_score"], best_trial=identifier, passed=trial_report["passed"],
                             attainability="witnessed" if trial_report["passed"] else "unknown")
                print(json.dumps({"elapsed_seconds": time.monotonic() - started, "trial": identifier, "family": result["family"],
                                  "score": trial_report["core_score"], "passed": trial_report["passed"], "metrics": trial_report["metrics"]}), flush=True)
        save("trials.json", records)
        save("run.json", state)

    try:
        while time.monotonic() < deadline and not state["passed"] and (next_job < len(jobs) or pending):
            while len(pending) < len(CORES) and next_job < len(jobs):
                job = jobs[next_job]
                save(f"trials/{job['trial_id']:04d}/job.json", job)
                pending[executor.submit(run_job, job)] = job["trial_id"]
                next_job += 1
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
    final = official(HERE / "best")
    state.update(finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), elapsed_seconds=time.monotonic() - started,
                 submitted_trials=next_job, queued_trials=len(jobs), passed=final["passed"], attainability="witnessed" if final["passed"] else "unknown",
                 best_metrics=final["metrics"], failing_gates=final["failing_gates"],
                 frozen_file_changes=[name for name, digest in frozen_before.items() if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest],
                 source_original_changes=[name for name, row in provenance.items() if hashlib.sha256((ROOT / "attempts/v_2" / Path(name).name).read_bytes()).hexdigest() != row["original_sha256"]],
                 termination="passing official witness" if final["passed"] else "bounded private continuation ended without a passing witness")
    save("trials.json", records)
    save("run.json", state)
    print(json.dumps(state, indent=2), flush=True)


if __name__ == "__main__":
    main()
