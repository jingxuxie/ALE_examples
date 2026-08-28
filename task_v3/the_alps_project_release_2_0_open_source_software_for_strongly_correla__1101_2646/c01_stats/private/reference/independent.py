import json
from pathlib import Path

import numpy as np


def expression_value(expression, moments):
    if "moment" in expression:
        return moments[..., expression["moment"]]
    if "constant" in expression:
        return np.full(moments.shape[:-1], float(expression["constant"]))
    arguments = [expression_value(argument, moments) for argument in expression["args"]]
    operation = expression["op"]
    functions = {"add": np.add, "sub": np.subtract, "mul": np.multiply,
                 "div": np.divide, "log": np.log, "sqrt": np.sqrt}
    return functions[operation](*arguments)


def transform(joint_means, expressions):
    moments = joint_means[..., 1:] / joint_means[..., :1]
    return np.stack([expression_value(expression, moments) for expression in expressions], axis=-1)


def batch_stream(replica, block_size):
    signs = np.asarray(replica["signs"], dtype=float)
    measurements = np.asarray(replica["measurements"], dtype=float)
    joint = np.column_stack((signs, signs[:, None] * measurements))
    starts = np.arange(0, len(signs), block_size)
    sums = np.add.reduceat(joint, starts, axis=0)
    counts = np.minimum(block_size, len(signs) - starts).astype(float)
    return sums, counts


def statistics(sums, counts, expressions):
    total_count = counts.sum()
    total_sum = sums.sum(axis=0)
    full = transform(total_sum / total_count, expressions)
    leaveout = transform((total_sum - sums) / (total_count - counts)[:, None], expressions)
    pseudovalues = (total_count * full - (total_count - counts)[:, None] * leaveout) / counts[:, None]
    weights = counts / total_count
    estimate = weights @ pseudovalues
    centered = pseudovalues - estimate
    squared_weights = weights @ weights
    covariance = (centered.T * weights) @ centered * squared_weights / (1.0 - squared_weights)
    return {"mean": estimate.tolist(), "covariance": covariance.tolist()}


def solve(data):
    analyses = []
    for block_size in data["block_sizes"]:
        batches = [batch_stream(replica, block_size) for replica in data["replicas"]]
        sums = np.concatenate([batch[0] for batch in batches])
        counts = np.concatenate([batch[1] for batch in batches])
        analyses.append({
            "block_size": block_size,
            "pooled": statistics(sums, counts, data["expressions"]),
            "replicas": [statistics(batch_sums, batch_counts, data["expressions"])
                         for batch_sums, batch_counts in batches],
        })
    return {"schema_version": 1, "analyses": analyses}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    result = solve(json.loads(Path(arguments.input).read_text()))
    Path(arguments.output).write_text(json.dumps(result, allow_nan=False) + "\n")
