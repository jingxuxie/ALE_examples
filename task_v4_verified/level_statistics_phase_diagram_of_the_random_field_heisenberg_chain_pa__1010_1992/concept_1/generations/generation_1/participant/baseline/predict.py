import argparse
import gzip
import json
import os
from pathlib import Path
import pickle
import sys

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                 "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

from descriptors import feature_matrix


def read_cases(path):
    text = Path(path).read_text()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    if isinstance(payload, dict):
        return payload["cases"] if "cases" in payload else [payload]
    return payload


def predict_cases(model, cases):
    estimates = np.clip(model.predict(feature_matrix(cases)), 0.0, 1.0)
    return {"predictions": [{"id": case["id"], "f": float(estimate)}
                            for case, estimate in zip(cases, estimates)]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input")
    parser.add_argument("--output")
    parser.add_argument("--model", default=str(Path(__file__).with_name("baseline.pkl.gz")))
    args = parser.parse_args()
    if bool(args.input) != bool(args.output):
        parser.error("--input and --output must be supplied together")
    with gzip.open(args.model, "rb") as stream:
        model = pickle.load(stream)
    model.n_jobs = 1
    if args.input:
        result = predict_cases(model, read_cases(args.input))
        Path(args.output).write_text(json.dumps(result, allow_nan=False) + "\n")
        return
    model.predict(feature_matrix([{"fields": np.linspace(-1.0, 1.0, 10)}]))
    print("READY", flush=True)
    line = sys.stdin.readline()
    if not line:
        raise ValueError("Expected one JSON input line after READY")
    cases = json.loads(line)["cases"]
    print(json.dumps(predict_cases(model, cases), allow_nan=False), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
