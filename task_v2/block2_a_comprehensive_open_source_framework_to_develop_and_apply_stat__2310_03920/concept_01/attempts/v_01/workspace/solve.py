import csv
import json
import math
import os
from pathlib import Path
import resource
import shutil
import sys
import time

import numpy as np


PROFILES = {
    'baseline': dict(exact_limit=0, bond=16, sweeps=8, step=0.12,
                     energy_tol=1e-8, eig_tol=1e-9, cutoff=1e-12, optimize_layout=False,
                     general_symmetry=True, davidson_tol=1e-12, krylov_tol=1e-14),
    'production': dict(exact_limit=1000000, bond=128, sweeps=14, step=0.1,
                       energy_tol=1e-11, eig_tol=2e-12, cutoff=1e-16, optimize_layout=True,
                       general_symmetry=False, davidson_tol=1e-15, krylov_tol=1e-18),
    'refined': dict(exact_limit=1200000, bond=192, sweeps=20, step=0.05,
                    energy_tol=1e-12, eig_tol=2e-13, cutoff=1e-18, optimize_layout=True,
                    general_symmetry=False, davidson_tol=1e-17, krylov_tol=1e-20),
}


def sector_dimension(case):
    sites = case['n_sites']
    sector = case['sector']
    if sector['kind'] == 'number_sz':
        up = (sector['value'] + sector['twosz']) // 2
        down = sector['value'] - up
        electronic = math.comb(sites, up) * math.comb(sites, down)
    elif sector['kind'] == 'number':
        electronic = math.comb(2 * sites, sector['value'])
    elif sector['kind'] == 'parity':
        electronic = 2 ** (2 * sites - 1)
    else:
        raise ValueError('Unknown sector')
    return electronic * math.prod(mode['levels'] for mode in case.get('phonons', []))


def main():
    case_path, output_path = sys.argv[1:3]
    profile = sys.argv[3] if len(sys.argv) > 3 else 'production'
    output = Path(output_path).resolve()
    output.mkdir(parents=True, exist_ok=True)
    case = json.loads(Path(case_path).read_text())
    settings = dict(PROFILES[profile])
    settings.update(spin_orbitals=False, number_as_sz=False, one_site_after=None, sparse_memory_limit_mb=2600)
    if profile != 'baseline':
        if case['sector']['kind'] == 'number':
            settings.update(spin_orbitals=True, bond=160 if profile == 'production' else 224,
                            step=0.15 if profile == 'production' else 0.075,
                            one_site_after=0.25 if profile == 'production' else None)
        elif case['sector']['kind'] == 'parity':
            settings.update(spin_orbitals=True, bond=96 if profile == 'production' else 160,
                            step=0.15 if profile == 'production' else 0.075,
                            one_site_after=0.25 if profile == 'production' else None)
        elif case.get('phonons') and case['n_sites'] > 8 and profile == 'production':
            settings['bond'] = 96
    settings.update(json.loads(os.environ.get('ALE_SETTINGS', '{}')))
    broad_start = bool(case.get('phonons')) and profile != 'baseline'
    settings.setdefault('initial_bond', settings['bond'] if broad_start else min(32, settings['bond']))
    settings.setdefault('bond_schedule', [settings['bond']] if broad_start else
                        [min(32, settings['bond'])] * 2 + [min(64, settings['bond'])] * 2 + [settings['bond']])
    settings.update(threads=2, seed=1729, normalization_during_evolution=False,
                    sector=case['sector'], sector_dimension=sector_dimension(case))
    active_hops = sum(any(complex(*edge[stage][first][second]) != 0 for stage in ('before', 'after'))
                      for edge in case.get('edges', []) for first in range(2) for second in range(2))
    estimated_degree = 1 + active_hops / 2 + len(case.get('pairing', [])) / 2 + 2 * len(case.get('phonons', []))
    settings['estimated_sparse_mb'] = settings['sector_dimension'] * (16 * 48 + estimated_degree * 90) / 2 ** 20 + 100
    if Path(case_path).resolve() != output / 'case.json':
        shutil.copyfile(case_path, output / 'case.json')
    (output / 'profile.txt').write_text(profile + '\n')
    started = time.perf_counter()
    settings['single_tensor_fallback'] = case['n_sites'] + len(case.get('phonons', [])) == 1
    if (settings['single_tensor_fallback'] or
            (settings['sector_dimension'] <= settings['exact_limit']
             and settings['estimated_sparse_mb'] <= settings['sparse_memory_limit_mb'])):
        from sparse_solver import simulate
        settings['method'] = 'sector sparse diagonalization and exponential action'
    else:
        from tensor_solver import simulate
        settings['method'] = 'two-site DMRG and two-site TDVP'
        if settings['one_site_after'] is not None:
            settings['method'] += '; one-site TDVP after ' + str(settings['one_site_after'])
    (output / 'configuration.json').write_text(json.dumps(settings, indent=2))
    initial_energy, rows, diagnostics = simulate(case, settings, output)
    seconds = time.perf_counter() - started
    with (output / 'trajectory.csv').open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=['time', 'norm', 'charge', 'number', 'spin',
                                                    'phonon', 'current', 'source', 'energy'])
        writer.writeheader()
        writer.writerows(rows)
    stats = dict(initial_energy=initial_energy, seconds=seconds,
                 peak_rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                 settings=settings, profile=profile, case=case.get('id', ''), diagnostics=diagnostics)
    (output / 'stats.json').write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats), flush=True)


if __name__ == '__main__':
    main()
