import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
from pathlib import Path

import numpy as np


TARGETS = ("odd_gap", "even_gap", "odd_spacing")


def features(case):
    scale = (case["lambda"] / 6.0) ** (1.0 / 3.0)
    spectra = sorted(case["spectra"], key=lambda record: (record["omega"], record["cutoff"]))
    finest = [record for record in spectra if record["cutoff"] == 8]
    chosen = min(finest, key=lambda record: np.sum(record["boundary_weights"]))
    anchor = np.log(np.maximum(np.abs([chosen["signed_gaps"][target] / scale
                                      for target in TARGETS]), 1e-10))
    values = [case["mu2"] / scale ** 2, case["kappa"] / scale ** 2,
              np.log(spectra[0]["omega"] / scale)]
    for record in spectra:
        signed = np.array([record["signed_gaps"][target] / scale for target in TARGETS])
        values.extend(np.log(np.maximum(np.abs(signed), 1e-10)))
    for record in finest:
        values.extend(np.log(np.maximum(np.array(record["boundary_weights"]).ravel(), 1e-10)))
    return np.array(values), anchor, scale


def kernel(first, second):
    distance = np.sum(first ** 2, axis=1)[:, None] + np.sum(second ** 2, axis=1)[None, :]
    distance -= 2.0 * first @ second.T
    return np.exp(-np.maximum(distance, 0.0) / 32.0)


def predict(training, queries):
    models = {}
    for sites in (2, 3):
        selected = [case for case in training if case["sites"] == sites]
        triples = [features(case) for case in selected]
        design = np.array([triple[0] for triple in triples])
        center = np.mean(design, axis=0)
        spread = np.maximum(np.std(design, axis=0), 0.1)
        normalized = (design - center) / spread
        residuals = np.array([np.log([case["targets"][target] / triple[2] for target in TARGETS])
                              - triple[1] for case, triple in zip(selected, triples)])
        offset = np.mean(residuals, axis=0)
        weights = np.linalg.solve(kernel(normalized, normalized) + 0.005 * np.eye(len(selected)),
                                  residuals - offset)
        models[sites] = (normalized, center, spread, weights, offset)
    predictions = []
    for case in queries:
        values, anchor, scale = features(case)
        design, center, spread, weights, offset = models[case["sites"]]
        correction = (kernel(((values - center) / spread)[None, :], design) @ weights)[0] + offset
        gaps = scale * np.exp(np.clip(anchor + correction, -25.0, 10.0))
        predictions.append({"id": case["id"], "targets": dict(zip(TARGETS, gaps.tolist()))})
    return {"schema_version": 1, "predictions": predictions}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--train", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    queries = json.loads(Path(arguments.input).read_text())["cases"]
    training = json.loads(Path(arguments.train).read_text())["cases"]
    result = predict(training, queries)
    Path(arguments.output).write_text(json.dumps(result, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
