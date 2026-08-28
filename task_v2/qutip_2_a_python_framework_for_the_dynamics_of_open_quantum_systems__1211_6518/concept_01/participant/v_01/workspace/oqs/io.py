import json
from pathlib import Path

import numpy as np


def load_case(filename):
    filename = Path(filename)
    case = json.loads(filename.read_text())
    with np.load(filename.parent / case['arrays'], allow_pickle=False) as arrays:
        case.update({name: arrays[name] for name in arrays.files})
    return case


def scalar(value):
    return complex(*value) if isinstance(value, list) else complex(value)


def coefficient(specification, time):
    kind = specification['kind']
    amplitude = scalar(specification.get('amplitude', 1.0))
    offset = scalar(specification.get('offset', 0.0))
    phase = specification.get('phase', 0.0)
    frequency = specification.get('omega', 1.0)
    if kind == 'constant':
        return scalar(specification.get('value', 1.0))
    if kind in ('sin', 'cos'):
        function = np.sin if kind == 'sin' else np.cos
        return offset + amplitude * function(frequency * time + phase)
    if kind == 'carrier':
        return offset + amplitude * np.exp(1j * (frequency * time + phase))
    if kind == 'gaussian':
        return offset + amplitude * np.exp(-0.5 * ((time - specification['center']) / specification['width']) ** 2)
    if kind == 'decay':
        return offset + amplitude * np.exp(-specification['rate'] * time)
    if kind == 'steps':
        index = np.searchsorted(specification['edges'], time, side='right')
        return scalar(specification['values'][index])
    raise ValueError('Unsupported coefficient: ' + kind)


def hamiltonian(case, time):
    result = case['H0'].copy()
    for operator, specification in zip(case['h_ops'], case['h_coeffs']):
        result += coefficient(specification, time) * operator
    return result
