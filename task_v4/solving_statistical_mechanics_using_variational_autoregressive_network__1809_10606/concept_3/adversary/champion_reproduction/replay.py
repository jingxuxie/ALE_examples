"""Bounded replay of recovered source, never using hidden data for fitting."""

import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import numpy as np


SIDE = Path(__file__).resolve().parent
CONCEPT = SIDE.parents[1]
WORK = SIDE / "recovered"


def save(name, value):
    (SIDE / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    if (SIDE / "REPLAY_STARTED.json").exists():
        raise SystemExit("One bounded replay only; no archived-prediction tuning.")
    started = time.monotonic()
    deadline = started + 900
    provenance = json.loads((SIDE / "SOURCE_PROVENANCE.json").read_text())
    summary = WORK / "summarize.py"
    old = "    predictions = np.asarray([[likelihood.predict(values, queries) for values in chain] for chain in chains[:, ::2]])"
    new = "    predictions = np.asarray([[likelihood.predict(values, queries) for values in chain] for chain in chains])"
    assert new in summary.read_text() and old not in summary.read_text()
    summary_provenance = provenance["sources"]["summarize.py"]
    summary_provenance.update({"recovery": "Verified initial Git blob followed by transcript Update File at line 3807",
                               "recorded_updates": [{"transcript_line": 3807, "old": old, "new": new}],
                               "transcript_source_sha256": hashlib.sha256(summary.read_bytes()).hexdigest(),
                               "restored_source_sha256": hashlib.sha256(summary.read_bytes()).hexdigest()})
    save("SOURCE_PROVENANCE.json", provenance)
    source_hashes = {name: hashlib.sha256((WORK / name).read_bytes()).hexdigest() for name in provenance["sources"]}
    for name, source in provenance["sources"].items():
        assert source_hashes[name] == source["restored_source_sha256"]
    public_paths = [CONCEPT / "participant/input" / name for name in ("model.json", "train.npz", "queries.json")]
    public_hashes = {str(path.relative_to(CONCEPT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in public_paths}
    if hasattr(os, "sched_setaffinity"):
        os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[-4:])
    cache = SIDE / "cache"
    cache.mkdir(exist_ok=True)
    environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
                       CUDA_VISIBLE_DEVICES="", PYTHONDONTWRITEBYTECODE="1", TMPDIR=str(cache),
                       TORCH_HOME=str(cache), XDG_CACHE_HOME=str(cache))
    save("REPLAY_STARTED.json", {"started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                "max_replay_seconds": 900, "source_sha256": source_hashes,
                                "public_inputs_sha256": public_hashes,
                                "only_fitting_inputs": "public observations, signs, bounds, and mask",
                                "command_policy": "Original fit, native compilation, posterior preparation, four seeded HMC chains, final summarizer",
                                "omitted": "Non-predictive multistart/synthetic validation and partial progress summaries; all source is restored",
                                "comparison_policy": "No archive read until predictions are complete; require bitwise probability and ID equality before champion stress claims",
                                "nonlocal_field_support": "Original native predictor assumes fields in readout column; do not silently correct it"})
    stages = []
    children = []
    handles = []
    def launch(name, command):
        handle = (SIDE / (name + ".log")).open("w")
        handles.append(handle)
        process = subprocess.Popen(command, cwd=WORK, env=environment, stdout=handle, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        children.append(process)
        return process
    def finish(name, process, stage_started):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(name, 900)
        status = process.wait(timeout=remaining)
        record = {"stage": name, "exit_code": status, "seconds": time.monotonic() - stage_started}
        stages.append(record)
        print(json.dumps(record), flush=True)
        if status:
            raise RuntimeError(name + " failed; see its sidecar log")
    try:
        stage_started = time.monotonic()
        compile_process = launch("compile", ["g++", "-O3", "-march=native", "-std=c++17", "-shared", "-fPIC", "strip.cpp", "-o", "strip.so"])
        fit_process = launch("fit", [sys.executable, "-B", "infer.py", "--maxiter", "1800"])
        finish("compile", compile_process, stage_started)
        finish("fit", fit_process, stage_started)
        stage_started = time.monotonic()
        finish("native_check", launch("native_check", [sys.executable, "-B", "native.py"]), stage_started)
        stage_started = time.monotonic()
        finish("posterior_prepare", launch("posterior_prepare", [sys.executable, "-B", "posterior.py", "--prepare"]), stage_started)
        stage_started = time.monotonic()
        chains = [(index, launch("chain_%d" % index, [sys.executable, "-B", "posterior.py", "--chain", str(index),
                                                     "--warmup", "800", "--samples", "2400"])) for index in range(4)]
        for index, process in chains:
            finish("chain_%d" % index, process, stage_started)
        stage_started = time.monotonic()
        finish("summarize", launch("summarize", [sys.executable, "-B", "summarize.py"]), stage_started)
        artifact = WORK / "predictions.npz"
        save("REPLAY_OUTPUT_FROZEN.json", {"completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                          "prediction_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                                          "archive_not_yet_opened": True})
        archived = CONCEPT / "champions/generation_1/predictions.npz"
        with np.load(artifact, allow_pickle=False) as reproduced, np.load(archived, allow_pickle=False) as champion:
            actual, reference = reproduced["probabilities"], champion["probabilities"]
            ids_equal = np.array_equal(reproduced["query_ids"], champion["query_ids"])
            exact = bool(ids_equal and np.array_equal(actual, reference))
            comparison = {"exact_probability_arrays_and_ids": exact,
                          "archive_bytes_identical": artifact.read_bytes() == archived.read_bytes(),
                          "max_absolute_probability_difference": float(np.max(abs(actual - reference))),
                          "max_query_tv_difference": float(np.max(0.5 * np.sum(abs(actual - reference), axis=1))),
                          "mean_forward_kl_archive_to_replay": float(np.mean(np.sum(reference * np.log(reference / actual), axis=1))),
                          "archived_sha256": hashlib.sha256(archived.read_bytes()).hexdigest(),
                          "reproduced_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()}
        result = {"completed": True, "stages": stages, "runtime_seconds": time.monotonic() - started,
                  "comparison": comparison, "source_faithful": True,
                  "champion_reproduced_exactly": exact, "champion_stress_evaluated": False,
                  "interpretation": "Exact original-query reproduction verified; stress evaluation is a separate step." if exact else
                                    "Source-faithful rerun differs numerically from the archived champion. Do not label this rerun or portfolio stress results as champion evaluations."}
    except Exception as error:
        result = {"completed": False, "stages": stages, "runtime_seconds": time.monotonic() - started,
                  "exception": type(error).__name__, "message": str(error),
                  "champion_reproduced_exactly": False, "champion_stress_evaluated": False,
                  "interpretation": "Bounded exact reproduction not established; artifact-only champion cannot be evaluated on new queries without recovered matching state."}
    finally:
        for process in children:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
        for handle in handles:
            handle.close()
    assert all(hashlib.sha256((WORK / name).read_bytes()).hexdigest() == digest for name, digest in source_hashes.items())
    assert all(hashlib.sha256(path.read_bytes()).hexdigest() == public_hashes[str(path.relative_to(CONCEPT))] for path in public_paths)
    save("REPRODUCTION_RESULT.json", result)
    (SIDE / "REPORT.md").write_text("# Champion source reproduction\n\n" + result["interpretation"] +
                                   "\n\nEight sources are restored with command/line/hash provenance in SOURCE_PROVENANCE.json. "
                                   "The recorded summarizer Update File is applied after its verified initial full-file snapshot. "
                                   "Source code is unchanged otherwise; output paths relocate automatically through __file__.\n\n"
                                   "Only public material observations and priors were used for fitting. The archived predictions are opened only after replay completion. "
                                   "No original attempts, champions, participant assets, evaluator, or status were modified. "
                                   "No hidden material parameters or query labels were used.\n\n"
                                   "The original native prediction method assumes field sites are in the readout column; nonlocal stress fields are outside its implemented interface. "
                                   "No correction of that scientific behavior is made.\n\n"
                                   "See REPRODUCTION_RESULT.json and stage logs for numerical comparison and runtime.\n")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
