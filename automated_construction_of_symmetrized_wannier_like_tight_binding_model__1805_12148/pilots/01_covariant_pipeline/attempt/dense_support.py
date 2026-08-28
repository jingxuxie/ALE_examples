"""Dense compatibility for the historical sparse constructor interface."""

from types import SimpleNamespace

import numpy as np


def dense_csr(value, dtype=complex, shape=None):
    if isinstance(value, tuple) and len(value) == 2:
        data, indices = value
        matrix = np.zeros(shape, dtype=dtype)
        np.add.at(matrix, indices, data)
        return matrix
    return np.asarray(value, dtype=dtype)


sp = SimpleNamespace(csr=dense_csr)
