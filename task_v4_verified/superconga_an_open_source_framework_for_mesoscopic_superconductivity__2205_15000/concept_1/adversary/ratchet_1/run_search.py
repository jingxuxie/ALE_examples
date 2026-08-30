from common import ROOT, CONCEPT, LimitedSandbox, checked_field, energy_gradient, lower_bound, read_case, scratch_usage, write_json

import argparse
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time

import numpy as np


def isolated_run(case_path, submission, directory, label, seconds=60):
    case = read_case(case_path)
    name = case["case_id"]
    destination = directory / name
    destination.mkdir(parents=True, exist_ok=True)
    record = {"case_id": name, "label": label, "case_path": str(case_path.relative_to(ROOT)), "submission": str(submission.relative_to(ROOT)), "seconds_limit": seconds, "timing_kind": "actual trusted Sandbox, one CPU affinity, 2GiB"}
    with tempfile.TemporaryDirectory(prefix="ratchet-case-", dir=ROOT / "scratch") as temporary:
        staging = Path(temporary)
        (staging / "case.json").write_text(Path(case_path).read_text())
        with LimitedSandbox(CONCEPT / "participant", submission, input_dir=staging, seconds=seconds, memory_gib=2) as sandbox:
            started = time.monotonic()
            failure = None
            log_path = destination / "solver.log"
            with log_path.open("wb") as log:
                process = sandbox.start(["/usr/bin/python3", "/submission/solve.py", "--input", "/input/case.json", "--output", "/output/result.npz"], stdout=log, stderr=log)
                while process.poll() is None:
                    if time.monotonic() - started > seconds:
                        failure = "wall deadline exceeded"
                        sandbox.stop()
                        break
                    if scratch_usage(sandbox.output) + log_path.stat().st_size > 256 * 1024**2:
                        failure = "scratch limit exceeded"
                        sandbox.stop()
                        break
                    time.sleep(0.025)
                elapsed = time.monotonic() - started
                sandbox.stop()
            record.update({"wall_seconds": elapsed, "returncode": process.returncode})
            if process.returncode or elapsed > seconds:
                failure = failure or "nonzero return or timeout"
            try:
                if failure:
                    raise ValueError(failure)
                field = checked_field(sandbox.output / "result.npz", case)
                energy, unused, rms = energy_gradient(case, field)
                np.savez_compressed(destination / "field.npz", psi=field)
                record.update({"energy": energy, "gradient_rms": rms, "valid": rms <= 0.002 and energy >= lower_bound(case) - 1e-8, "reason": "ok" if rms <= 0.002 else "stationarity"})
            except Exception as error:
                record.update({"valid": False, "reason": str(error)[:300]})
    write_json(destination / "record.json", record)
    print(record, flush=True)
    return record


def offline_run(case_path, directory, seconds, seed, mode, warm_directory=None):
    case = read_case(case_path)
    name = case["case_id"]
    destination = directory / name
    destination.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(ROOT / "challenger/solve.py"), "--input", str(case_path), "--output", str(destination / "field.npz"), "--seconds", str(seconds), "--seed", str(seed), "--mode", mode, "--history", str(destination / "history.json")]
    if warm_directory is not None:
        warm_started = time.monotonic()
        while not (warm_directory / name / "record.json").exists():
            if time.monotonic() - warm_started > 300:
                raise RuntimeError("warm baseline record was not produced")
            time.sleep(0.5)
        if not read_case(warm_directory / name / "record.json")["valid"]:
            raise RuntimeError("refusing invalid warm baseline")
        command.extend(["--start", str(warm_directory / name / "field.npz")])

    def limits():
        available = sorted(os.sched_getaffinity(0))
        os.sched_setaffinity(0, {available[os.getpid() % len(available)]})
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
        resource.setrlimit(resource.RLIMIT_CPU, (int(seconds + 10), int(seconds + 10)))

    started = time.monotonic()
    with (destination / "solver.log").open("w") as log:
        result = subprocess.run(command, stdout=log, stderr=log, preexec_fn=limits, timeout=seconds + 20, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1"))
    record = {"case_id": name, "label": directory.name, "case_path": str(case_path.relative_to(ROOT)), "seconds_limit": seconds, "wall_seconds": time.monotonic() - started, "returncode": result.returncode, "timing_kind": "privileged offline quality search, not resource qualification", "seed": seed, "mode": mode}
    try:
        if result.returncode:
            raise ValueError("offline solver failed")
        field = checked_field(destination / "field.npz", case)
        energy, unused, rms = energy_gradient(case, field)
        record.update({"energy": energy, "gradient_rms": rms, "valid": rms <= 0.002, "reason": "ok" if rms <= 0.002 else "stationarity"})
    except Exception as error:
        record.update({"valid": False, "reason": str(error)[:300]})
    write_json(destination / "record.json", record)
    print(record, flush=True)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["baseline", "offline", "bounded"], required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--cases", type=Path, default=ROOT / "cases")
    parser.add_argument("--workers", type=int, default=9)
    parser.add_argument("--seconds", type=float, default=210)
    parser.add_argument("--seed", type=int, default=713)
    parser.add_argument("--search-mode", choices=["combined", "joint", "extended"], default="combined")
    parser.add_argument("--warm-label")
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()
    paths = sorted(args.cases.resolve().glob("*.json"))
    if args.only:
        paths = [path for path in paths if path.stem in args.only]
    destination = ROOT / "runs" / args.label
    destination.mkdir(parents=True, exist_ok=True)
    def run(path):
        if args.mode == "offline":
            warm_directory = ROOT / "runs" / args.warm_label if args.warm_label else None
            return offline_run(path, destination, args.seconds, args.seed, args.search_mode, warm_directory)
        submission = ROOT / ("baseline" if args.mode == "baseline" else "challenger")
        return isolated_run(path, submission, destination, args.label)
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        records = list(executor.map(run, paths))
    write_json(destination / "summary.json", {"case_count": len(records), "valid_count": sum(record["valid"] for record in records), "records": records})


if __name__ == "__main__":
    main()
