import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

from generated import generate, restrict
from numerics import diagonalize, hamiltonian
from physics import physical_couplings
from tails import SpectralTail, contractions, tail_matrix


def run(source, destination, maximum=32, methods=None, cutoffs=None):
    request = json.loads(Path(source).read_text())
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    for case in request['cases']:
        if max(term['degree'] for term in case['couplings']) < 3:
            continue
        coefficients, constant = physical_couplings(case)
        terms = contractions(coefficients, case['boundary'])
        keys = sorted(set(coefficients) | {(key[0], key[1]) for key in terms})
        spectral = SpectralTail(case, terms, destination / case['id'] / 'tail')
        for sector in case['sectors']:
            generated = generate(case, sector, maximum, keys, destination / case['id'] / sector['name'])
            print(case['id'], sector['name'], 'dimension', len(generated['energy']), 'generation',
                  generated['generation_seconds'], 'events', spectral.count_events, flush=True)
            for cutoff in cutoffs or [16, 20, 24, 28, 32, 36, 40]:
                if cutoff > maximum:
                    continue
                basis = restrict(generated, cutoff)
                base = hamiltonian(basis, coefficients, constant)
                for method in methods or ['raw', 'local', 'spectator']:
                    started = time.perf_counter()
                    matrix = base
                    if method != 'raw':
                        matrix = base + tail_matrix(basis, cutoff, terms, spectral, variant=method)
                    values, vectors, residual = diagonalize(matrix, 3, True)
                    if method == 'spectator':
                        for level in range(3):
                            corrected = base + tail_matrix(basis, cutoff, terms, spectral,
                                                           eigenvalue=values[level] - constant)
                            values[level] = vectors[:, level] @ (corrected @ vectors[:, level])
                    print(case['id'], sector['name'], cutoff, method, np.round(values, 7),
                          'seconds', round(time.perf_counter() - started, 3), flush=True)
                    for level, energy in enumerate(values):
                        records.append(dict(case=case['id'], sector=sector['name'], cutoff=cutoff,
                                            method=method, level=level, energy=energy, dimension=len(basis['energy']),
                                            seconds=time.perf_counter() - started))
                    with (destination / 'convergence.csv').open('w', newline='') as handle:
                        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
                        writer.writeheader()
                        writer.writerows(records)


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 32,
        sys.argv[4].split(',') if len(sys.argv) > 4 else None,
        [float(value) for value in sys.argv[5].split(',')] if len(sys.argv) > 5 else None)
