import numpy as np


def read_tables(data):
    for row, center in enumerate(data["centers"]):
        size = int(data["scope_size"][row])
        scope = tuple(int(value) for value in data["scope_nodes"][row, :size])
        start, stop = data["local_ptr"][row:row + 2]
        table = data["local_probs"][start:stop].reshape((2,) * size, order="F")
        yield int(center), scope, table


def marginal(table, axes):
    axes = tuple(axes)
    removed = tuple(axis for axis in range(table.ndim) if axis not in axes)
    reduced = table.sum(axis=removed)
    retained = sorted(axes)
    return reduced.transpose(tuple(retained.index(axis) for axis in axes))


def pair_information(table, first, second):
    pair = marginal(table, (first, second))
    product = pair.sum(axis=1)[:, None] * pair.sum(axis=0)[None, :]
    return float(np.sum(pair * np.log2(pair / product)))


def conditional_information(table, first_axes, second_axes, given_axes):
    raise NotImplementedError("Grouped conditional analysis is not implemented")
