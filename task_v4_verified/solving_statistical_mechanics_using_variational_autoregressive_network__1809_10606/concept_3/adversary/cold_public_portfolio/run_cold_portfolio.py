import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np


SIDE = Path(__file__).resolve().parent
PUBLIC = SIDE.parents[1] / "participant"
PREVIOUS = SIDE.parent / "public_data_portfolio"


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def load_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def memory_snapshot():
    status = {}
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith(("VmPeak:", "VmHWM:", "VmSize:", "VmRSS:")):
            key, value = line.split(":", 1)
            status[key] = value.strip()
    return status


def fit_worker(index):
    started = time.monotonic()
    cpu_started = time.process_time()
    protocol = json.loads((SIDE / "PREREGISTRATION.json").read_text())
    variant = protocol["variants"][index]
    available = sorted(os.sched_getaffinity(0))
    offset = (index % 4) * 4
    affinity = {available[(offset + position) % len(available)] for position in range(min(4, len(available)))}
    os.sched_setaffinity(0, affinity)
    resource.setrlimit(resource.RLIMIT_AS, (8 * 1024 ** 3, 8 * 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_CPU, (1600, 1601))
    directory = SIDE / variant["name"]
    directory.mkdir(exist_ok=False)
    helper = load_module("public_likelihood", SIDE / "public_likelihood.py")
    transfer = load_module("public_transfer", PUBLIC / "transfer.py")
    spec = json.loads((PUBLIC / "input/model.json").read_text())
    queries = json.loads((SIDE / "queries.json").read_text())
    with np.load(SIDE / variant["warm_start"], allow_pickle=False) as saved:
        initial = np.concatenate((saved["magnitudes"], saved["fields"]))
    metadata = {"variant": variant, "public_inputs_only": True, "cold_truth_reads": 0,
                "cpu_affinity": sorted(affinity), "address_space_limit_bytes": 8 * 1024 ** 3,
                "wall_cap_fit_seconds": variant.get("max_fit_seconds"), "initialization": variant["warm_start"]}
    if variant["kind"] == "frozen_control":
        parameters = initial
        metadata.update(optimizer_iterations=0, objective_evaluations=0, stop_reason="Existing public-trained parameters reused unchanged")
    else:
        import torch
        from scipy.optimize import minimize

        torch.set_num_threads(4)
        torch.set_num_interop_threads(1)
        with np.load(PUBLIC / "input/train.npz", allow_pickle=False) as training:
            configurations = training["visible_spins"]
            betas = training["betas"]
        engine = helper.LatentLikelihood(torch, spec, configurations, betas)
        if variant.get("perturbation_fraction", 0):
            generator = np.random.default_rng(variant["optimizer_seed"])
            initial = initial + generator.normal(0, variant["perturbation_fraction"], initial.shape) * engine.scale
            initial = np.clip(initial, np.asarray(engine.bounds)[:, 0], np.asarray(engine.bounds)[:, 1])
        track = {"best_loss": float("inf"), "best": initial.copy(), "evaluations": 0, "trace": []}
        fit_started = time.monotonic()

        def objective(parameters):
            if time.monotonic() - fit_started > variant["max_fit_seconds"]:
                raise helper.FitTimeout()
            loss, gradient, likelihood = engine.objective(parameters, variant["regularization"])
            track["evaluations"] += 1
            if loss < track["best_loss"]:
                track.update(best_loss=loss, best=parameters.copy(), best_nll=likelihood)
            if track["evaluations"] == 1 or track["evaluations"] % 25 == 0:
                record = {"evaluation": track["evaluations"], "objective": loss, "mean_nll": likelihood,
                          "fit_seconds": time.monotonic() - fit_started}
                track["trace"].append(record)
                print(json.dumps(record), flush=True)
            return loss, gradient

        try:
            result = minimize(objective, initial, jac=True, method="L-BFGS-B", bounds=engine.bounds,
                              options={"maxiter": variant["max_iterations"], "maxfun": variant["max_function_evaluations"],
                                       "ftol": variant["ftol"], "gtol": variant["gtol"], "maxls": 20, "maxcor": 25})
            stop_reason = str(result.message)
            iterations = int(result.nit)
        except helper.FitTimeout:
            stop_reason = "Preregistered fit wall-time cap"
            iterations = None
        if not np.isfinite(track["best_loss"]):
            raise RuntimeError("No completed training objective evaluation")
        parameters = track["best"]
        metadata.update(optimizer_iterations=iterations, objective_evaluations=track["evaluations"],
                        stop_reason=stop_reason, best_regularized_objective=track["best_loss"],
                        best_mean_negative_log_likelihood=track["best_nll"], trace=track["trace"],
                        training_configurations=int(np.prod(configurations.shape[:2])),
                        fit_wall_seconds=time.monotonic() - fit_started, torch_threads=torch.get_num_threads(),
                        torch_interop_threads=torch.get_num_interop_threads(), torch_version=torch.__version__)
        del engine, configurations
    edge_count = len(spec["edges"])
    probabilities = helper.model_predictions(transfer, spec, queries, parameters[:edge_count], parameters[edge_count:])
    probabilities = np.maximum(probabilities, 1e-15)
    probabilities /= probabilities.sum(axis=1, keepdims=True)
    probabilities = np.ascontiguousarray(probabilities, dtype="<f8")
    identifiers = np.ascontiguousarray([query["id"] for query in queries], dtype="<U24")
    assert probabilities.shape == (48, 64) and np.isfinite(probabilities).all()
    assert np.all(probabilities > 0) and np.max(np.abs(probabilities.sum(axis=1) - 1)) <= 1e-10
    np.savez(directory / "predictions.npz", probabilities=probabilities, query_ids=identifiers)
    np.savez(directory / "fitted_parameters.npz", magnitudes=parameters[:edge_count], fields=parameters[edge_count:])
    assert (directory / "predictions.npz").stat().st_size <= 65536
    metadata.update(total_wall_seconds=time.monotonic() - started, cpu_seconds=time.process_time() - cpu_started,
                    peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, process_memory=memory_snapshot(),
                    predictions_sha256=digest(directory / "predictions.npz"),
                    parameters_sha256=digest(directory / "fitted_parameters.npz"))
    write_json(directory / "fit_report.json", metadata)
    print(json.dumps({"finished": variant["name"], "total_wall_seconds": metadata["total_wall_seconds"],
                      "cpu_seconds": metadata["cpu_seconds"], "peak_rss_kib": metadata["peak_rss_kib"]}), flush=True)


def launch(index, variant):
    log_path = SIDE / (variant["name"] + ".log")
    started = time.monotonic()
    with log_path.open("xb") as log:
        try:
            process = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--worker", str(index)],
                                     stdout=log, stderr=subprocess.STDOUT, timeout=430, env=os.environ.copy(), cwd=SIDE)
            return_code = process.returncode
            reason = "completed" if return_code == 0 else "worker_exit_" + str(return_code)
        except subprocess.TimeoutExpired:
            return_code = None
            reason = "hard_worker_timeout"
    result = {"name": variant["name"], "return_code": return_code, "reason": reason,
              "worker_wall_seconds": time.monotonic() - started}
    if return_code != 0:
        directory = SIDE / variant["name"]
        directory.mkdir(exist_ok=True)
        write_json(directory / "FAILED.json", result)
    return result


def run():
    assert not (SIDE / "OUTPUTS_FROZEN.json").exists()
    protocol = json.loads((SIDE / "PREREGISTRATION.json").read_text())
    started = time.monotonic()
    write_json(SIDE / "STARTED.json", {"started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                       "protocol_sha256": digest(SIDE / "PREREGISTRATION.json"), "cold_truth_opened": False})
    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(launch, index, variant) for index, variant in enumerate(protocol["variants"])]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            write_json(SIDE / "fit_execution.json", results)
            print(json.dumps(result), flush=True)
    for relative, expected in protocol["public_input_hashes"].items():
        assert digest(SIDE / relative) == expected, relative
    hashes = {str(path.relative_to(SIDE)): digest(path) for path in sorted(SIDE.rglob("*")) if path.is_file() and path.name != "run.log"}
    manifest = {"frozen_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "files_sha256": hashes,
                "wall_seconds_since_fit_launch": time.monotonic() - started, "cold_truth_opened": False,
                "hidden_model_opened": False, "variants_expected": len(protocol["variants"]),
                "variants_with_predictions": [variant["name"] for variant in protocol["variants"] if (SIDE / variant["name"] / "predictions.npz").exists()],
                "policy": "All parameter fits and predictions are sealed. No further optimization or prediction edits; one cold-label evaluation only."}
    write_json(SIDE / "OUTPUTS_FROZEN.json", manifest)
    for variant in protocol["variants"]:
        directory = SIDE / variant["name"]
        if directory.exists():
            for path in directory.iterdir():
                path.chmod(0o444)
            directory.chmod(0o555)
    (SIDE / "PREREGISTRATION.json").chmod(0o444)
    (SIDE / "OUTPUTS_FROZEN.json").chmod(0o444)
    print(json.dumps({"outputs_frozen": True, "variants_with_predictions": manifest["variants_with_predictions"],
                      "wall_seconds_since_fit_launch": manifest["wall_seconds_since_fit_launch"]}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", type=int)
    arguments = parser.parse_args()
    if arguments.worker is None:
        run()
    else:
        fit_worker(arguments.worker)
