import os
import sys

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import resource
import signal
import subprocess
import time

HERE = Path(__file__).resolve().parent
CONCEPT = HERE.parents[1]
sys.path.insert(0, str(HERE / "v1"))
from contractor import load_mps, measure


def hashes(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob("*")) if path.is_file()}


def run_solver(directory, request, destination):
    destination.mkdir(parents=True, exist_ok=True)
    request_path, state_path = destination / "request.json", destination / "state.npz"
    request_path.write_text(json.dumps(request, indent=2) + "\n")

    def limits():
        resource.setrlimit(resource.RLIMIT_CPU, (math.ceil(request["budget_seconds"]) + 2,
                                               math.ceil(request["budget_seconds"]) + 3))
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))

    def alarm_handler(signum, frame):
        raise TimeoutError("Public preflight solver wall exceeded")

    environment = dict(os.environ, MPS_DEBUG="1", PYTHONDONTWRITEBYTECODE="1")
    started = time.monotonic()
    with (destination / "stdout.log").open("wb") as output, (destination / "stderr.log").open("wb") as error:
        process = subprocess.Popen([sys.executable, str(directory / "solve.py"), "--request", str(request_path),
                                    "--output", str(state_path)], cwd=directory, env=environment,
                                   stdin=subprocess.DEVNULL, stdout=output, stderr=error, preexec_fn=limits)
        previous = signal.signal(signal.SIGALRM, alarm_handler)
        signal.setitimer(signal.ITIMER_REAL, request["wall_seconds"])
        timeout = False
        try:
            _, status, usage = os.wait4(process.pid, 0)
        except TimeoutError:
            timeout = True
            process.kill()
            _, status, usage = os.wait4(process.pid, 0)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0.0)
            signal.signal(signal.SIGALRM, previous)
        process.returncode = os.waitstatus_to_exitcode(status)
    cpu = usage.ru_utime + usage.ru_stime
    result = {"returncode": process.returncode, "cpu_seconds": cpu,
              "wall_seconds": time.monotonic() - started, "max_rss_kib": usage.ru_maxrss,
              "wall_timeout": timeout, "valid": False, "mode": "reviewed-copy direct-child public preflight, not official bwrap grade"}
    if process.returncode == 0 and cpu <= request["budget_seconds"] and not timeout:
        result.update(measure(load_mps(state_path, request), request), valid=True,
                      state_sha256=hashlib.sha256(state_path.read_bytes()).hexdigest())
    (destination / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return result


def main():
    source_hashes = hashes(HERE / "v1")
    report = {"started_utc": datetime.now(timezone.utc).isoformat(), "source_hashes": source_hashes,
              "variants": 1, "official_evaluations": 0, "cases": []}
    tasks = [(name, 6.0, 30.0) for name in ("symmetric", "nonuniform", "odd")]
    tasks.append(("odd", 40.0, 120.0))
    for name, budget, wall in tasks:
        request = json.loads((CONCEPT / "participant/input" / ("example_" + name + ".json")).read_text())
        request.update(budget_seconds=budget, wall_seconds=wall)
        entry = {"example": name, "budget_seconds": budget}
        for label, directory in (("baseline", HERE / "provenance/published_baseline"), ("v1", HERE / "v1")):
            result = run_solver(directory, request, HERE / "preflight" / (name + "_" + str(int(budget))) / label)
            entry[label] = result
            print(json.dumps({"example": name, "budget_seconds": budget, "solver": label, **result}), flush=True)
        if entry["baseline"]["valid"] and entry["v1"]["valid"]:
            entry["energy_improvement"] = entry["baseline"]["energy"] - entry["v1"]["energy"]
        report["cases"].append(entry)
        (HERE / "preflight.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    assert hashes(HERE / "v1") == source_hashes
    report["all_valid"] = all(entry[label]["valid"] for entry in report["cases"] for label in ("baseline", "v1"))
    report["completed_utc"] = datetime.now(timezone.utc).isoformat()
    report["solver_invocations"] = 8
    (HERE / "preflight.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
