import argparse
import csv
import json
from pathlib import Path
import numpy as np
from legacy_transport.model import load_suite
from legacy_transport.simulate import simulate


def summarize(case, result, metadata, config):
    density = result['density']
    current = result['current']
    times = result['times']
    return dict(row_id=case['id'] + ':' + config, case=case['id'], family=case['family'], config=config,
                initial_charge=float(np.sum(density[0])), final_charge=float(np.sum(density[-1])),
                peak_current=float(np.max(abs(current))) if current.size else 0.,
                transported_charge=float(np.trapz(current[:, 0], times)) if current.size else 0.,
                max_density_change=float(np.max(abs(density - density[0]))),
                runtime_s=metadata['seconds'], peak_rss_mb=metadata['peak_rss_mb'])


def run_suite(cases_path, output_path, config):
    output = Path(output_path)
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for case in load_suite(cases_path):
        result, metadata = simulate(case, config)
        np.savez_compressed(output / (case['id'] + '.npz'), **result)
        (output / (case['id'] + '.json')).write_text(json.dumps(metadata, indent=2))
        row = summarize(case, result, metadata, config)
        rows.append(row)
        print(json.dumps(row), flush=True)
    with open(output / 'results.csv', 'w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cases', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--config', default='production')
    args = parser.parse_args()
    run_suite(args.cases, args.output, args.config)


if __name__ == '__main__':
    main()
