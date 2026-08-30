import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import time
import numpy as np
from scipy.linalg import eigh
from contractor import hamiltonian_terms, measure
from optimizer import optimize
from benchmark import make_case


def embed(operator, site, length, dimension):
    return np.kron(np.eye(dimension ** site), np.kron(operator, np.eye(dimension ** (length - site - 1))))


for sector in ("even", "odd", "any"):
    request = make_case(sector, 4, 4, 16, sector, -0.9, 1.7, 0.8, 1.1)
    if sector == "any":
        request["field"] = [0.002, -0.003, 0.001, -0.002]
    onsite, positions = hamiltonian_terms(request)
    matrix = sum(embed(onsite[site], site, 4, 4) for site in range(4))
    for site in range(3):
        matrix -= request["coupling"][site] * embed(positions[site], site, 4, 4) @ embed(positions[site + 1], site + 1, 4, 4)
    if sector != "any":
        configurations = np.indices((4, 4, 4, 4)).reshape(4, -1)
        active = np.flatnonzero(configurations.sum(axis=0) % 2 == int(sector == "odd"))
        matrix = matrix[np.ix_(active, active)]
    exact = eigh(matrix, subset_by_index=(0, 0))[0][0]
    tensors = optimize(request)
    metrics = measure(tensors, request)
    error = metrics["energy"] - exact
    print(sector, "exact", exact, "error", error, metrics, flush=True)
    assert abs(error) < 1e-9
