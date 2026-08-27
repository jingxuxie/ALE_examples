import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'private' / 'engine'))

from archive import write_archive
from solver import solve


def cases(group):
    hidden = group == 'hidden'
    common = {'mass': 1.0, 'boundary': 'periodic', 'cutoffs': [10.0, 12.0, 14.0, 16.0],
              'sectors': [{'name': 'even', 'momentum': 0, 'parity': 0},
                          {'name': 'odd', 'momentum': 0, 'parity': 1}]}
    specifications = [
        dict(id='quadratic', family='quadratic', length=4.7 if hidden else 4.0,
             couplings=[{'degree': 2, 'value': 1.1 if hidden else 0.65}]),
        dict(id='periodic', family='periodic', length=5.3 if hidden else 5.0,
             couplings=[{'degree': 4, 'value': 1.7 if hidden else 1.2}]),
        dict(id='twisted', family='antiperiodic', boundary='antiperiodic',
             length=4.6 if hidden else 4.0,
             couplings=[{'degree': 4, 'value': 1.9 if hidden else 1.4}],
             sectors=[{'name': 'even', 'momentum': 0, 'parity': 0},
                      {'name': 'odd', 'momentum': 1, 'parity': 1}]),
        dict(id='biased', family='source_broken', length=3.7 if hidden else 3.5,
             couplings=[{'degree': 4, 'value': 1.5 if hidden else 1.2},
                        {'degree': 3, 'value': 0.55 if hidden else -0.4},
                        {'degree': 1, 'value': -0.22 if hidden else 0.18}],
             sectors=[{'name': 'mixed', 'momentum': 0, 'parity': None}]),
        dict(id='modulated', family='inhomogeneous', length=2.9 if hidden else 2.5,
             couplings=[{'degree': 4, 'value': 1.3 if hidden else 1.0},
                        {'degree': 4, 'transfer': 2, 'value': 0.24 if hidden else 0.18},
                        {'degree': 4, 'transfer': -2, 'value': 0.24 if hidden else 0.18},
                        {'degree': 2, 'transfer': 2, 'value': -0.15 if hidden else 0.12},
                        {'degree': 2, 'transfer': -2, 'value': -0.15 if hidden else 0.12}],
             operator_transfers=[-4, -2, 0, 2, 4],
             sectors=[{'name': 'even', 'momentum': None, 'parity': 0},
                      {'name': 'odd', 'momentum': None, 'parity': 1}]),
    ]
    return [dict(common, **specification) for specification in specifications]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--group', choices=['public', 'hidden'], default='public')
    parser.add_argument('--cutoff', type=float, default=24.0)
    parser.add_argument('--only', default='')
    arguments = parser.parse_args()
    folder = ROOT / 'private' / 'generated' / arguments.group
    folder.mkdir(parents=True, exist_ok=True)
    selected = cases(arguments.group)
    (folder / 'cases.json').write_text(json.dumps(selected, indent=2))
    for case in selected:
        if arguments.only and case['id'] not in arguments.only.split(','):
            continue
        archive = folder / f"{case['id']}_{int(arguments.cutoff)}"
        if not (archive / 'manifest.json').exists():
            write_archive(archive, case, arguments.cutoff)
        records = []
        for cutoff in sorted(set(case['cutoffs'] + [arguments.cutoff - 2, arguments.cutoff])):
            if cutoff > arguments.cutoff:
                continue
            for method in ['raw', 'local', 'improved']:
                record = solve(case, archive, cutoff, method)
                records.append(record)
                print(case['id'], cutoff, method, record['levels'], round(record['seconds'], 3), flush=True)
        (folder / f"{case['id']}_{int(arguments.cutoff)}_scan.json").write_text(json.dumps(records, indent=2))


if __name__ == '__main__':
    main()
