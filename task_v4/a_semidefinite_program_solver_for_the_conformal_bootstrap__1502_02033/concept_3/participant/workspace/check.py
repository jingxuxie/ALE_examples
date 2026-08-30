import argparse
from fractions import Fraction
import json
from pathlib import Path
import re
import time


MAX_BYTES = 8 * 1024 * 1024
MAX_BITS = 2048


def rational(value):
    if not isinstance(value, str) or len(value) > 1300:
        raise ValueError("rational coefficients must be bounded strings")
    if re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?", value) is None:
        raise ValueError("invalid rational syntax")
    number = Fraction(value)
    if max(abs(number.numerator).bit_length(), number.denominator.bit_length()) > MAX_BITS:
        raise ValueError("rational exceeds bit budget")
    return number


def factor(value, degree, rows, columns):
    if not isinstance(value, list) or len(value) != degree + 1:
        raise ValueError("wrong polynomial degree axis")
    result = []
    for matrix in value:
        if not isinstance(matrix, list) or len(matrix) != rows:
            raise ValueError("wrong factor row count")
        checked = []
        for row in matrix:
            if not isinstance(row, list) or len(row) != columns:
                raise ValueError("wrong factor column count")
            checked.append([rational(entry) for entry in row])
        result.append(checked)
    return result


def coefficient_product(first, second, power, row, column):
    total = Fraction(0)
    for left in range(len(first)):
        right = power - left
        if 0 <= right < len(second):
            for middle in range(len(first[left])):
                total += first[left][middle][row] * second[right][middle][column]
    return total


def verify_instance(instance, certificate):
    dimension = instance["dimension"]
    first = factor(certificate["A"], instance["a_degree"], instance["a_rows"], dimension)
    second = factor(certificate["B"], instance["b_degree"], instance["b_rows"], dimension)
    expected = instance["coefficients"]
    maximum = Fraction(0)
    equal = 0
    count = 0
    mismatch = None
    for power in range(max(len(expected), 2 * len(first) - 1, 2 * len(second))):
        for row in range(dimension):
            for column in range(row, dimension):
                value = coefficient_product(first, first, power, row, column)
                value += coefficient_product(second, second, power - 1, row, column)
                target = Fraction(expected[power][row][column]) if power < len(expected) else Fraction(0)
                error = abs(value - target) / (1 + abs(target))
                maximum = max(maximum, error)
                count += 1
                equal += value == target
                if value != target and mismatch is None:
                    mismatch = [power, row, column]
    try:
        residual = float(maximum)
    except OverflowError:
        residual = 1e300
    return {"id": instance["id"], "certified": maximum == 0,
            "exact_coefficient_fraction": equal / count,
            "scaled_max_residual": min(residual, 1e300), "first_mismatch": mismatch}


def verify(input_path, certificate_path):
    started = time.process_time()
    report = {"core_score": 0.0, "worst_family_score": 0.0, "runtime_score": 1.0,
              "passed": False, "valid": False, "reason": "invalid submission", "cases": []}
    try:
        certificate_path = Path(certificate_path)
        if certificate_path.stat().st_size > MAX_BYTES:
            raise ValueError("certificate exceeds byte budget")
        inputs = json.loads(Path(input_path).read_text())["instances"]
        document = json.loads(certificate_path.read_text())
        certificates = document["certificates"]
        if not isinstance(certificates, list) or len(certificates) != len(inputs):
            raise ValueError("one certificate is required for every instance")
        indexed = {entry["id"]: entry for entry in certificates}
        if len(indexed) != len(certificates) or set(indexed) != {entry["id"] for entry in inputs}:
            raise ValueError("IDs do not match the instance set exactly")
        report["cases"] = [verify_instance(entry, indexed[entry["id"]]) for entry in inputs]
        report["valid"] = True
        report["core_score"] = sum(entry["certified"] for entry in report["cases"]) / len(inputs)
        report["worst_family_score"] = float(all(entry["certified"] for entry in report["cases"]))
        report["passed"] = report["core_score"] == 1.0
        report["reason"] = "all exact identities verified" if report["passed"] else "at least one polynomial identity is not exact"
    except (ValueError, KeyError, TypeError, IndexError, OSError, OverflowError, ZeroDivisionError) as error:
        report["reason"] = str(error)
    report["checker_cpu_seconds"] = time.process_time() - started
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("certificate", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(verify(arguments.input, arguments.certificate), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
