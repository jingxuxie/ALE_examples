import os
import time

STARTED = time.monotonic()
for name in ('OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'OMP_NUM_THREADS'):
    os.environ[name] = '1'

import argparse
import ctypes
import json
import sys
from pathlib import Path

import numpy as np


def solve(directory):
    directory = Path(directory).resolve()
    for location in (directory.parent.parent / 'workspace',
                     Path(__file__).resolve().parents[2] / 'participant' / 'workspace',
                     Path('/workspace')):
        if location.is_dir():
            sys.path.insert(0, str(location))
    from atlas import Atlas

    atlas = Atlas.load(directory)
    with np.load(directory / 'arrays.npz', allow_pickle=False) as archive:
        baseline = np.asarray(archive['baseline_choices'], dtype=np.int32)
    vertices = atlas.vertices
    widths = np.array([1] * vertices + [2] * len(atlas.edges) +
                      [4] * len(atlas.plaquettes), dtype=np.int32)
    members = np.full((len(widths), 4), -1, dtype=np.int32)
    members[:vertices, 0] = np.arange(vertices)
    members[vertices:vertices + len(atlas.edges), :2] = atlas.edges
    members[vertices + len(atlas.edges):] = atlas.plaquettes
    values = []
    for losses, flux, invalid in (
        (atlas.unary, None, None),
        (atlas.pair, None, np.any(atlas.link_magnitude < atlas.minimum_link, axis=0)),
        (atlas.face, atlas.flux,
         np.any(np.pi - np.abs(atlas.flux) < atlas.branch_margin, axis=0)),
    ):
        normalized = losses / atlas.normalizers.reshape((-1,) + (1,) * (losses.ndim - 1))
        flat = np.moveaxis(normalized, 0, -1).reshape(-1, 4)
        table = np.zeros((len(flat), 9), dtype=np.float64)
        table[:, :4] = flat
        if flux is not None:
            table[:, 4:8] = np.moveaxis(flux, 0, -1).reshape(-1, 4)
        if invalid is not None:
            table[:, 8] = invalid.reshape(-1)
        values.append(table)
    tables = np.ascontiguousarray(np.concatenate(values))
    costs = np.ascontiguousarray(atlas.costs, dtype=np.int32)
    anchors = np.full(vertices, -1, dtype=np.int32)
    for vertex, choice in atlas.anchors.items():
        anchors[vertex] = choice
    weights = np.ascontiguousarray(atlas.mean_weight * atlas.weights / atlas.weights.sum())
    library = ctypes.CDLL(str(Path(__file__).with_name('optimizer.so')))
    integer_pointer = ctypes.POINTER(ctypes.c_int)
    double_pointer = ctypes.POINTER(ctypes.c_double)
    library.optimize.argtypes = [ctypes.c_int, ctypes.c_int, integer_pointer,
                                 integer_pointer, double_pointer, integer_pointer,
                                 integer_pointer, integer_pointer, double_pointer,
                                 ctypes.c_int, ctypes.c_double, ctypes.c_uint64,
                                 integer_pointer]
    deadline = STARTED + float(os.environ.get('ATLAS_SECONDS', '78'))
    seed = int(os.environ.get('ATLAS_SEED', '81473'))

    def polish(initial, seconds):
        nonlocal seed
        answer = np.ascontiguousarray(initial, dtype=np.int32).copy()
        seed += 7919
        library.optimize(vertices, len(widths), widths.ctypes.data_as(integer_pointer),
                         members.ctypes.data_as(integer_pointer), tables.ctypes.data_as(double_pointer),
                         costs.ctypes.data_as(integer_pointer), anchors.ctypes.data_as(integer_pointer),
                         answer.ctypes.data_as(integer_pointer), weights.ctypes.data_as(double_pointer),
                         atlas.budget, max(0.001, seconds), seed,
                         answer.ctypes.data_as(integer_pointer))
        return answer

    answer = polish(baseline, min(1.5, max(0.001, deadline - time.monotonic())))
    lower_bound = 0.0
    if deadline - time.monotonic() > 8 and not os.environ.get('ATLAS_NO_LP'):
        from linear import refine
        answer, lower_bound = refine(atlas, answer, min(30.0, deadline - time.monotonic() - 3), polish)
    while deadline - time.monotonic() > 0.05:
        value = atlas.score(answer)['objective']
        if value - lower_bound <= max(1e-8, 0.0001 * value):
            break
        answer = polish(answer, min(3.0, deadline - time.monotonic()))
    result = atlas.score(answer)
    if not result['feasible'] or result['objective'] > atlas.score(baseline)['objective'] + 1e-12:
        answer = baseline
    return answer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    choices = solve(arguments.input)
    Path(arguments.output).write_text(json.dumps({'choices': choices.tolist()}) + '\n')


if __name__ == '__main__':
    main()
