import argparse
import csv
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

import numpy as np

from .backend import solve, CONFIGURATIONS, DEFAULT_CONFIGURATION, AVAILABLE_CONFIGURATIONS
from .model import load_case, summarize


def write_csv(path, rows):
    with Path(path).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def one_case(case_path, output_path, configuration):
    case = load_case(case_path)
    start = time.perf_counter()
    result = solve(case, config=configuration)
    elapsed = time.perf_counter() - start
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output_path, **result)
    metrics = {'case': case.meta['id'], 'configuration': configuration,
               'seconds': elapsed, 'max_rss_mib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
               'vertices': len(case.points), 'triangles': len(case.triangles), 'drives': len(case.drive_H)}
    for phase in ('warmup', 'setup', 'solve', 'readout'):
        metrics[f'{phase}_seconds'] = float(result.get(f'timing_{phase}', np.nan))
    output_path.with_suffix('.metrics.json').write_text(json.dumps(metrics, indent=2))
    rows = [{**row, 'configuration': configuration} for row in summarize(case, result)]
    return rows, metrics


def suite(suite_path, output_path):
    suite_path, output_path = Path(suite_path), Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    paths = [suite_path.parent / filename for filename in json.loads(suite_path.read_text())['cases']]
    results, scaling = [], []
    for configuration in CONFIGURATIONS:
        for case_path in paths:
            raw_path = output_path / 'raw' / configuration / case_path.name
            start = time.perf_counter()
            subprocess.run([sys.executable, '-m', 'qualification.cli', 'case', str(case_path),
                            str(raw_path), '--config', configuration], check=True)
            metrics = json.loads(raw_path.with_suffix('.metrics.json').read_text())
            metrics['process_wall_seconds'] = time.perf_counter() - start
            raw_path.with_suffix('.metrics.json').write_text(json.dumps(metrics, indent=2))
            case = load_case(case_path)
            with np.load(raw_path) as archive:
                rows = [{**row, 'configuration': configuration} for row in summarize(case, dict(archive))]
            results.extend(rows)
            scaling.append(metrics)
            print(case_path.stem, configuration, round(metrics['seconds'], 3), flush=True)
    from .evidence import augment, claims
    results = augment(paths, output_path, results)
    write_csv(output_path / 'results.csv', [row for row in results if row['configuration'] == DEFAULT_CONFIGURATION])
    write_csv(output_path / 'ablation.csv', results)
    write_csv(output_path / 'scaling.csv', scaling)
    claims(output_path, results)
    from .visualize import figures
    figures(output_path)


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)
    case_parser = subparsers.add_parser('case')
    case_parser.add_argument('case')
    case_parser.add_argument('output')
    case_parser.add_argument('--config', choices=AVAILABLE_CONFIGURATIONS, default=DEFAULT_CONFIGURATION)
    suite_parser = subparsers.add_parser('suite')
    suite_parser.add_argument('suite')
    suite_parser.add_argument('output')
    args = parser.parse_args()
    if args.command == 'case':
        one_case(args.case, args.output, args.config)
    else:
        suite(args.suite, args.output)


if __name__ == '__main__':
    main()
