import argparse
from fractions import Fraction
import json
from pathlib import Path
import numpy as np


def endpoint_factor(matrix, rows):
    values, vectors = np.linalg.eigh(np.asarray([[float(Fraction(value)) for value in row] for row in matrix]))
    chosen = np.argsort(values)[::-1][:rows]
    result = np.sqrt(np.maximum(values[chosen], 0.0))[:, None] * vectors[:, chosen].T
    return [[str(Fraction(float(value)).limit_denominator(1000000)) for value in row] for row in result]


def solve(document):
    certificates = []
    for instance in document["instances"]:
        dimension = instance["dimension"]
        first = [[["0" for column in range(dimension)] for row in range(instance["a_rows"])]
                 for power in range(instance["a_degree"] + 1)]
        second = [[["0" for column in range(dimension)] for row in range(instance["b_rows"])]
                  for power in range(instance["b_degree"] + 1)]
        first[0] = endpoint_factor(instance["coefficients"][0], instance["a_rows"])
        first[-1] = endpoint_factor(instance["coefficients"][-1], instance["a_rows"])
        certificates.append({"id": instance["id"], "A": first, "B": second})
    return {"certificates": certificates}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    arguments.output.write_text(json.dumps(solve(json.loads(arguments.input.read_text())), indent=2))


if __name__ == "__main__":
    main()
