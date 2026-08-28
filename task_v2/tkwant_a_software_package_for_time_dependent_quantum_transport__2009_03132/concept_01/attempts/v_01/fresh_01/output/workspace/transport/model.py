import json
from pathlib import Path
import numpy as np
from scipy import sparse


def decode(value):
    if isinstance(value, dict):
        return np.asarray(value['real'], dtype=float) + 1j * np.asarray(value['imag'], dtype=float)
    return np.asarray(value, dtype=complex)


def encode(value):
    array = np.asarray(value)
    return {'real': array.real.tolist(), 'imag': array.imag.tolist()}


def load_suite(path):
    with open(path) as handle:
        return json.load(handle)['cases']


def matrices(case):
    central = decode(case['hamiltonian'])
    leads = []
    for spec in case['leads']:
        leads.append((decode(spec['cell']), decode(spec['hop']), decode(spec['contact'])))
    return central, leads


def extend(case, cells):
    central, leads = matrices(case)
    sizes = [central.shape[0]] + [cells * lead[0].shape[0] for lead in leads]
    offsets = np.cumsum([0] + sizes)
    matrix = sparse.lil_matrix((sum(sizes), sum(sizes)), dtype=complex)
    matrix[:sizes[0], :sizes[0]] = central
    interfaces = []
    ends = []
    for index, (cell, hop, contact) in enumerate(leads):
        width = len(cell)
        start = offsets[index + 1]
        interfaces.append(np.arange(start, start + width))
        ends.append(np.arange(start + (cells - 1) * width, start + cells * width))
        matrix[:sizes[0], start:start + width] = contact
        matrix[start:start + width, :sizes[0]] = contact.conj().T
        for position in range(cells):
            begin = start + position * width
            matrix[begin:begin + width, begin:begin + width] = cell
            if position:
                matrix[begin:begin + width, begin - width:begin] = hop
                matrix[begin - width:begin, begin:begin + width] = hop.conj().T
    return matrix.tocsr(), interfaces, ends


def validate(case):
    central, leads = matrices(case)
    assert central.ndim == 2 and central.shape[0] == central.shape[1]
    assert np.max(abs(central - central.conj().T)) < 1e-12
    for cell, hop, contact in leads:
        assert cell.shape == hop.shape
        assert np.max(abs(cell - cell.conj().T)) < 1e-12
        assert contact.shape == (len(central), len(cell))
    times = np.asarray(case['times'])
    assert times[0] == 0 and np.all(np.diff(times) > 0)
    return True
