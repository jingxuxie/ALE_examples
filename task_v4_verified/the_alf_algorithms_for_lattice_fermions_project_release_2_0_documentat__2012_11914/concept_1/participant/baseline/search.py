import argparse
import json
from pathlib import Path
import sys

import numpy as np


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))
from physics import load_model, weight_batch


def search(draws=512, seed=20317):
    model = load_model()
    random = np.random.default_rng(seed)
    selected = None
    for start in range(0, draws, 256):
        fields = random.choice([-1, 1], size=(min(256, draws - start), model["time_slices"], model["linear_size"] ** 2))
        signs, logabs = weight_batch(fields, model)
        negative = np.flatnonzero(signs < 0)
        selected = fields[negative[0] if len(negative) else int(np.argmin(logabs))]
        if len(negative):
            break
    return {"fields": selected.tolist()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--draws", type=int, default=512)
    parser.add_argument("--seed", type=int, default=20317)
    arguments = parser.parse_args()
    Path(arguments.output).write_text(json.dumps(search(arguments.draws, arguments.seed)) + "\n")
