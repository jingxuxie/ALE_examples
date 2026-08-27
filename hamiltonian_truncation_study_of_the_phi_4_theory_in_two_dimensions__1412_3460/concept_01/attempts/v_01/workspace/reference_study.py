import json
import resource
import sys
import time
from pathlib import Path

from generated import generate
from physics import physical_couplings
from refinement import refined_levels
from tails import SpectralTail, contractions


def run(request_path, destination, maximum=38):
    request = json.loads(Path(request_path).read_text())
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    records = {}
    started = time.perf_counter()
    for case in request['cases']:
        if max(term['degree'] for term in case['couplings']) < 3:
            continue
        coefficients, constant = physical_couplings(case)
        terms = contractions(coefficients, case['boundary'])
        keys = sorted(set(coefficients) | {key[:2] for key in terms})
        spectral = SpectralTail(case, terms, destination / case['id'] / 'tail')
        records[case['id']] = {}
        for sector in case['sectors']:
            window = 8 if sector['momentum'] is None else 1000000
            basis = generate(case, sector, maximum, keys, destination / case['id'] / sector['name'], momentum_window=window)
            refined = refined_levels(basis, maximum, coefficients, constant, terms, spectral, sample_step=1.0)
            refined['dimension'] = len(basis['energy'])
            records[case['id']][sector['name']] = refined
            print(case['id'], sector['name'], refined['levels'], 'seconds', refined['seconds'], flush=True)
            (destination / 'reference.json').write_text(json.dumps(records, indent=2))
            del basis
    (destination / 'resources.json').write_text(json.dumps({'wall_seconds': time.perf_counter() - started,
                                                           'peak_rss_mb': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024}, indent=2))


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 38)
