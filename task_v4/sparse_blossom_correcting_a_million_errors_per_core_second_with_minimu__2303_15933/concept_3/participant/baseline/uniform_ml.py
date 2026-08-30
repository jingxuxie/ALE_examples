import json
import os
import sys
from pathlib import Path

import numpy as np

input_directory = Path("/participant/input")
if not input_directory.is_dir():
    input_directory = Path(os.environ.get("DETECTOR_INPUT_DIR", Path(__file__).resolve().parents[1] / "input"))
sys.path.insert(0, str(input_directory))
from model import Model


def send(message):
    print(json.dumps(message, allow_nan=False), flush=True)


def main():
    spec = json.loads(sys.stdin.readline())["spec"]
    model = Model(spec)
    action_count = len(spec["actions"])
    counts = np.zeros((action_count, model.state_count), dtype=np.int64)
    remaining = spec["shot_budget"]
    for action_id in range(action_count):
        allocation = remaining // (action_count - action_id)
        while allocation:
            shots = min(allocation, spec["max_shots_per_query"])
            send({"type": "query", "action": action_id, "shots": shots})
            response = json.loads(sys.stdin.readline())
            if response.get("type") != "observation":
                raise RuntimeError(response)
            counts[action_id] += response["counts"]
            allocation -= shots
            remaining -= shots
    fitted = model.fit(counts)
    send({"type": "final", "rates": np.exp(fitted).tolist()})


if __name__ == "__main__":
    main()
