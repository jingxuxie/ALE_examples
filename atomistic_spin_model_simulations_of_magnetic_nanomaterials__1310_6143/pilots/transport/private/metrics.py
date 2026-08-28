import math
import numpy as np

GROUPS = {
    'resistance': ['total_resistance_ohm', 'stack_resistance_ohm', 'cell_resistance_ohm'],
    'current': ['total_current_A', 'stack_current_A', 'channel_current_A'],
    'field': ['atom_field_T'],
    'derivative': ['atom_dspin_dt'],
}


def errors(predicted, expected):
    result = {}
    for group, keys in GROUPS.items():
        components = []
        for key in keys:
            candidate = np.asarray(predicted[key], dtype=float)
            truth = np.asarray(expected[key], dtype=float)
            if candidate.shape != truth.shape or not np.isfinite(candidate).all():
                raise ValueError('Invalid shape or nonfinite output: '+key)
            floor = {'resistance': 1e-12, 'current': 1e-18, 'field': 1e-18, 'derivative': 1e-7}[group]
            scale = max(float(np.sqrt(np.mean(truth*truth))), floor)
            with np.errstate(over='ignore', invalid='ignore'):
                component = float(np.sqrt(np.mean((candidate-truth)**2)))/scale
            if not math.isfinite(component):
                raise ValueError('Numerically unbounded error: '+key)
            components.append(component)
        result[group] = float(np.mean(components))
    return result


def scores(error, weak_error):
    return {group: math.exp(-math.log(2)*error[group]/weak_error[group]) for group in GROUPS}
