from __future__ import annotations

from runtime import SOURCE

import numpy as np
from bposd.css import css_code
from scipy.sparse import load_npz


def binary_rank(matrix):
    reduced = np.asarray(matrix, dtype=np.uint8).copy()
    pivot = 0
    for column in range(reduced.shape[1]):
        candidates = np.flatnonzero(reduced[pivot:, column])
        if not len(candidates):
            continue
        selected = pivot + candidates[0]
        reduced[[pivot, selected]] = reduced[[selected, pivot]]
        targets = np.flatnonzero(reduced[pivot + 1 :, column]) + pivot + 1
        reduced[targets] ^= reduced[pivot]
        pivot += 1
        if pivot == reduced.shape[0]:
            break
    return pivot


def toric3d(length):
    coordinates = list(np.ndindex((length, length, length)))
    vertex_index = {coordinate: index for index, coordinate in enumerate(coordinates)}
    volume = length**3
    planes = [(0, 1), (0, 2), (1, 2)]
    stabilizers = np.zeros((volume, 3 * volume), dtype=np.uint8)
    checks = np.zeros((3 * volume, 3 * volume), dtype=np.uint8)
    meta = np.zeros((volume, 3 * volume), dtype=np.uint8)

    def shift(coordinate, direction):
        result = list(coordinate)
        result[direction] = (result[direction] + 1) % length
        return tuple(result)

    def edge(coordinate, direction):
        return 3 * vertex_index[coordinate] + direction

    def face(coordinate, plane):
        return 3 * vertex_index[coordinate] + planes.index(plane)

    for coordinate in coordinates:
        vertex = vertex_index[coordinate]
        for direction in range(3):
            column = edge(coordinate, direction)
            stabilizers[vertex, column] ^= 1
            stabilizers[vertex_index[shift(coordinate, direction)], column] ^= 1
        for first, second in planes:
            row = face(coordinate, (first, second))
            for endpoint, direction in (
                (coordinate, first),
                (shift(coordinate, first), second),
                (shift(coordinate, second), first),
                (coordinate, second),
            ):
                checks[row, edge(endpoint, direction)] ^= 1
            normal = next(direction for direction in range(3) if direction not in (first, second))
            meta[vertex, row] ^= 1
            meta[vertex, face(shift(coordinate, normal), (first, second))] ^= 1
    return checks, stabilizers, meta, []


def lifted_product(lift):
    directory = SOURCE / "src/mqt/qecc/codes/instances/lifted_product"
    paths = [directory / f"lp_l={lift}_{sector}.npz" for sector in ("hx", "hz")]
    stabilizers, checks = [load_npz(path).toarray().astype(np.uint8) for path in paths]
    return checks, stabilizers, np.zeros((0, checks.shape[0]), dtype=np.uint8), paths


def construct(family, size):
    checks, stabilizers, meta, paths = (
        toric3d(size) if family == "toric3d" else lifted_product(size)
    )
    assert not np.any(checks @ stabilizers.T % 2)
    assert not np.any(meta @ checks % 2)
    code = css_code(stabilizers, checks)
    logical_checks = np.asarray(code.lz.toarray() if hasattr(code.lz, "toarray") else code.lz, dtype=np.uint8)
    num_logicals = checks.shape[1] - binary_rank(checks) - binary_rank(stabilizers)
    assert logical_checks.shape == (num_logicals, checks.shape[1])
    assert num_logicals > 0
    assert not np.any(stabilizers @ logical_checks.T % 2)
    assert binary_rank(np.vstack((checks, logical_checks))) == binary_rank(checks) + num_logicals
    if family == "toric3d":
        assert num_logicals == 3
        assert np.all(np.sum(checks, axis=1) == 4)
        assert np.all(np.sum(meta, axis=1) == 6)
    return checks, stabilizers, meta, logical_checks, paths
