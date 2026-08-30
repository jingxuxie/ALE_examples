import argparse
import json
import os
from pathlib import Path
import subprocess

import numpy as np

from model import Model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", type=int, default=0)
    parser.add_argument("--workdir")
    parser.add_argument("--output")
    parser.add_argument("worker", nargs=argparse.REMAINDER)
    arguments = parser.parse_args()
    episodes = json.loads(Path(__file__).with_name("training.json").read_text())["episodes"]
    episode = episodes[arguments.episode]
    spec = episode["spec"]
    rates = np.array(episode["rates"])
    probabilities = Model(spec).distribution(np.log(rates))
    probabilities /= probabilities.sum(axis=1, keepdims=True)
    rng = np.random.default_rng(episode["sample_seed"])
    worker = arguments.worker
    if worker and worker[0] == "--":
        worker = worker[1:]
    if not worker:
        parser.error("Specify worker command after --")
    environment = dict(os.environ)
    environment["DETECTOR_INPUT_DIR"] = str(Path(__file__).resolve().parent)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    process = subprocess.Popen(worker, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                               cwd=arguments.workdir, env=environment)

    def send(message):
        process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()

    remaining = spec["shot_budget"]
    queries = 0
    try:
        send({"type": "hello", "spec": spec})
        while True:
            message = json.loads(process.stdout.readline())
            if message["type"] == "final":
                estimates = np.array(message["rates"])
                assert estimates.shape == rates.shape and np.all(np.isfinite(estimates)) and np.all(estimates > 0)
                errors = (np.log(estimates) - np.log(rates)) ** 2
                families = [channel["family"] for channel in spec["channels"]]
                scores = {family: float(np.sqrt(np.mean(errors[np.array(families) == family]))) for family in set(families)}
                report = {"episode": episode["id"], "family_log_rmse": scores,
                          "mean_family_log_rmse": float(np.mean(list(scores.values()))),
                          "shots_used": spec["shot_budget"] - remaining}
                text = json.dumps(report, indent=2) + "\n"
                print(text, end="")
                if arguments.output:
                    Path(arguments.output).write_text(text)
                process.stdin.close()
                assert process.wait(timeout=900) == 0
                break
            assert message["type"] == "query" and set(message) == {"type", "action", "shots"}
            action = message["action"]
            shots = message["shots"]
            assert type(action) is int and 0 <= action < len(spec["actions"])
            assert type(shots) is int and 1 <= shots <= min(remaining, spec["max_shots_per_query"])
            assert queries < spec["max_queries"]
            counts = rng.multinomial(shots, probabilities[action])
            remaining -= shots
            queries += 1
            send({"type": "observation", "action": action, "shots": shots, "counts": counts.tolist(),
                  "shots_remaining": remaining, "queries_remaining": spec["max_queries"] - queries})
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


if __name__ == "__main__":
    main()
