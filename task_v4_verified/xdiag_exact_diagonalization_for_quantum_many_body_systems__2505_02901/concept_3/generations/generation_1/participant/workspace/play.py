import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
from physics import LOWER, UPPER, probabilities, validate_experiment


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--controller", required=True, type=Path)
    parser.add_argument("--example", default=0, type=int)
    arguments = parser.parse_args()
    participant = Path(__file__).resolve().parents[1]
    config = json.loads((participant / "input/config.json").read_text())
    examples = json.loads((participant / "input/development.json").read_text())
    truth = np.asarray(examples[arguments.example]["parameters"])
    environment = dict(os.environ, PYTHONPATH=str(participant / "workspace"))
    process = subprocess.Popen([sys.executable, str(arguments.controller.resolve())], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=environment)
    process.stdin.write(json.dumps({"type": "start", "config": config, "device_id": "development"}) + "\n")
    process.stdin.flush()
    random = np.random.default_rng(9917)
    for query_index in range(config["query_budget"] + 1):
        line = process.stdout.readline()
        if not line:
            raise RuntimeError("controller stopped without answer")
        message = json.loads(line)
        if message.get("type") == "answer":
            estimate = np.asarray(message["parameters"])
            error = np.sqrt(np.mean(((estimate - truth) / (UPPER - LOWER)) ** 2))
            print(json.dumps({"normalized_rmse": float(error), "score": float(1 - error), "parameters": estimate.tolist(), "truth": truth.tolist()}, indent=2))
            process.stdin.close()
            process.wait(timeout=3)
            return
        if query_index == config["query_budget"]:
            process.kill()
            raise ValueError("query budget exceeded")
        validate_experiment(message)
        counts = random.multinomial(config["shots"], probabilities(truth, message))
        process.stdin.write(json.dumps({"type": "observation", "counts": counts.tolist(), "remaining": config["query_budget"] - query_index - 1}) + "\n")
        process.stdin.flush()
    raise RuntimeError("no answer")


if __name__ == "__main__":
    main()
