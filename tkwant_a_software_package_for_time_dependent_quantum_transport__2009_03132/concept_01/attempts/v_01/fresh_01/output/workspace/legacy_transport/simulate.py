import resource
import time
from .model import extend, validate
from .protocols import drive_entries
from .initialize import prepare
from .boundaries import absorption
from .propagate import evolve


CONFIGS = {
    'production': {'cells': 18, 'step': 0.08, 'absorption': 0.35},
    'conservative': {'cells': 30, 'step': 0.04, 'absorption': 0.35},
}


def simulate(case, config_name='production'):
    started = time.perf_counter()
    validate(case)
    config = dict(CONFIGS[config_name])
    hamiltonian, interfaces, ends = extend(case, config['cells'])
    energies, initial, metadata = prepare(case, hamiltonian, interfaces, ends, config)
    absorb = absorption(hamiltonian, interfaces, ends, config)
    entries = drive_entries(case, interfaces)
    density, current = evolve(case, hamiltonian, energies, initial, entries, absorb, config)
    metadata.update(config=config, seconds=time.perf_counter() - started, peak_rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
    return {'times': case['times'], 'density': density, 'current': current}, metadata
