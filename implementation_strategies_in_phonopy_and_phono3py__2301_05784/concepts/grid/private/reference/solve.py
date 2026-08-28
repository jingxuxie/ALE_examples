"""Private pinned official BZ-grid and tetrahedron adapter."""

import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from pathlib import Path
import sys

TARGET = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(TARGET / "author" / "runtime"))
sys.dont_write_bytecode = True

import numpy as np
from phono3py.phonon.grid import BZGrid, get_grid_point_from_address_py
from phono3py.other.tetrahedron_method import get_integration_weights


def make_grid(data):
    return BZGrid(
        data["grid_matrix"],
        reciprocal_lattice=data["reciprocal_lattice"],
        transformation_matrix=np.eye(3),
        is_time_reversal=False,
        store_dense_gp_map=True,
    )


def grid_indices(addresses, grid):
    transformed = np.asarray(addresses @ grid.P.T, dtype=np.int64)
    return get_grid_point_from_address_py(transformed, grid.D_diag)


def geometry(data, grid):
    queries = data["query_addresses"]
    fractional = queries @ np.linalg.inv(data["grid_matrix"]).T
    indices = grid_indices(queries, grid)
    offsets = [0]
    image_shifts = []
    distances = []
    for point, query in zip(indices, fractional):
        addresses = grid.addresses[grid.gp_map[point] : grid.gp_map[point + 1]]
        images = addresses @ grid.QDinv.T
        shifts = np.rint(images - query).astype(np.int64)
        cartesian = (query + shifts) @ data["reciprocal_lattice"].T
        squared = np.einsum("ij,ij->i", cartesian, cartesian)
        minimum = float(squared.min())
        shifts = shifts[squared <= minimum + float(data["tie_tolerance"])]
        shifts = np.unique(shifts, axis=0)
        image_shifts.extend(shifts.tolist())
        offsets.append(len(image_shifts))
        distances.append(minimum)
    return {
        "image_offsets": np.array(offsets, dtype=np.int64),
        "image_shifts": np.array(image_shifts, dtype=np.int64).reshape(-1, 3),
        "distance2": np.array(distances, dtype=np.float64),
    }


def solve(data, block_size=512):
    grid = make_grid(data)
    permutation = grid_indices(data["grid_addresses"], grid)
    count = len(permutation)
    if not np.array_equal(np.sort(permutation), np.arange(count)):
        raise ValueError("Input addresses do not form a complete quotient grid")
    frequencies = np.empty_like(data["frequencies"], order="C")
    frequencies[permutation] = data["frequencies"]
    result = geometry(data, grid)
    for field, function in (("dos", "I"), ("cumulative", "J")):
        total = np.zeros((len(data["sampling_points"]), frequencies.shape[1]))
        for start in range(0, count, block_size):
            weights = get_integration_weights(
                data["sampling_points"],
                frequencies,
                grid,
                grid_points=grid.grg2bzg[start : start + block_size],
                bzgp2irgp_map=grid.bzg2grg,
                function=function,
            )
            total += weights.sum(axis=0)
        result[field] = total / count
    return result


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: python solve.py INPUT.npz OUTPUT.npz")
    with np.load(sys.argv[1], allow_pickle=False) as data:
        result = solve(data)
    np.savez_compressed(sys.argv[2], **result)


if __name__ == "__main__":
    main()
