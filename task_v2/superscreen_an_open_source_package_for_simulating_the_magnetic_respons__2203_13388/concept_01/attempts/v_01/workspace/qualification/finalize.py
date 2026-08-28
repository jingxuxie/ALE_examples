import argparse
import csv
import json
from pathlib import Path

from .cli import write_csv
from .visualize import figures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    rows = list(csv.DictReader((args.output / 'scaling.csv').open()))
    rows = [row for row in rows if row.get('run_kind', 'development_fresh_process')
            in ('development_cached', 'development_fresh_process')]
    for row in rows:
        row['run_kind'] = 'development_fresh_process'
        row['raw_file'] = f'raw/{row["configuration"]}/{row["case"]}.npz'
    for row in csv.DictReader((args.output / 'extended_scaling.csv').open()):
        row['run_kind'] = 'synthetic_cached'
        row['raw_file'] = f'raw/{row["configuration"]}/{row["case"]}.npz'
        rows.append(row)
    cold_path = args.output / 'raw' / 'qualified' / 'cold_dev_ring.metrics.json'
    cold = json.loads(cold_path.read_text())
    cold['run_kind'] = 'relocated_cold'
    cold['raw_file'] = 'raw/qualified/cold_dev_ring.npz'
    rows.append(cold)
    write_csv(args.output / 'scaling.csv', rows)
    figures(args.output)


if __name__ == '__main__':
    main()
