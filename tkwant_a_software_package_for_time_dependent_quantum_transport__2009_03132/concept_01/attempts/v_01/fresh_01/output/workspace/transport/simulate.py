import resource
import time
import numpy as np
from scipy import sparse
from .model import extend, validate, matrices
from .protocols import drive_entries
from .scattering import prepare_scattering
from .source_evolution import evolve_source


CONFIGS = {
    'production': {'minimum_cells': 64, 'boundary_guard': 28, 'length_factor': 1.0,
                   'maximum_cells': 112, 'absorber_cells': 64, 'absorber_strength': 0.8,
                   'quadrature_tolerance': 2e-7, 'quadrature_max_depth': 12, 'quadrature_output_order': 8,
                   'bound_tail_tolerance': 1e-10, 'bound_cells': 128, 'state_batch_size': 128,
                   'rtol': 3e-8, 'atol': 3e-10,
                   'max_step': 0.5, 'preparation': 'independent_occupations'},
    'conservative': {'minimum_cells': 96, 'boundary_guard': 42, 'length_factor': 1.3,
                     'maximum_cells': 168, 'absorber_cells': 96, 'absorber_strength': 0.8,
                     'quadrature_tolerance': 2e-8, 'quadrature_max_depth': 14, 'quadrature_output_order': 16,
                     'bound_tail_tolerance': 1e-12, 'bound_cells': 192, 'state_batch_size': 128,
                     'rtol': 3e-10, 'atol': 3e-12,
                     'max_step': 0.3, 'preparation': 'independent_occupations'},
}
CONFIGS['ablation'] = dict(CONFIGS['production'], preparation='averaged_occupations')


def simulate(case, config_name='production'):
    started = time.perf_counter()
    validate(case)
    config = dict(CONFIGS[config_name])
    central, leads = matrices(case)
    maximum_hop = max([np.linalg.norm(hop, 2) for cell, hop, contact in leads] + [0.])
    requested_cells = max(config['minimum_cells'], int(np.ceil(
        config['length_factor'] * maximum_hop * case['times'][-1])) + config['boundary_guard'])
    config['cells'] = min(requested_cells, config['maximum_cells'])
    config['unabsorbed_cells_requested'] = requested_cells
    config['boundary'] = 'hard_wall_beyond_round_trip_light_cone'
    hamiltonian, interfaces, ends = extend(case, config['cells'])
    energies, initial, active, metadata = prepare_scattering(case, hamiltonian, interfaces, ends, config)
    metadata['preparation_seconds'] = time.perf_counter() - started
    entries = drive_entries(case, interfaces)
    propagation_hamiltonian = hamiltonian
    if requested_cells > config['maximum_cells']:
        profile = np.zeros(hamiltonian.shape[0])
        for interface, end, (cell, hop, contact) in zip(interfaces, ends, leads):
            count = config['absorber_cells']
            values = config['absorber_strength'] * max(1., 2 * np.linalg.norm(hop, 2)) * (np.arange(1, count + 1) / count) ** 4
            start = int(end[-1]) + 1 - count * len(cell)
            profile[start:int(end[-1]) + 1] = np.repeat(values, len(cell))
        propagation_hamiltonian = hamiltonian - 1j * sparse.diags(profile, format='csr')
        config['boundary'] = 'quartic_absorber_on_driven_correction_only'
    density, current, evolution_metadata = evolve_source(case, propagation_hamiltonian, energies, initial, active, entries, config)
    metadata.update(evolution_metadata)
    metadata['embedded_dimension'] = hamiltonian.shape[0]
    metadata.update(config=config, seconds=time.perf_counter() - started, peak_rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
    return {'times': case['times'], 'density': density, 'current': current}, metadata
