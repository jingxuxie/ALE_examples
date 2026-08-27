import argparse
import csv
import gc
import json
import resource
import time
from pathlib import Path

import numpy as np

from generated import generate
from io_archive import load_archive
from numerics import diagonalize, hamiltonian
from physics import gaussian_vacuum, physical_couplings
from plotting import plot_results
from refinement import refined_levels
from tails import SpectralTail, contractions, tail_matrix


FIELDS = ['row_id', 'case', 'family', 'method', 'cutoff', 'sector', 'level',
          'energy', 'gap', 'dimension', 'elapsed_s', 'vacuum_energy', 'uncertainty',
          'retained_dimension', 'generated_dimension', 'generated_cutoff', 'momentum_window']
SCALING_FIELDS = ['case', 'method', 'cutoff', 'dimension', 'elapsed_s', 'peak_rss_mb',
                  'retained_dimension', 'generated_dimension', 'generated_cutoff',
                  'momentum_window', 'loop_events', 'shared_setup_s', 'incremental_s']


def write_csv(path, records, fields):
    with Path(path).open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def peak_memory():
    return max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) / 1024


def is_gaussian(case):
    return all(term['degree'] == 2 and term.get('transfer', 0) == 0 for term in case['couplings'])


def prepare_case(case, directory):
    started = time.perf_counter()
    coefficients, constant = physical_couplings(case)
    terms = contractions(coefficients, case['boundary'])
    spectral = SpectralTail(case, terms, directory / 'spectral') if terms else None
    output = {'levels': {}, 'raw': {}, 'local': {}, 'uncertainty': {}, 'dimension': 0,
              'generated_cutoff': 0.0, 'momentum_window': None,
              'loop_events': spectral.count_events if spectral is not None else 0,
              'coefficients': coefficients, 'constant': constant, 'terms': terms,
              'spectral': spectral, 'diagnostics': {}}
    if is_gaussian(case):
        physical_mass, vacuum = gaussian_vacuum(case)
        transformed = dict(case, mass=physical_mass)
        minimum_frequency = np.hypot(physical_mass, np.pi / case['length']) if case['boundary'] == 'antiperiodic' else physical_mass
        for index, sector in enumerate(case['sectors']):
            basis = generate(transformed, sector, 6 * minimum_frequency, [], directory / f'gaussian_{index}')
            output['levels'][sector['name']] = (basis['energy'][:3] + vacuum).tolist()
            output['uncertainty'][sector['name']] = [1e-12] * 3
            output['dimension'] += len(basis['energy'])
        output['vacuum'] = vacuum
        output['generated_cutoff'] = 6 * minimum_frequency
        output['diagnostics']['gaussian_physical_mass'] = physical_mass
        output['seconds'] = time.perf_counter() - started
        return output
    maximum = max(34 * case['mass'], max(case['cutoffs']))
    maximum_transfer = max(abs(term.get('transfer', 0)) for term in case['couplings'])
    unprojected = any(sector['momentum'] is None for sector in case['sectors'])
    window = max(8, 4 * maximum_transfer) if unprojected else 1000000
    budget = 45000
    while True:
        dimensions = []
        for index, sector in enumerate(case['sectors']):
            counted = generate(case, sector, maximum, [], directory / f'count_{index}', momentum_window=window)
            dimensions.append(len(counted['energy']))
        if max(dimensions) <= budget or maximum <= max(case['cutoffs']) + 0.1:
            break
        maximum = max(max(case['cutoffs']), maximum - case['mass'])
    keys = sorted(set(coefficients) | {key[:2] for key in terms})
    output['generated_cutoff'] = maximum
    output['momentum_window'] = window if unprojected else None
    output['loop_events'] = spectral.count_events
    for index, sector in enumerate(case['sectors']):
        basis = generate(case, sector, maximum, keys, directory / f'sector_{index}', momentum_window=window)
        refined = refined_levels(basis, maximum, coefficients, constant, terms, spectral,
                                 sample_step=0.5 * case['mass'], minimum=maximum - 8 * case['mass'])
        name = sector['name']
        output['levels'][name] = sorted(refined['levels'])
        output['raw'][name] = refined['raw']
        output['local'][name] = refined['local']
        output['uncertainty'][name] = refined['uncertainty']
        output['dimension'] += len(basis['energy'])
        output['diagnostics'][name] = refined
        output['diagnostics'][name]['dimension'] = len(basis['energy'])
        output['diagnostics'][name]['generation_seconds'] = basis['generation_seconds']
        del basis
        gc.collect()
    output['vacuum'] = min(values[0] for values in output['levels'].values())
    output['seconds'] = time.perf_counter() - started
    return output


def run(request_path, destination):
    started = time.perf_counter()
    request_path = Path(request_path).resolve()
    request = json.loads(request_path.read_text())
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    root = Path(request['archive_root'])
    if not root.is_absolute():
        root = request_path.parent / root
    records, scaling, diagnostics = [], [], {}
    for case_index, case in enumerate(request['cases']):
        print(f"Preparing {case['id']}", flush=True)
        work = prepare_case(case, destination / 'work' / f'case_{case_index}')
        diagnostics[case['id']] = {'generated_cutoff': work['generated_cutoff'],
                                  'generated_dimension': work['dimension'],
                                  'momentum_window': work['momentum_window'],
                                  'loop_events': work['loop_events'], 'details': work['diagnostics']}
        for cutoff in case['cutoffs']:
            archive_started = time.perf_counter()
            manifest, sectors = load_archive(root / case['archive'], cutoff,
                                             [sector['name'] for sector in case['sectors']])
            for parameter in ['mass', 'length']:
                if abs(manifest[parameter] - case[parameter]) > 1e-9:
                    raise ValueError(f'Archive/request mismatch: {parameter}')
            if manifest['boundary'] != case['boundary']:
                raise ValueError('Archive/request boundary mismatch')
            for specified in case['sectors']:
                archived = next(item for item in manifest['sectors'] if item['name'] == specified['name'])
                if any(archived[key] != specified[key] for key in ['momentum', 'parity']):
                    raise ValueError('Archive/request sector mismatch')
            retained_dimension = sum(len(sector['energy']) for sector in sectors.values())
            load_seconds = time.perf_counter() - archive_started
            configurations = [('production', work['levels'], work['seconds'], work['dimension'], work['vacuum'])]
            for method in ['raw', 'local_tail']:
                method_started = time.perf_counter()
                levels = {}
                for name, sector in sectors.items():
                    matrix = hamiltonian(sector, work['coefficients'], work['constant'])
                    if method == 'local_tail' and work['spectral'] is not None:
                        matrix += tail_matrix(sector, cutoff, work['terms'], work['spectral'], variant='local')
                    elif method == 'local_tail':
                        from tails import SpectralTail
                        local_spectral = SpectralTail(case, work['terms'], destination / 'work' / f'case_{case_index}' / 'gaussian_tail')
                        matrix += tail_matrix(sector, cutoff, work['terms'], local_spectral, variant='local')
                    levels[name] = diagonalize(matrix).tolist()
                seconds = time.perf_counter() - method_started + load_seconds
                configurations.append((method, levels, seconds, retained_dimension,
                                       min(values[0] for values in levels.values())))
            if work['raw']:
                configurations += [('generated_raw', work['raw'], work['seconds'], work['dimension'],
                                    min(values[0] for values in work['raw'].values())),
                                   ('generated_local', work['local'], work['seconds'], work['dimension'],
                                    min(values[0] for values in work['local'].values()))]
            for method, levels, seconds, dimension, vacuum in configurations:
                generated = method in ['production', 'generated_raw', 'generated_local']
                scaling.append({'case': case['id'], 'method': method, 'cutoff': cutoff,
                                'dimension': dimension, 'elapsed_s': seconds, 'peak_rss_mb': peak_memory(),
                                'retained_dimension': retained_dimension,
                                'generated_dimension': work['dimension'] if generated else 0,
                                'generated_cutoff': work['generated_cutoff'] if generated else 0,
                                'momentum_window': work['momentum_window'] if generated else None,
                                'loop_events': work['loop_events'] if method != 'raw' else 0,
                                'shared_setup_s': work['seconds'] if generated else 0,
                                'incremental_s': 0 if generated else seconds})
                for name, values in levels.items():
                    for level, energy in enumerate(values[:3]):
                        row_id = f"{case['id']}:{method}:{cutoff:g}:{name}:{level}"
                        records.append({'row_id': row_id, 'case': case['id'], 'family': case['family'],
                                        'method': method, 'cutoff': cutoff, 'sector': name, 'level': level,
                                        'energy': energy, 'gap': energy - vacuum, 'dimension': dimension,
                                        'elapsed_s': seconds, 'vacuum_energy': vacuum,
                                        'uncertainty': work['uncertainty'][name][level] if method == 'production' else '',
                                        'retained_dimension': retained_dimension,
                                        'generated_dimension': work['dimension'] if generated else 0,
                                        'generated_cutoff': work['generated_cutoff'] if generated else 0,
                                        'momentum_window': work['momentum_window'] if generated else None})
        print(f"Finished {case['id']}: generated dimension={work['dimension']}, "
              f"cutoff={work['generated_cutoff']:g}, setup={work['seconds']:.2f}s", flush=True)
        del work
        gc.collect()
    write_csv(destination / 'results.csv', [row for row in records if row['method'] == 'production'], FIELDS)
    write_csv(destination / 'ablation.csv', [row for row in records if row['method'] != 'production'], FIELDS)
    write_csv(destination / 'scaling.csv', scaling, SCALING_FIELDS)
    claims = []
    for case in request['cases']:
        cutoffs = sorted(set(case['cutoffs']))
        if len(cutoffs) < 2:
            continue
        candidates = [row for row in records if row['case'] == case['id'] and row['method'] == 'production'
                      and row['cutoff'] == cutoffs[-1]]
        vacuum_row = min(candidates, key=lambda row: row['energy'])
        excited_row = min((row for row in candidates if row['gap'] > 1e-8), key=lambda row: row['gap'])
        for quantity, example in [('energy', vacuum_row), ('gap', excited_row)]:
            selected = [next(row for row in records if row['case'] == case['id']
                             and row['sector'] == example['sector'] and row['level'] == example['level']
                             and row['cutoff'] == cutoff and row['method'] == method)
                        for method in ['production', 'raw'] for cutoff in [cutoffs[-2], cutoffs[-1]]]
            ratio = abs(selected[1][quantity] - selected[0][quantity]) / max(abs(selected[3][quantity] - selected[2][quantity]), 1e-12)
            claims.append({'id': f"{case['id']}_{quantity}_drift", 'kind': 'cutoff_drift_ratio',
                           'statement': 'Requested-cutoff drift with independent generated refinement held fixed; not an accuracy test.',
                           'rows': [row['row_id'] for row in selected], 'quantity': quantity,
                           'value': ratio, 'conclusion': 'improved' if ratio < 1 else 'not_improved'})
    discussion = ['Production independently generates its working basis, without importing archive states above the requested cutoff.',
                  'Its generated work cutoff is held fixed across requested cutoffs: zero drift is by construction, not proof of accuracy.',
                  'Generated-raw spectra are also flat in requested cutoff but retain a sizable omitted-state bias.',
                  'Convergence and extrapolation sensitivity are recorded in diagnostics.json; Gaussian accuracy has an exact independent check.',
                  'Elapsed setup time is measured once per case and repeated on reused configuration rows; these rows are not additive.']
    (destination / 'claims.json').write_text(json.dumps({'claims': claims, 'additional_discussion': discussion}, indent=2))
    (destination / 'diagnostics.json').write_text(json.dumps(diagnostics, indent=2))
    (destination / 'runtime.json').write_text(json.dumps({'wall_seconds': time.perf_counter() - started,
                                                        'peak_process_rss_mb': peak_memory(),
                                                        'memory_convention': 'max of parent and child process high-water RSS, not their sum'}, indent=2))
    plot_results(records, destination / 'figures')
    return records


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('request')
    parser.add_argument('destination')
    options = parser.parse_args()
    run(options.request, options.destination)
