import argparse
import json
import os
from pathlib import Path
import selectors
import subprocess
import time

import numpy as np

from simulator import sample_events


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", type=int, default=0)
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--output")
    parser.add_argument("worker", nargs=argparse.REMAINDER)
    arguments = parser.parse_args()
    input_directory = Path(__file__).resolve().parent
    episodes = json.loads((input_directory / "training.json").read_text())["episodes"]
    episode = episodes[arguments.episode]
    spec = episode["spec"]
    rates = np.asarray(episode["rates"])
    rng = np.random.default_rng(episode["sample_seed"])
    worker = arguments.worker[1:] if arguments.worker[:1] == ["--"] else arguments.worker
    if not worker:
        parser.error("Provide a worker command after --")
    workdir = Path(arguments.workdir).resolve(strict=True)
    if arguments.output:
        output = Path(arguments.output).resolve()
        if not output.is_relative_to(workdir):
            parser.error("--output must be within --workdir")
    environment = dict(os.environ, DETECTOR_INPUT_DIR=str(input_directory), PYTHONDONTWRITEBYTECODE="1",
                       OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    process = subprocess.Popen(worker, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                               cwd=workdir, env=environment)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + 1200

    def send(message):
        process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        process.stdin.flush()

    shots_used = 0
    queries = 0
    try:
        send({"type": "hello", "spec": spec})
        while True:
            if not selector.select(max(0.0, deadline - time.monotonic())):
                raise RuntimeError("development_wall_watchdog")
            line = process.stdout.readline(1048577)
            if not line or len(line) > 1048576:
                raise RuntimeError("worker_closed_pipe_or_oversized_line")
            message = json.loads(line)
            if message.get("type") == "final":
                if set(message) != {"type", "rates"} or not isinstance(message["rates"], list):
                    raise ValueError("final_keys")
                if any(type(value) not in (int, float) for value in message["rates"]):
                    raise ValueError("invalid_rates")
                estimates = np.asarray(message["rates"], dtype=float)
                if estimates.shape != rates.shape or not np.all(np.isfinite(estimates)) or np.any(estimates <= 0):
                    raise ValueError("invalid_rates")
                errors = (np.log(estimates) - np.log(rates))**2
                families = np.array([channel["family"] for channel in spec["channels"]])
                family_scores = {family: float(np.sqrt(np.mean(errors[families == family]))) for family in sorted(set(families))}
                process.stdin.close()
                process.stdin = None
                extra, unused_stderr = process.communicate(timeout=max(1.0, deadline - time.monotonic()))
                if extra.strip():
                    raise RuntimeError("output_after_final")
                if process.returncode != 0:
                    raise RuntimeError("worker_nonzero_exit")
                report = {"episode": episode["id"], "valid": True, "development_only": True,
                          "family_log_rmse": family_scores, "mean_family_log_rmse": float(np.mean(list(family_scores.values()))),
                          "worst_family_log_rmse": max(family_scores.values()), "shots_used": shots_used, "queries": queries,
                          "resource_qualification": False}
                text = json.dumps(report, indent=2) + "\n"
                print(text, end="")
                if arguments.output:
                    output.write_text(text)
                break
            if set(message) != {"type", "action", "shots"} or message["type"] != "query":
                raise ValueError("invalid_query")
            action, shots = message["action"], message["shots"]
            if type(action) is not int or not 0 <= action < len(spec["actions"]):
                raise ValueError("invalid_action")
            if type(shots) is not int or not 1 <= shots <= spec["max_shots_per_query"]:
                raise ValueError("invalid_shots")
            if shots_used + shots > spec["shot_budget"] or queries >= spec["max_queries"]:
                raise ValueError("query_budget")
            syndromes, multiplicities = sample_events(spec, rates, action, shots, rng)
            shots_used += shots
            queries += 1
            send({"type": "observation", "action": action, "shots": shots, "encoding": "sparse_histogram_v1",
                  "syndromes": syndromes.tolist(), "multiplicities": multiplicities.tolist(),
                  "shots_remaining": spec["shot_budget"] - shots_used, "queries_remaining": spec["max_queries"] - queries})
    finally:
        selector.close()
        if process.poll() is None:
            process.kill()
            process.wait()


if __name__ == "__main__":
    main()
