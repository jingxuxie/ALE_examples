import argparse
import csv
import json
from pathlib import Path
import resource
import time

from solver import solve
from plotting import plot_results


FIELDS = ['row_id', 'case', 'family', 'method', 'cutoff', 'sector', 'level',
          'energy', 'gap', 'dimension', 'elapsed_s']


def write_csv(path, records, fields):
    with Path(path).open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def run(request_path, destination, methods=None):
    request_path = Path(request_path).resolve()
    request = json.loads(request_path.read_text())
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    root = Path(request['archive_root'])
    if not root.is_absolute():
        root = request_path.parent / root
    records, scaling = [], []
    methods = methods or ['production', 'raw', 'scalar_twice']
    for case in request['cases']:
        for cutoff in case['cutoffs']:
            for method in methods:
                result = solve(case, root / case['archive'], cutoff, method)
                vacuum = min(values[0] for values in result['levels'].values())
                scaling.append({'case': case['id'], 'method': method, 'cutoff': cutoff,
                                'dimension': result['dimension'], 'elapsed_s': result['seconds'],
                                'peak_rss_mb': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024})
                for sector, values in result['levels'].items():
                    for level, energy in enumerate(values):
                        row_id = f"{case['id']}:{method}:{cutoff:g}:{sector}:{level}"
                        records.append({'row_id': row_id, 'case': case['id'], 'family': case['family'],
                                        'method': method, 'cutoff': cutoff, 'sector': sector, 'level': level,
                                        'energy': energy, 'gap': energy - vacuum,
                                        'dimension': result['dimension'], 'elapsed_s': result['seconds']})
    production = [row for row in records if row['method'] == 'production']
    ablation = [row for row in records if row['method'] != 'production']
    write_csv(destination / 'results.csv', production, FIELDS)
    write_csv(destination / 'ablation.csv', ablation, FIELDS)
    write_csv(destination / 'scaling.csv', scaling,
              ['case', 'method', 'cutoff', 'dimension', 'elapsed_s', 'peak_rss_mb'])
    claims = []
    for case in request['cases']:
        cutoffs = sorted(case['cutoffs'])
        if len(cutoffs) < 2:
            continue
        sector = case['sectors'][-1]['name']
        selected_level = 1 if sector == 'mixed' else 0
        selected = [next(row for row in records if row['case'] == case['id']
                         and row['sector'] == sector and row['level'] == selected_level
                         and row['cutoff'] == cutoff and row['method'] == method)
                    for method in ['production', 'raw'] for cutoff in [cutoffs[-2], cutoffs[-1]]]
        ratio = abs(selected[1]['gap'] - selected[0]['gap']) / max(abs(selected[3]['gap'] - selected[2]['gap']), 1e-12)
        claims.append({'id': case['id'] + '_drift', 'kind': 'cutoff_drift_ratio',
                       'statement': 'Cutoff drift comparison for the lowest level in the selected sector.',
                       'rows': [row['row_id'] for row in selected], 'quantity': 'gap',
                       'value': ratio, 'conclusion': 'improved' if ratio < 1 else 'not_improved'})
    (destination / 'claims.json').write_text(json.dumps({'claims': claims}, indent=2))
    plot_results(records, destination / 'figures')
    return records


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('request')
    parser.add_argument('destination')
    options = parser.parse_args()
    run(options.request, options.destination)
