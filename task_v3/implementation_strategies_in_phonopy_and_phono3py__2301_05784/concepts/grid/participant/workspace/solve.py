"""Restricted diagonal-grid and histogram starting implementation."""

import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

import sys

import numpy as np


def solve(data):
    diagonal = np.maximum(np.abs(np.diag(data["grid_matrix"])), 1)
    fractional = data["query_addresses"] / diagonal
    shifts = -np.rint(fractional).astype(np.int64)
    cartesian = (fractional + shifts) @ data["reciprocal_lattice"].T
    samples = data["sampling_points"]
    frequencies = data["frequencies"]
    width = max(float(np.ptp(frequencies)), 1.0) / 40.0
    lower = float(frequencies.min()) - width
    upper = float(frequencies.max()) + width
    edges = np.linspace(lower, upper, 43)
    centers = (edges[1:] + edges[:-1]) / 2
    dos = np.empty((len(samples), frequencies.shape[1]))
    cumulative = np.empty_like(dos)
    for branch in range(frequencies.shape[1]):
        counts = np.histogram(frequencies[:, branch], bins=edges)[0]
        heights = counts / (len(frequencies) * np.diff(edges))
        dos[:, branch] = np.interp(samples, centers, heights, left=0, right=0)
        masses = np.concatenate(([0.0], np.cumsum(counts) / len(frequencies)))
        cumulative[:, branch] = np.interp(samples, edges, masses, left=0, right=1)
    return {
        "image_offsets": np.arange(len(shifts) + 1, dtype=np.int64),
        "image_shifts": shifts,
        "distance2": np.einsum("ij,ij->i", cartesian, cartesian),
        "dos": dos,
        "cumulative": cumulative,
    }


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: python solve.py INPUT.npz OUTPUT.npz")
    with np.load(sys.argv[1], allow_pickle=False) as data:
        result = solve(data)
    np.savez_compressed(sys.argv[2], **result)


if __name__ == "__main__":
    main()
