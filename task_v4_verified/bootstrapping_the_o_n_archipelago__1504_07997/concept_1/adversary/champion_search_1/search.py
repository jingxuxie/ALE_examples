import concurrent.futures
import hashlib
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import mpmath as mp


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / "champions/generation_1/output/solve.py"
SANDBOX = ROOT.parent / "authoring/sandbox.py"
FAMILIES = ("separated", "near_coincident", "multiscale", "boundary_isolated", "rotating_null", "coupled_high_order")


def load_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


generator = load_module("search_generator", ROOT / "evaluator/hidden/generate.py")
objective = load_module("search_objective", ROOT / "evaluator/evaluate.py")
validation = load_module("search_validation", ROOT / "evaluator/hidden/validate.py")


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def initialize(cpus):
    identity = multiprocessing.current_process()._identity[0]
    os.sched_setaffinity(0, {cpus[identity % len(cpus)]})


def run_solver(raw, directory):
    directory.mkdir(parents=True, exist_ok=True)
    scratch = directory / "scratch"
    scratch.mkdir(exist_ok=True)
    command = [sys.executable, str(SANDBOX), "--submission", str(SOURCE.parent),
               "--participant", str(ROOT / "participant"), "--scratch", str(scratch),
               "--entry", SOURCE.name, "--seconds", "30", "--memory-mib", "1024"]
    started = time.monotonic()
    with (directory / "stdout.json").open("wb") as stdout, (directory / "stderr.log").open("wb") as stderr:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
                                   start_new_session=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        timed_out = False
        try:
            process.communicate(raw, timeout=30)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
    runtime = time.monotonic() - started
    if timed_out:
        return None, objective.failed("timeout", runtime)
    if process.returncode != 0:
        return None, objective.failed("nonzero_exit:" + str(process.returncode), runtime)
    if (directory / "stderr.log").stat().st_size > objective.OUTPUT_BYTES:
        return None, objective.failed("stderr_limit", runtime)
    try:
        output = objective.load_output((directory / "stdout.json").read_bytes())
    except objective.InvalidOutput as error:
        return None, objective.failed(str(error), runtime)
    return output, {"runtime_seconds": runtime}


def run_case(specification):
    started = time.monotonic()
    identifier, family, variant, seed = specification
    directory = HERE / "cases" / identifier
    directory.mkdir(parents=True, exist_ok=True)
    record = {"id": identifier, "family": family, "variant": variant, "seed": seed,
              "source_sha256": digest(SOURCE), "budget_seconds": 30}
    try:
        mp.mp.dps = 290
        case, witness = generator.make_case(family, variant, seed)
        write(directory / "input.json", case)
        write(directory / "witness.json", witness)
        record["input_sha256"] = digest(directory / "input.json")
        record["witness_sha256"] = digest(directory / "witness.json")
        planted_output = validation.witness_output(witness)
        planted_score = objective.score_case(case, witness, planted_output)
        if not planted_score["protocol_valid"] or planted_score["score"] < 1 - 1e-12:
            raise ValueError("planted spectrum fails objective")
        conditioning = validation.conditioned_fit(case, witness)
        weights = [mp.mpf(feature["weight"]) for feature in witness["features"]]
        assert min(weights) >= mp.mpf("1e-12") and max(weights) <= mp.mpf("1e11")
        assert len(case["blocks"]) <= 5 and len(case["rhs"]) == 40
        assert all(len(kernel) <= 17 for block in case["blocks"] for kernel in block["moments"])
        record.update({"case_valid": True, "planted_score": planted_score, "conditioning": conditioning})
        write(directory / "validation.json", {"planted_score": planted_score, "conditioning": conditioning})
        raw = (directory / "input.json").read_bytes()
        output, execution = run_solver(raw, directory / "run_1")
        score = execution if output is None else objective.score_case(case, witness, output, execution["runtime_seconds"])
        record["score"] = score
        if not score["protocol_valid"] or score["score"] < 1 - 1e-12:
            output, execution = run_solver(raw, directory / "run_2")
            record["repeat_score"] = execution if output is None else objective.score_case(case, witness, output, execution["runtime_seconds"])
    except Exception as error:
        record.update({"case_valid": False, "validation_error": type(error).__name__ + ": " + str(error)})
    record["authoring_seconds"] = time.monotonic() - started
    write(directory / "record.json", record)
    print(json.dumps({"id": identifier, "family": family, "valid": record["case_valid"],
                      "score": record.get("score", {}).get("score"),
                      "runtime": record.get("score", {}).get("runtime_seconds"),
                      "error": record.get("validation_error")}), flush=True)
    return record


def main():
    started = time.monotonic()
    protected = [ROOT / "status.json", ROOT / "evaluator/evaluate.py", ROOT / "evaluator/hidden/manifest.json",
                 ROOT / "evaluator/hidden/generate.py", ROOT / "evaluator/hidden/validate.py", SOURCE,
                 ROOT / "champions/generation_1/solve.py", SANDBOX]
    protected += [path for path in (ROOT / "participant").rglob("*") if path.is_file()]
    hashes = {str(path): digest(path) for path in protected}
    write(HERE / "protected_hashes_before.json", hashes)
    specifications = [("search_%02d_%02d" % (family_index, serial), family, serial % 3,
                       2026082800 + 1009 * family_index + 104729 * serial)
                      for family_index, family in enumerate(FAMILIES) for serial in range(8)]
    write(HERE / "search_manifest.json", {"cases": [{"id": identifier, "family": family, "variant": variant, "seed": seed}
                                                    for identifier, family, variant, seed in specifications],
                                         "generator_sha256": digest(ROOT / "evaluator/hidden/generate.py"),
                                         "scorer_sha256": digest(ROOT / "evaluator/evaluate.py"),
                                         "source_sha256": digest(SOURCE), "search_source_sha256": digest(Path(__file__)),
                                         "parameters": "unchanged generator variants 0,1,2; fresh seeds only"})
    cpus = sorted(os.sched_getaffinity(0))[-6:]
    with concurrent.futures.ProcessPoolExecutor(max_workers=len(cpus), initializer=initialize, initargs=(cpus,)) as pool:
        records = list(pool.map(run_case, specifications))
    valid = [record for record in records if record["case_valid"]]
    failures = [record for record in valid if not record["score"]["protocol_valid"] or record["score"]["score"] < 1 - 1e-12]
    families = {family: [record for record in valid if record["family"] == family] for family in FAMILIES}
    means = {family: sum(record["score"]["score"] for record in members) / len(members) if members else 0
             for family, members in families.items()}
    unchanged = all(digest(Path(path)) == original for path, original in hashes.items())
    report = {"requested_cases": 48, "valid_cases": len(valid), "rejected_cases": len(records) - len(valid),
              "family_counts": {family: len(members) for family, members in families.items()},
              "core": sum(means.values()) / len(means), "worst_family": min(means.values()),
              "family_scores": means, "minimum_case_score": min((record["score"]["score"] for record in valid), default=0),
              "nonperfect_cases": len(failures), "counterexample_ids": [record["id"] for record in failures],
              "total_champion_runtime_seconds": sum(record["score"]["runtime_seconds"] for record in valid),
              "maximum_case_runtime_seconds": max((record["score"]["runtime_seconds"] for record in valid), default=0),
              "protocol_failures": sum(not record["score"]["protocol_valid"] for record in valid),
              "worst_condition_2": max((float(record["conditioning"]["condition_2_row_equilibrated"]) for record in valid), default=0),
              "maximum_reconstructed_weight_relative_error": max((float(record["conditioning"]["max_relative_recovered_weight_error"]) for record in valid), default=0),
              "protected_files_unchanged": unchanged, "elapsed_search_seconds": time.monotonic() - started,
              "scope": "48 fresh-seed cases, unchanged exact-PSD generator and numerical contract; no new magnitude or conditioning parameters",
              "runtime_interpretation": "30 seconds per case; the 240-second/18-case suite cap is not reapplied to a 48-case exploratory search",
              "records": records}
    write(HERE / "results.json", report)
    write(HERE / "counterexamples.json", {"records": failures})
    assert unchanged, "a protected file changed during search"
    assert len(valid) == 48, "search must validate all 48 cases before completion"
    print(json.dumps({key: value for key, value in report.items() if key != "records"}), flush=True)


if __name__ == "__main__":
    main()
