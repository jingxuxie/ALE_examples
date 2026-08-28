import resource
import time
import sys
import numpy as np
from .model import extend, validate, matrices
from .protocols import drive_entries
from .spectral import prepare
from .propagate import evolve


CONFIGS = {
    'production': {'step': 0.065, 'quadrature_tolerance': 3e-7, 'order': 8, 'length_factor': 1.0, 'extra_cells': 16, 'stationary_cells': 128, 'singular_stationary_cells': 256},
    'conservative': {'step': 0.038, 'quadrature_tolerance': 2e-8, 'order': 10, 'length_factor': 1.3, 'extra_cells': 22, 'stationary_cells': 160, 'singular_stationary_cells': 320},
    'gold': {'step': 0.035, 'quadrature_tolerance': 2e-9, 'order': 10, 'length_factor': 1.25, 'extra_cells': 24, 'stationary_cells': 192, 'singular_stationary_cells': 384},
}
CONFIGS['ablation'] = dict(CONFIGS['production'], include_bound=False)


def simulate(case, config_name='production'):
    started = time.perf_counter()
    validate(case)
    config = dict(CONFIGS[config_name])
    central, leads = matrices(case)
    velocity_bound = max([2 * np.linalg.norm(hop, 2) for cell, hop, contact in leads] + [0])
    config['cells'] = max(4, int(np.ceil(max(case['times']) * velocity_bound / 2 * config['length_factor'])) + config['extra_cells'])
    hamiltonian, interfaces, ends = extend(case, config['cells'])
    energies, initial, metadata = prepare(case, hamiltonian, interfaces, ends, config)
    print(case['id'], 'prepared', initial.shape, 'in', time.perf_counter() - started, file=sys.stderr, flush=True)
    entries = drive_entries(case, interfaces)
    density, current = evolve(case, hamiltonian, energies, initial, entries, np.zeros(hamiltonian.shape[0]), config)
    metadata.update(config=config, seconds=time.perf_counter() - started, peak_rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, expanded_size=hamiltonian.shape[0])
    return {'times': case['times'], 'density': density, 'current': current}, metadata
