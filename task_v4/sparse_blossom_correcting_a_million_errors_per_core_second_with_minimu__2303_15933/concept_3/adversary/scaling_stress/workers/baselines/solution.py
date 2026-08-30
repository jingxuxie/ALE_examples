import argparse
import json
import sys

import numpy as np

sys.path.insert(0, "/stress_public")
from local_model import LocalModel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", choices=("prior", "composite"), default="composite")
    arguments = parser.parse_args()
    spec = json.loads(sys.stdin.readline())["spec"]
    model = LocalModel(spec)
    remaining = spec["shot_budget"]
    action_count = len(spec["actions"])
    for action in range(action_count):
        allocation = remaining // (action_count - action)
        while allocation:
            shots = min(allocation, spec["max_shots_per_query"])
            print(json.dumps({"type": "query", "action": action, "shots": shots}), flush=True)
            observation = json.loads(sys.stdin.readline())
            model.observe(action, observation["syndromes"], observation["multiplicities"])
            remaining -= shots
            allocation -= shots
    fitted = model.bounds.mean(axis=1) if arguments.policy == "prior" else model.fit()
    print(json.dumps({"type": "final", "rates": np.exp(fitted).tolist()}), flush=True)


if __name__ == "__main__":
    main()
