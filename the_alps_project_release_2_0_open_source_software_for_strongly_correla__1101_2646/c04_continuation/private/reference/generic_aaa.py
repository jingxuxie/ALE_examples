import argparse
import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "private" / "sources" / "baryrat"))
import baryrat


def unpack(value):
    return np.asarray(value["real"]) + 1j * np.asarray(value["imag"])


def pack(value):
    return {"real": value.real.tolist(), "imag": value.imag.tolist()}


def solve(request):
    imaginary = np.asarray(request["iw"])
    values = unpack(request["G_iw"])
    nodes = np.r_[-1j * imaginary[::-1], 1j * imaginary]
    samples = np.concatenate([values[::-1].conj().transpose(0, 2, 1), values])
    real_nodes = np.asarray(request["omega"]) + 1j * request["eta"]
    dimension = values.shape[-1]
    green = np.empty((len(real_nodes), dimension, dimension), dtype=complex)
    for row in range(dimension):
        for column in range(dimension):
            approximation = baryrat.aaa(nodes, samples[:, row, column], tol=5e-12, mmax=70)
            green[:, row, column] = approximation(real_nodes)
    sigma = real_nodes[:, None, None] * np.eye(dimension) - unpack(request["h0"]) - np.linalg.inv(green)
    return {"G_retarded": pack(green), "Sigma_retarded": pack(sigma)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    Path(arguments.output).write_text(json.dumps(solve(json.loads(Path(arguments.input).read_text()))))
