"""Weak iid, diagonal delta-method baseline; ignores blocking and cross-covariance."""

import argparse
import json
from pathlib import Path

import numpy as np


def expression_value(expression, moments):
    if "moment" in expression:
        return moments[expression["moment"]]
    if "constant" in expression:
        return float(expression["constant"])
    arguments = [expression_value(argument, moments) for argument in expression["args"]]
    functions = {"add": np.add, "sub": np.subtract, "mul": np.multiply,
                 "div": np.divide, "log": np.log, "sqrt": np.sqrt}
    return functions[expression["op"]](*arguments)


def transform(joint_mean, expressions):
    moments = joint_mean[1:] / joint_mean[0]
    return np.array([expression_value(expression, moments) for expression in expressions])


def iid_statistics(joint, expressions):
    mean = joint.mean(axis=0)
    estimate = transform(mean, expressions)
    gradient = np.empty((len(expressions), len(mean)))
    for index in range(len(mean)):
        step = 1e-5 * max(1.0, abs(mean[index]))
        offset = np.zeros_like(mean)
        offset[index] = step
        gradient[:, index] = (transform(mean + offset, expressions)
                              - transform(mean - offset, expressions)) / (2 * step)
    variance = gradient ** 2 @ (joint.var(axis=0, ddof=1) / len(joint))
    return {"mean": estimate.tolist(), "covariance": np.diag(variance).tolist()}


def solve(data):
    streams = []
    for replica in data["replicas"]:
        signs = np.asarray(replica["signs"], dtype=float)
        values = np.asarray(replica["measurements"], dtype=float)
        streams.append(np.column_stack((signs, signs[:, None] * values)))
    pooled = iid_statistics(np.concatenate(streams), data["expressions"])
    replicas = [iid_statistics(stream, data["expressions"]) for stream in streams]
    return {"schema_version": 1, "analyses": [
        {"block_size": block_size, "pooled": pooled, "replicas": replicas}
        for block_size in data["block_sizes"]]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    data = json.loads(Path(arguments.input).read_text())
    result = solve(data)
    Path(arguments.output).write_text(json.dumps(result, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
