import copy
from pathlib import Path

import numpy as np
from scipy.linalg import expm

from .diagnostics import distance
from .io import load_case


def random_basis(dimension):
    random = np.random.default_rng(8201 + dimension)
    matrix = random.normal(size=(dimension, dimension)) + 1j * random.normal(size=(dimension, dimension))
    return np.linalg.qr(matrix)[0]


def rotate(case, basis):
    result = copy.deepcopy(case)
    for name in ['H0', 'rho0', 'h_ops', 'c_ops', 'a_ops', 'e_ops']:
        result[name] = basis @ case[name] @ basis.conj().T
    return result


def oscillator(dimension):
    lowering = np.diag(np.sqrt(np.arange(1, dimension)), 1).astype(complex)
    number = lowering.conj().T @ lowering
    displacement = expm((0.7 + 0.4j) * lowering.conj().T - (0.7 - 0.4j) * lowering)
    populations = 0.5 ** np.arange(dimension)
    initial = displacement @ np.diag(populations / populations.sum()) @ displacement.conj().T
    return {'id': 'resource_oscillator_' + str(dimension), 'family': 'controlled_resonator',
            'physics': 'lindblad', 'H0': 0.12 * number + 0.0008 * number @ number,
            'h_ops': np.array([lowering + lowering.conj().T, 1j * (lowering.conj().T - lowering)]),
            'h_coeffs': [{'kind': 'gaussian', 'amplitude': 2.1, 'center': 3.1, 'width': 0.13},
                         {'kind': 'steps', 'edges': [1.31, 1.38, 4.7], 'values': [0, 3.7, -0.04, 0.25]}],
            'c_ops': np.array([lowering, lowering.conj().T, 0.1 * number]),
            'c_coeffs': [{'kind': 'decay', 'amplitude': 0.6, 'offset': 0.17, 'rate': 0.3},
                         {'kind': 'carrier', 'amplitude': [0.19, 0.09], 'offset': 0.11, 'omega': 1.7},
                         {'kind': 'steps', 'edges': [2.3, 3.7], 'values': [0.08, 0.31, 0.12]}],
            'a_ops': np.empty((0, dimension, dimension), complex), 'baths': [],
            'rho0': initial, 'e_ops': np.array([number, lowering + lowering.conj().T,
                                               1j * (lowering.conj().T - lowering)]),
            'times': np.unique(np.append(np.linspace(0.17, 8.17, 65), [1.31, 1.38, 2.3, 3.1, 3.7, 4.7]))}


def resource_study(output_directory, configurations):
    from .experiment import isolated_run
    rows = []
    for dimension in [16, 32, 64, 112]:
        case = oscillator(dimension)
        implementations = ['structured', 'dense'] if dimension in [32, 64] else ['structured']
        if dimension == 112:
            implementations.extend(['rotated_structured', 'refined'])
        reference = None
        for implementation in implementations:
            options = dict(configurations['refined'] if implementation == 'refined' else configurations['production'],
                           dense_operators=implementation == 'dense')
            basis = random_basis(dimension) if implementation == 'rotated_structured' else np.eye(dimension)
            supplied = rotate(case, basis) if implementation == 'rotated_structured' else case
            raw, metrics = isolated_run(supplied, output_directory / 'runs' / case['id'] / implementation,
                                        options, implementation)
            laboratory = dict(raw, states=basis.conj().T @ raw['states'] @ basis)
            if reference is None:
                reference = laboratory
            rows.append({'row_id': case['id'] + '/' + implementation, **metrics,
                         'study': 'controlled_size', 'implementation': implementation,
                         'boundary_population': float(laboratory['states'][:, -1, -1].real.max()),
                         'distance_to_comparator': distance(laboratory, reference)})
    return rows


def controlled_studies(input_directory, output_directory, configurations):
    from .experiment import isolated_run, write_table
    rows = []
    for filename in sorted(Path(input_directory).glob('*.json')):
        case = load_case(filename)
        with np.load(output_directory / 'runs' / case['id'] / 'production' / 'result.npz', allow_pickle=False) as archive:
            production = {key: archive[key] for key in archive.files}
        variants = []
        if case['physics'] == 'redfield':
            variants.append(('toggle_secular', dict(case, secular=not case.get('secular', False)),
                             configurations['production']))
        elif case['physics'] == 'floquet':
            for cutoff in [0, 1, 3, 6]:
                variants.append(('harmonics_' + str(cutoff), case,
                                 dict(configurations['production'], samples=256, harmonics=cutoff, adaptive_harmonics=False)))
            variants.append(('quasienergy_branches', case,
                             dict(configurations['production'], branch_shifts=list(range(-len(case['H0']), 0)))))
            variants.append(('absolute_period_shift', dict(case, times=case['times'] + 1701 * case['period']),
                             configurations['production']))
        for label, variant, options in variants:
            raw, metrics = isolated_run(variant, output_directory / 'runs' / case['id'] / label, options, label)
            rows.append({'row_id': case['id'] + '/' + label, **metrics,
                         'comparator': case['id'] + '/production', 'distance_to_comparator': distance(raw, production)})
        if case['physics'] == 'floquet':
            times = case['times'][0] + case['period'] * np.array([0, 0.137, 0.5, 1.23, 17.717, 123.217, 2001.31, 10000.173])
            extended = dict(case, times=times)
            long_runs = {}
            for configuration in ['production', 'refined']:
                label = 'long_' + configuration
                long_runs[configuration] = isolated_run(extended, output_directory / 'runs' / case['id'] / label,
                                                        configurations[configuration], label)
            for configuration, (raw, metrics) in long_runs.items():
                comparator = 'refined' if configuration == 'production' else 'production'
                rows.append({'row_id': case['id'] + '/long_' + configuration, **metrics,
                             'comparator': case['id'] + '/long_' + comparator,
                             'distance_to_comparator': distance(raw, long_runs[comparator][0])})
    write_table(output_directory / 'controlled.csv', rows)
