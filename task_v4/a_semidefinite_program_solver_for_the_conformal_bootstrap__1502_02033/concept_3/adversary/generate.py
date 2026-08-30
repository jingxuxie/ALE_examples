from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import random
import shutil


ROOT = Path(__file__).resolve().parents[1]


def zeros(degree, rows, columns):
    return [[[Fraction(0) for column in range(columns)] for row in range(rows)] for power in range(degree + 1)]


def random_factor(generator, degree, rows, columns, denominator=8):
    return [[[Fraction(generator.randint(-5, 5), denominator) for column in range(columns)]
             for row in range(rows)] for power in range(degree + 1)]


def multiply(first, second):
    output = zeros(len(first) + len(second) - 2, len(first[0]), len(second[0][0]))
    for left, matrix in enumerate(first):
        for right, other in enumerate(second):
            for row in range(len(matrix)):
                for column in range(len(other[0])):
                    output[left + right][row][column] += sum(matrix[row][middle] * other[middle][column]
                                                             for middle in range(len(other)))
    return output


def gram(first, second):
    columns = len(first[0][0])
    output = zeros(max(2 * len(first) - 2, 2 * len(second) - 1), columns, columns)
    for offset, current in [(0, first), (1, second)]:
        for left, matrix in enumerate(current):
            for right, other in enumerate(current):
                for row in range(columns):
                    for column in range(columns):
                        output[left + right + offset][row][column] += sum(
                            matrix[middle][row] * other[middle][column] for middle in range(len(matrix)))
    return output


def strings(value):
    if isinstance(value, list):
        return [strings(entry) for entry in value]
    return str(value)


def generate():
    generator = random.Random(940728361)
    factors = []
    factors.append((random_factor(generator, 6, 2, 3), random_factor(generator, 5, 2, 3), "endpoint_faces"))
    moving = zeros(2, 3, 4)
    for index in range(3):
        moving[0][index][index] = Fraction(1)
    moving[0][0][3], moving[1][0][3] = Fraction(1), Fraction(1)
    moving[0][1][3], moving[1][1][3], moving[2][1][3] = Fraction(2), Fraction(-1), Fraction(1)
    moving[0][2][3], moving[1][2][3] = Fraction(-1), Fraction(2)
    factors.append((multiply(random_factor(generator, 5, 3, 3), moving),
                    multiply(random_factor(generator, 4, 2, 3), moving), "moving_nullspace"))
    first = random_factor(generator, 9, 3, 4, 16)
    second = random_factor(generator, 8, 3, 4, 16)
    transform = [[[Fraction(1), Fraction(64), Fraction(0), Fraction(1, 64)],
                  [Fraction(0), Fraction(1, 16), Fraction(128), Fraction(0)],
                  [Fraction(0), Fraction(0), Fraction(16), Fraction(16)],
                  [Fraction(0), Fraction(0), Fraction(0), Fraction(1, 256)]]]
    for current in [first, second]:
        for power, matrix in enumerate(current):
            for row in range(len(matrix)):
                for column in range(4):
                    matrix[row][column] /= 2 ** power
    factors.append((multiply(first, transform), multiply(second, transform), "scale_separated"))
    instances = []
    certificates = []
    families = {}
    for number, (first, second, family) in enumerate(factors, 1):
        identifier = f"pmp_{number:02}"
        instance = {"id": identifier, "dimension": len(first[0][0]),
                    "coefficients": strings(gram(first, second)), "a_rows": len(first[0]),
                    "b_rows": len(second[0]), "a_degree": len(first) - 1, "b_degree": len(second) - 1}
        instances.append(instance)
        certificates.append({"id": identifier, "A": strings(first), "B": strings(second)})
        families[identifier] = family
    document = {"instances": instances}
    for target in [ROOT / "participant" / "input" / "instances.json", ROOT / "evaluator" / "hidden" / "instances.json"]:
        target.write_text(json.dumps(document, indent=2) + "\n")
    (ROOT / "evaluator" / "hidden" / "planted_certificate.json").write_text(json.dumps({"certificates": certificates}, indent=2) + "\n")
    (ROOT / "evaluator" / "hidden" / "families.json").write_text(json.dumps(families, indent=2) + "\n")
    shutil.copyfile(ROOT / "participant" / "workspace" / "check.py", ROOT / "evaluator" / "hidden" / "checker.py")
    print(json.dumps({"instances": len(instances), "families": families}))


if __name__ == "__main__":
    generate()
