"""Joint, count-weighted delete-one-batch jackknife for signed replicas."""

import argparse
import json
from pathlib import Path

import numpy as np


PRECISION = np.longdouble
OPERATORS = {
    "add": np.add,
    "sub": np.subtract,
    "mul": np.multiply,
    "div": np.divide,
    "log": np.log,
    "sqrt": np.sqrt,
}


def expression_value(expression, moments):
    """Evaluate a scalar expression on any leading batch dimensions."""
    if "moment" in expression:
        return moments[..., expression["moment"]]
    if "constant" in expression:
        return PRECISION(expression["constant"])
    arguments = [
        expression_value(argument, moments) for argument in expression["args"]
    ]
    return OPERATORS[expression["op"]](*arguments)


def transform(joint_sums, expressions):
    """Count normalization cancels in every reweighted channel mean."""
    moments = joint_sums[..., 1:] / joint_sums[..., :1]
    estimates = np.empty(moments.shape[:-1] + (len(expressions),), dtype=PRECISION)
    for index, expression in enumerate(expressions):
        estimates[..., index] = expression_value(expression, moments)
    return estimates


def make_blocks(joint, block_size):
    """Partition one replica, including its final, possibly shorter block."""
    starts = np.arange(0, len(joint), block_size, dtype=np.int64)
    counts = np.minimum(block_size, len(joint) - starts)
    sums = np.add.reduceat(joint, starts, axis=0)
    return counts, sums


def jackknife_statistics(counts, sums, expressions):
    """Return the specified weighted pseudovalue mean and its covariance."""
    total_count = int(counts.sum())
    total_sum = sums.sum(axis=0, dtype=PRECISION)
    estimate = transform(total_sum, expressions)
    deleted_estimates = transform(total_sum - sums, expressions)

    weights = counts.astype(PRECISION) / total_count
    corrections = (estimate - deleted_estimates) * (
        (total_count - counts).astype(PRECISION) / counts
    )[:, None]
    mean_correction = np.sum(weights[:, None] * corrections, axis=0)
    corrected_mean = estimate + mean_correction

    centered = corrections - mean_correction
    squared_weight_sum = np.sum(weights * weights)
    covariance = centered.T @ (weights[:, None] * centered)
    covariance *= squared_weight_sum / (1 - squared_weight_sum)
    covariance = (covariance + covariance.T) / 2

    return {
        "mean": corrected_mean.astype(float).tolist(),
        "covariance": covariance.astype(float).tolist(),
    }


def solve(data):
    streams = []
    for replica in data["replicas"]:
        signs = np.asarray(replica["signs"], dtype=PRECISION)
        measurements = np.asarray(replica["measurements"], dtype=PRECISION)
        joint = np.empty((len(signs), measurements.shape[1] + 1), dtype=PRECISION)
        joint[:, 0] = signs
        np.multiply(signs[:, None], measurements, out=joint[:, 1:])
        streams.append(joint)

    analyses = []
    expressions = data["expressions"]
    for block_size in data["block_sizes"]:
        blocks = [make_blocks(stream, block_size) for stream in streams]
        counts = np.concatenate([block[0] for block in blocks])
        sums = np.concatenate([block[1] for block in blocks])
        analyses.append({
            "block_size": block_size,
            "pooled": jackknife_statistics(counts, sums, expressions),
            "replicas": [
                jackknife_statistics(counts, sums, expressions)
                for counts, sums in blocks
            ],
        })
    return {"schema_version": 1, "analyses": analyses}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    with Path(arguments.input).open(encoding="utf-8") as source:
        data = json.load(source)
    result = solve(data)
    with Path(arguments.output).open("w", encoding="utf-8") as destination:
        json.dump(result, destination, allow_nan=False, separators=(",", ":"))
        destination.write("\n")


if __name__ == "__main__":
    main()
