import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
import math

import numpy as np
import scipy.linalg as sla

sys.path.insert(0, str(ROOT.parents[1] / "evaluator" / "hidden"))
import trusted_physics


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def validate_positions(positions):
    if len(positions) != 4 or any(int(position) != position for position in positions):
        raise ValueError("Four integer sites are required")
    positions = tuple(map(int, positions))
    if any(right <= left for left, right in zip(positions, positions[1:])):
        raise ValueError("Sites must be strictly increasing")
    return positions


def cauchy_determinant(positions, size=None):
    positions = validate_positions(positions)
    first, second, third, fourth = positions
    rows = np.concatenate((np.arange(first + 1, second + 1), np.arange(third + 1, fourth + 1)))
    columns = np.concatenate((np.arange(first, second), np.arange(third, fourth)))
    differences = rows[:, None] - columns[None, :] - 0.5
    if size is None:
        matrix = 1.0 / (np.pi * differences)
    else:
        if size % 2 or size < 4 or first < 0 or fourth >= size:
            raise ValueError("Finite formula requires an even periodic chain containing all sites")
        matrix = 1.0 / (size * np.sin(np.pi * differences / size))
    sign, logarithm = np.linalg.slogdet(matrix)
    return float(sign * np.exp(logarithm))


class ExactTargets:
    def __init__(self, maximum_span=1024):
        self.maximum_span = maximum_span
        distances = np.arange(1, maximum_span + 1, dtype=np.longdouble)
        increments = -np.log1p(-1 / (4 * distances**2))
        self.double_prefix = np.concatenate((np.zeros(1, dtype=np.longdouble), np.cumsum(np.cumsum(increments))))
        self.log_pairs = np.zeros(maximum_span + 1, dtype=np.longdouble)
        base = np.log(np.longdouble(2) / np.longdouble(str(math.pi)))
        accumulated = np.longdouble(0)
        for distance in range(1, maximum_span + 1):
            self.log_pairs[distance] = self.log_pairs[distance - 1] + base + accumulated
            accumulated += increments[distance - 1]

    def pair(self, distance):
        return float(np.exp(self.log_pairs[distance]))

    def evaluate(self, positions):
        first, second, third, fourth = validate_positions(positions)
        left, gap, right = second - first, third - second, fourth - third
        if fourth - first > self.maximum_span:
            raise ValueError("Quartet exceeds the initialized exact-target range")
        prefix = self.double_prefix
        cross_log = (prefix[gap + left + right - 1] - prefix[gap + left - 1]
                     - prefix[gap + right - 1] + prefix[gap - 1])
        product = np.exp(self.log_pairs[left] + self.log_pairs[right])
        enhancement = np.expm1(cross_log)
        return {"raw": float(product * (1 + enhancement)), "covariance": float(product * enhancement),
                "pair_product": float(product), "connected_ratio": float(enhancement),
                "cross_ratio": left * right / ((left + gap) * (right + gap))}


def high_precision_target(positions, digits=70):
    import mpmath as mp
    first, second, third, fourth = validate_positions(positions)
    left, gap, right = second - first, third - second, fourth - third
    with mp.workdps(digits):
        def pair_log(length):
            return length * mp.log(2 / mp.pi) - mp.fsum((length - index) * mp.log1p(-mp.mpf(1) / (4 * index**2))
                                                       for index in range(1, length))
        cross_log = mp.fsum(-multiplicity * mp.log1p(-mp.mpf(1) / (4 * (gap + offset)**2))
                           for offset in range(1, left + right)
                           for multiplicity in (max(0, min(left - 1, offset - 1) - max(0, offset - right) + 1),))
        product = mp.exp(pair_log(left) + pair_log(right))
        covariance = product * mp.expm1(cross_log)
        return {"raw": str(product + covariance), "covariance": str(covariance), "digits": digits}


class TensorContractions:
    def __init__(self, tensor, density=None):
        self.tensor = np.asarray(tensor, dtype=np.complex128)
        self.dimension = tensor.shape[1]
        self.identity = np.eye(self.dimension, dtype=np.complex128)
        if density is None:
            density, self.second_modulus, self.stationary_residual, self.fixed_error = trusted_physics.stationary(self.tensor)
        self.density = density
        self.right_intervals = {}
        self.left_intervals = {}
        self.pairs = {}
        self.prepared = 0
        self.right_environment = self.apply(self.identity, True)
        self.left_environment = self.adjoint(self.density, True)

    def apply(self, environment, insertion=False):
        if insertion:
            return (self.tensor[0] @ environment @ self.tensor[1].conj().T
                    + self.tensor[1] @ environment @ self.tensor[0].conj().T)
        return sum(physical @ environment @ physical.conj().T for physical in self.tensor)

    def adjoint(self, environment, insertion=False):
        if insertion:
            return (self.tensor[0].conj().T @ environment @ self.tensor[1]
                    + self.tensor[1].conj().T @ environment @ self.tensor[0])
        return sum(physical.conj().T @ environment @ physical for physical in self.tensor)

    def prepare(self, maximum_length):
        for length in range(self.prepared + 1, maximum_length + 1):
            right = self.apply(self.right_environment, True)
            left = self.adjoint(self.left_environment, True)
            self.right_intervals[length] = right
            self.left_intervals[length] = left
            self.pairs[length] = float(np.trace(self.density @ right).real)
            self.right_environment = self.apply(self.right_environment)
            self.left_environment = self.adjoint(self.left_environment)
        self.prepared = max(self.prepared, maximum_length)

    def evaluate(self, positions):
        first, second, third, fourth = validate_positions(positions)
        left, gap, right = second - first, third - second, fourth - third
        self.prepare(max(left, right))
        centered = self.right_intervals[right] - self.pairs[right] * self.identity
        uncentered = self.right_intervals[right].copy()
        for unused_step in range(gap - 1):
            centered = self.apply(centered)
            uncentered = self.apply(uncentered)
        covariance = np.vdot(self.left_intervals[left], centered)
        raw = np.vdot(self.left_intervals[left], uncentered)
        if max(abs(covariance.imag), abs(raw.imag)) > 1e-10:
            raise ValueError("Non-real four-spin contraction")
        product = self.pairs[left] * self.pairs[right]
        return {"raw": float(raw.real), "covariance": float(raw.real - product), "pair_product": product,
                "centered_covariance": float(covariance.real),
                "centered_vs_subtracted_absolute_difference": float(abs(covariance.real - (raw.real - product)))}

    def even_transfer(self):
        half = self.dimension // 2
        even = self.tensor[0, :half, :half]
        odd = self.tensor[0, half:, half:]
        upper = self.tensor[1, :half, half:]
        lower = self.tensor[1, half:, :half]
        return np.block([[np.kron(even, even.conj()), np.kron(upper, upper.conj())],
                         [np.kron(lower, lower.conj()), np.kron(odd, odd.conj())]])

    def pack_even(self, matrix):
        half = self.dimension // 2
        return np.concatenate((matrix[:half, :half].reshape(-1), matrix[half:, half:].reshape(-1)))


def check_fourpoint(state_path, quartets, raw_limit=0.025, covariance_limit=0.1, target_floor=1e-6):
    tensor = trusted_physics.load_tensor(state_path)
    original = trusted_physics.score_metrics(trusted_physics.metrics(tensor))
    contractions = TensorContractions(tensor)
    targets = ExactTargets(max(quartet[-1] - quartet[0] for quartet in quartets))
    records = []
    for positions in quartets:
        exact = targets.evaluate(positions)
        if exact["covariance"] < target_floor:
            raise ValueError("Composite covariance below the declared stable target floor")
        observed = contractions.evaluate(positions)
        records.append({"positions": list(positions), "exact": exact, "observed": observed,
                        "raw_relative_error": abs(observed["raw"] / exact["raw"] - 1),
                        "covariance_relative_error": abs(observed["covariance"] / exact["covariance"] - 1)})
    raw_error = max(record["raw_relative_error"] for record in records)
    covariance_error = max(record["covariance_relative_error"] for record in records)
    return {"original_v2_passed": original["passed"], "original_v2_metrics": original["metrics"],
            "fourpoint_passed": raw_error <= raw_limit and covariance_error <= covariance_limit,
            "raw_max_relative_error": raw_error, "covariance_max_relative_error": covariance_error,
            "raw_limit": raw_limit, "covariance_limit": covariance_limit, "target_floor": target_floor,
            "records": records}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True)
    parser.add_argument("--quartets", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--covariance-limit", type=float, default=0.1)
    arguments = parser.parse_args()
    specification = json.loads(Path(arguments.quartets).read_text())
    quartets = specification["quartets"] if isinstance(specification, dict) else specification
    result = check_fourpoint(arguments.state, quartets, covariance_limit=arguments.covariance_limit)
    write_json(arguments.output, result)
    print(json.dumps({key: value for key, value in result.items() if key not in ("records", "original_v2_metrics")}, indent=2))


if __name__ == "__main__":
    main()
