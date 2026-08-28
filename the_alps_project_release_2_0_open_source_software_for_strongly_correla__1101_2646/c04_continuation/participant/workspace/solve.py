import argparse
import json
from pathlib import Path

import numpy as np


def unpack(value):
    return np.asarray(value["real"]) + 1j * np.asarray(value["imag"])


def pack(value):
    return {"real": value.real.tolist(), "imag": value.imag.tolist()}


def solve(request):
    first_moment = unpack(request["moments"][1])
    bare = unpack(request["h0"])
    dimension = len(bare)
    frequencies = np.asarray(request["omega"]) + 1j * request["eta"]
    diagonal = np.diag(np.diag(first_moment))
    green = np.linalg.inv(frequencies[:, None, None] * np.eye(dimension) - diagonal)
    sigma = frequencies[:, None, None] * np.eye(dimension) - bare - np.linalg.inv(green)
    return {"G_retarded": pack(green), "Sigma_retarded": pack(sigma)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    Path(arguments.output).write_text(json.dumps(solve(json.loads(Path(arguments.input).read_text()))))
