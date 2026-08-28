"""Independent high-precision oracle and invariants for the JSON solver."""

import copy
from decimal import Decimal, localcontext
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

from solve import solve


ROOT = Path(__file__).resolve().parent


def moment(index):
    return {"moment": index}


def constant(value):
    return {"constant": value}


def operation(name, *arguments):
    return {"op": name, "args": list(arguments)}


EXPRESSIONS = [
    moment(0),
    operation("sub", moment(1), operation("mul", moment(0), moment(0))),
    operation("div", moment(2), moment(0)),
    operation("log", operation("add", moment(0), constant(2))),
    operation("sqrt", operation("add", moment(1), constant(3))),
    operation("div", operation("mul", moment(2), moment(0)),
              operation("add", moment(1), constant(2))),
]


def decimal_number(value):
    if isinstance(value, float):
        return Decimal.from_float(value)
    return Decimal(int(value))


def decimal_expression(expression, moments):
    if "moment" in expression:
        return moments[expression["moment"]]
    if "constant" in expression:
        return decimal_number(expression["constant"])
    arguments = [decimal_expression(argument, moments)
                 for argument in expression["args"]]
    name = expression["op"]
    if name == "add":
        return arguments[0] + arguments[1]
    if name == "sub":
        return arguments[0] - arguments[1]
    if name == "mul":
        return arguments[0] * arguments[1]
    if name == "div":
        return arguments[0] / arguments[1]
    if name == "log":
        return arguments[0].ln()
    if name == "sqrt":
        return arguments[0].sqrt()
    raise ValueError(name)


def decimal_transform(joint_mean, expressions):
    moments = [value / joint_mean[0] for value in joint_mean[1:]]
    return [decimal_expression(expression, moments) for expression in expressions]


def decimal_blocks(replica, size):
    blocks = []
    for start in range(0, len(replica["signs"]), size):
        signs = replica["signs"][start:start + size]
        measurements = replica["measurements"][start:start + size]
        total = [Decimal(0)] * (len(measurements[0]) + 1)
        for sign, row in zip(signs, measurements):
            signed = Decimal(sign)
            total[0] += signed
            for column, value in enumerate(row, 1):
                total[column] += signed * decimal_number(value)
        blocks.append((len(signs), total))
    return blocks


def decimal_statistics(blocks, expressions):
    total_count = sum(count for count, _ in blocks)
    total = [sum(values) for values in zip(*(sums for _, sums in blocks))]
    estimate = decimal_transform([value / total_count for value in total], expressions)
    weights = []
    pseudovalues = []
    for count, block_sum in blocks:
        remaining_mean = [(value - removed) / (total_count - count)
                          for value, removed in zip(total, block_sum)]
        deleted = decimal_transform(remaining_mean, expressions)
        pseudovalues.append([
            (total_count * value - (total_count - count) * without) / count
            for value, without in zip(estimate, deleted)
        ])
        weights.append(Decimal(count) / total_count)
    mean = [sum(weight * pseudo[column]
                for weight, pseudo in zip(weights, pseudovalues))
            for column in range(len(expressions))]
    squared_weights = sum(weight * weight for weight in weights)
    covariance = [[
        squared_weights / (1 - squared_weights) * sum(
            weight * (pseudo[row] - mean[row]) * (pseudo[column] - mean[column])
            for weight, pseudo in zip(weights, pseudovalues)
        ) for column in range(len(expressions))] for row in range(len(expressions))]
    return {"mean": [float(value) for value in mean],
            "covariance": [[float(value) for value in row] for row in covariance]}


def decimal_oracle(data):
    with localcontext() as context:
        context.prec = 65
        analyses = []
        for size in data["block_sizes"]:
            blocks = [decimal_blocks(replica, size) for replica in data["replicas"]]
            analyses.append({
                "block_size": size,
                "pooled": decimal_statistics([block for stream in blocks for block in stream],
                                             data["expressions"]),
                "replicas": [decimal_statistics(stream, data["expressions"])
                             for stream in blocks],
            })
        return {"schema_version": 1, "analyses": analyses}


def signed_fixture(seed=0):
    random = np.random.default_rng(seed)
    replicas = []
    for replica_index, length in enumerate([17, 23, 29]):
        signs = [(-1 if index % 5 == 2 else 1) for index in range(length)]
        values = random.normal(size=(length, 3)) * 0.08
        values += [1.4 + replica_index * 0.2, 3.0, -1.7]
        replicas.append({"signs": signs, "measurements": values.tolist()})
    return {"schema_version": 1, "block_sizes": [7, 1, 3, 5],
            "expressions": copy.deepcopy(EXPRESSIONS), "replicas": replicas}


class SolverTests(unittest.TestCase):
    def assert_statistics_close(self, actual, expected, rtol=2e-11, atol=2e-13):
        for key in ["mean", "covariance"]:
            np.testing.assert_allclose(actual[key], expected[key], rtol=rtol, atol=atol)
        covariance = np.asarray(actual["covariance"])
        np.testing.assert_array_equal(covariance, covariance.T)
        self.assertTrue(np.isfinite(actual["mean"]).all())
        self.assertTrue(np.isfinite(covariance).all())
        tolerance = 1e-12 * max(1.0, float(np.max(np.abs(covariance))))
        self.assertGreaterEqual(np.linalg.eigvalsh(covariance).min(), -tolerance)

    def assert_results_close(self, actual, expected):
        self.assertEqual(actual["schema_version"], 1)
        self.assertEqual(len(actual["analyses"]), len(expected["analyses"]))
        for result, reference in zip(actual["analyses"], expected["analyses"]):
            self.assertEqual(result["block_size"], reference["block_size"])
            self.assert_statistics_close(result["pooled"], reference["pooled"])
            self.assertEqual(len(result["replicas"]), len(reference["replicas"]))
            for replica, target in zip(result["replicas"], reference["replicas"]):
                self.assert_statistics_close(replica, target)

    def test_random_signed_nonlinear_against_decimal(self):
        for seed in range(12):
            with self.subTest(seed=seed):
                data = signed_fixture(seed)
                self.assert_results_close(solve(data), decimal_oracle(data))

    def test_unequal_replicas_and_partial_blocks(self):
        data = {"schema_version": 1, "block_sizes": [3, 1],
                "expressions": [moment(0), operation("mul", moment(0), moment(1))],
                "replicas": [
                    {"signs": [1] * length,
                     "measurements": [[offset + index, 2 - index * 0.1]
                                      for index in range(length)]}
                    for length, offset in [(7, -2), (31, 20)]
                ]}
        self.assert_results_close(solve(data), decimal_oracle(data))

    def test_iid_linear_sample_mean_covariance(self):
        random = np.random.default_rng(382)
        values = random.normal(size=(38, 2))
        data = {"schema_version": 1, "block_sizes": [1, 4],
                "expressions": [moment(0), moment(1)],
                "replicas": [
                    {"signs": [1] * len(stream), "measurements": stream.tolist()}
                    for stream in [values[:15], values[15:]]
                ]}
        expected = {"mean": values.mean(axis=0),
                    "covariance": np.cov(values, rowvar=False, ddof=1) / len(values)}
        result = solve(data)
        self.assert_statistics_close(result["analyses"][0]["pooled"], expected)
        self.assert_results_close(result, decimal_oracle(data))

    def test_full_cross_covariance_and_constants(self):
        data = signed_fixture()
        data["expressions"] = [moment(0),
                               operation("add", operation("mul", constant(2), moment(0)),
                                         constant(3)),
                               operation("sub", constant(4), moment(0)),
                               constant(17), operation("log", constant(1))]
        for analysis in solve(data)["analyses"]:
            for statistics in [analysis["pooled"]] + analysis["replicas"]:
                covariance = np.asarray(statistics["covariance"])
                coefficients = np.array([1, 2, -1, 0, 0])
                np.testing.assert_allclose(covariance,
                                           covariance[0, 0] * np.outer(coefficients, coefficients),
                                           rtol=1e-12, atol=1e-16)
                np.testing.assert_array_equal(covariance[3:], 0)
                self.assertEqual(statistics["mean"][3:], [17.0, 0.0])

    def test_sign_reversal_and_replica_permutation(self):
        data = signed_fixture(12)
        expected = solve(data)
        reversed_data = copy.deepcopy(data)
        for replica in reversed_data["replicas"]:
            replica["signs"] = [-sign for sign in replica["signs"]]
        self.assert_results_close(solve(reversed_data), expected)
        data["replicas"].reverse()
        for analysis in expected["analyses"]:
            analysis["replicas"].reverse()
        self.assert_results_close(solve(data), expected)

    def test_small_average_sign(self):
        data = signed_fixture()
        data["block_sizes"] = [1, 3]
        data["replicas"] = []
        for length in [10, 14]:
            signs = [-1, 1] * (length // 2)
            signs[0] = 1
            values = [[10 + index * 0.01, 30 + index * 0.03, -2 + index * 0.002]
                      for index in range(length)]
            data["replicas"].append({"signs": signs, "measurements": values})
        self.assert_results_close(solve(data), decimal_oracle(data))

    def test_temporal_blocking_changes_covariance(self):
        values = np.repeat(np.array([-1.0, 2.0, 0.0, 3.0] * 3), 8)
        measurements = np.column_stack((values, values * -3)).tolist()
        data = {"schema_version": 1, "block_sizes": [1, 4, 8],
                "expressions": [moment(0), moment(1)],
                "replicas": [{"signs": [1] * len(values), "measurements": measurements}
                             for _ in range(2)]}
        result = solve(data)
        variance_iid = result["analyses"][0]["pooled"]["covariance"][0][0]
        variance_blocks = result["analyses"][2]["pooled"]["covariance"][0][0]
        self.assertGreater(variance_blocks, 7 * variance_iid)
        self.assert_results_close(result, decimal_oracle(data))

    def test_example_and_cli_from_another_directory(self):
        example = ROOT.parent / "participant" / "input" / "example.json"
        data = json.loads(example.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            directory = Path(directory)
            input_path = directory / "arbitrary-input.json"
            output_path = directory / "arbitrary-output.json"
            input_path.write_text(json.dumps(data), encoding="utf-8")
            process = subprocess.run(
                [sys.executable, str(ROOT / "solve.py"), "--input", str(input_path),
                 "--output", str(output_path)], cwd=directory, capture_output=True,
                text=True, timeout=120, check=True,
            )
            self.assertEqual(process.stdout, "")
            actual = json.loads(output_path.read_text(encoding="utf-8"))
            self.assert_results_close(actual, decimal_oracle(data))


if __name__ == "__main__":
    unittest.main(verbosity=2)
