import sys

sys.dont_write_bytecode = True

import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import time

import numpy as np

from cases import TOPOLOGIES, cases, sample

SIDE = Path(__file__).resolve().parent
CONCEPT = SIDE.parents[1]
sys.path.insert(0, str(CONCEPT / "evaluator"))
from evaluate import InvalidEpisode, Lines, send, worker_command


def check_frozen():
    expected = json.loads((SIDE / "frozen_snapshot.json").read_text())
    for name, value in expected.items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == value


def stress_command(submission, worker, bridge):
    submission = Path(submission).resolve(strict=True)
    relative = submission.relative_to(SIDE)
    if len(relative.parts) < 2 or relative.parts[0] not in ("workers", "candidates", "runs"):
        raise ValueError("Use an exact submission leaf under this sidecar's workers, candidates, or runs")
    if bridge:
        worker = ["/usr/bin/python3", "/stress_public/legacy_bridge.py"] + worker
    command = worker_command(submission, worker)
    original_public = str(CONCEPT / "participant")
    command[command.index(original_public)] = str(CONCEPT / "generations/generation_2/participant")
    command[1:1] = ["--ro-bind", str(SIDE / "worker_support"), "/stress_public"]
    return command


def run_case(case, submission, worker, output_directory, bridge=False):
    spec = case["spec"]
    rates = np.asarray(case["rates"])
    rng = np.random.default_rng(case["sample_seed"])
    key = secrets.token_bytes(32)
    stderr_path = output_directory / (case["id"] + ".stderr")
    started = time.monotonic()
    with stderr_path.open("wb") as stderr_stream:
        process = subprocess.Popen(stress_command(submission, worker, bridge), stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=stderr_stream, close_fds=True,
                                   start_new_session=True, env={"PATH": "/usr/bin:/bin"})
        os.set_blocking(process.stdin.fileno(), False)
        lines = Lines(process)
        shots_used = 0
        queries = 0
        observations_bytes = 0
        max_observation_bytes = 0
        allocation = np.zeros(len(spec["actions"]), dtype=int)
        estimate = None
        meter = None
        reason = "ok"
        try:
            send(process, {"key": key.hex(), "cpu_limit": spec["cpu_seconds"]}, started + 300)
            ready = lines.read(started + 300)
            if ready.get("type") != "_ready" or not hmac.compare_digest(str(ready.get("auth", "")), hmac.new(key, b"ready", hashlib.sha256).hexdigest()):
                raise InvalidEpisode("supervisor_initialization_failed")
            deadline = time.monotonic() + spec["wall_seconds"]
            send(process, {"type": "hello", "spec": spec}, deadline)
            while True:
                message = lines.read(deadline)
                kind = message.get("type")
                if kind == "_meter":
                    encoded = json.dumps(message.get("meter"), sort_keys=True, separators=(",", ":"))
                    expected = hmac.new(key, encoded.encode(), hashlib.sha256).hexdigest()
                    if not hmac.compare_digest(str(message.get("auth", "")), expected):
                        raise InvalidEpisode("invalid_cpu_authentication")
                    meter = message["meter"]
                    if meter["cpu_seconds"] > spec["cpu_seconds"] + 0.05:
                        raise InvalidEpisode("cpu_limit")
                    if meter["exit_status"] != 0:
                        raise InvalidEpisode("worker_nonzero_exit")
                    if estimate is None:
                        raise InvalidEpisode("missing_final")
                    break
                if estimate is not None:
                    raise InvalidEpisode("output_after_final")
                if kind == "query":
                    if set(message) != {"type", "action", "shots"}:
                        raise InvalidEpisode("query_keys")
                    action = message["action"]
                    shots = message["shots"]
                    if type(action) is not int or not 0 <= action < len(spec["actions"]):
                        raise InvalidEpisode("invalid_action")
                    if type(shots) is not int or not 1 <= shots <= spec["max_shots_per_query"]:
                        raise InvalidEpisode("invalid_shots")
                    if shots_used + shots > spec["shot_budget"] or queries >= spec["max_queries"]:
                        raise InvalidEpisode("query_budget")
                    syndromes, multiplicities = sample(case, action, shots, rng)
                    shots_used += shots
                    queries += 1
                    allocation[action] += shots
                    response = {"type": "observation", "action": action, "shots": shots,
                                "encoding": "sparse_histogram_v1", "syndromes": syndromes.tolist(),
                                "multiplicities": multiplicities.tolist(),
                                "shots_remaining": spec["shot_budget"] - shots_used,
                                "queries_remaining": spec["max_queries"] - queries}
                    length = len(json.dumps(response, separators=(",", ":"))) + 1
                    observations_bytes += length
                    max_observation_bytes = max(max_observation_bytes, length)
                    send(process, response, deadline)
                elif kind == "final":
                    if set(message) != {"type", "rates"} or not isinstance(message["rates"], list):
                        raise InvalidEpisode("final_keys")
                    if any(type(value) not in (int, float) for value in message["rates"]):
                        raise InvalidEpisode("invalid_rates")
                    estimate = np.asarray(message["rates"], dtype=float)
                    if estimate.shape != rates.shape or not np.all(np.isfinite(estimate)) or np.any(estimate <= 0):
                        raise InvalidEpisode("invalid_rates")
                    process.stdin.close()
                else:
                    raise InvalidEpisode("unknown_message")
            process.wait(timeout=max(1.0, deadline - time.monotonic()))
            if process.returncode != 0:
                raise InvalidEpisode("sandbox_nonzero_exit")
        except (InvalidEpisode, ValueError, OSError, subprocess.TimeoutExpired) as error:
            reason = str(error) if isinstance(error, InvalidEpisode) else type(error).__name__
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            lines.close()
            process.stdout.close()
            if not process.stdin.closed:
                process.stdin.close()
    with stderr_path.open("rb") as stderr_stream:
        stderr_stream.seek(max(0, stderr_path.stat().st_size - 4096))
        stderr_tail = stderr_stream.read().decode(errors="replace")
    valid = reason == "ok"
    if not valid and ("MemoryError" in stderr_tail or "Unable to allocate" in stderr_tail):
        reason = "memory_error_under_3GiB_cap"
    family_rmse = {}
    if valid:
        squared_error = (np.log(estimate) - np.log(rates)) ** 2
        families = np.array([channel["family"] for channel in spec["channels"]])
        family_rmse = {family: float(np.sqrt(np.mean(squared_error[families == family]))) for family in sorted(set(families))}
    mean_error = float(np.mean(list(family_rmse.values()))) if valid else None
    worst_error = max(family_rmse.values()) if valid else None
    return {"case": case["id"], "detectors": spec["detector_count"], "channels": len(rates),
            "actions": len(spec["actions"]), "valid": valid, "passed": None, "reason": reason,
            "core_score": None if not valid else float(np.exp(-mean_error)),
            "worst_family_score": None if not valid else float(np.exp(-worst_error)),
            "runtime_score": None if meter is None else max(0.0, 1.0 - meter["cpu_seconds"] / spec["cpu_seconds"]),
            "mean_family_log_rmse": mean_error, "worst_family_log_rmse": worst_error,
            "family_log_rmse": family_rmse, "cpu_seconds": None if meter is None else meter["cpu_seconds"],
            "wall_seconds": time.monotonic() - started, "shots_used": shots_used, "queries": queries,
            "allocation": allocation.tolist(), "legacy_bridge": bridge,
            "max_observation_bytes": max_observation_bytes, "total_observation_bytes": observations_bytes,
            "stderr_tail": stderr_tail, "spec_sha256": hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--sizes", nargs="+", type=int, default=[14, 16, 18, 20])
    parser.add_argument("--topologies", nargs="+", choices=TOPOLOGIES, default=list(TOPOLOGIES))
    parser.add_argument("--seed", type=int, default=8317021)
    parser.add_argument("--shots", type=int, default=40000)
    parser.add_argument("--legacy-bridge", action="store_true")
    parser.add_argument("worker", nargs=argparse.REMAINDER)
    arguments = parser.parse_args()
    output = Path(arguments.output).resolve()
    if not output.is_relative_to(SIDE):
        parser.error("All stress outputs must stay inside adversary/scaling_stress")
    output.parent.mkdir(parents=True, exist_ok=True)
    log_directory = output.parent / (output.stem + "_logs")
    log_directory.mkdir(exist_ok=True)
    worker = arguments.worker[1:] if arguments.worker[:1] == ["--"] else arguments.worker
    if not worker:
        parser.error("Specify a worker command after --")
    check_frozen()
    results = []
    for case in cases(arguments.seed, arguments.sizes, arguments.topologies, arguments.shots):
        result = run_case(case, arguments.submission, worker, log_directory, arguments.legacy_bridge)
        results.append(result)
        print(json.dumps(result, allow_nan=False), flush=True)
        output.write_text(json.dumps({"status": "exploratory_unfrozen", "official_generation": False,
                                     "passed": None, "targets": None, "seed": arguments.seed,
                                     "fresh_agent_launched": False, "cases": results}, indent=2) + "\n")
    check_frozen()


if __name__ == "__main__":
    main()
