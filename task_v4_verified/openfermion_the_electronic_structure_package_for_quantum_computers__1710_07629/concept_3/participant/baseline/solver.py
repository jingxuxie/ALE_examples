"""CLI entry point. Model paths are relative to this submitted file."""

import json
import os
from pathlib import Path
import sys

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import numpy as np

from features import predict


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: solver.py REQUEST_JSON PREDICTIONS_JSON")
    request = json.loads(Path(sys.argv[1]).read_text())
    if request["schema_version"] != 1:
        raise ValueError("unsupported schema")
    with np.load(request["inputs"], allow_pickle=False) as archive:
        inputs = {key: archive[key] for key in archive.files}
    with np.load(Path(__file__).resolve().with_name("model.npz"), allow_pickle=False) as model:
        predictions = predict(inputs, model)
    Path(sys.argv[2]).write_text(json.dumps({"schema_version": 1,
        "predictions": predictions.tolist()}, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
