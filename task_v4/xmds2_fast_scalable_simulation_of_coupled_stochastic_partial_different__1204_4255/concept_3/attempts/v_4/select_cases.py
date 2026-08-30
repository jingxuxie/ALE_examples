import argparse
import json

from optimize import OUT, PROTOCOL, PUBLIC


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('report')
    parser.add_argument('--output', default='active_cases.json')
    parser.add_argument('--groups', type=int, default=20)
    args = parser.parse_args()
    rows = json.loads((OUT / args.report).read_text())
    rows.sort(key=lambda row: row['fidelity'])
    chosen = PUBLIC.copy()
    groups = set()
    for row in rows:
        case = row['case']
        group = tuple(case[key] for key in ('g', 'self_ratio', 'trap_x', 'bias', 'gradient'))
        if group not in groups:
            groups.add(group)
            chosen.append(case)
        if len(groups) >= args.groups:
            break
    boundary_rows = sorted(rows, key=lambda row: row['audit']['boundary_mass'], reverse=True)
    chosen.extend(row['case'] for row in boundary_rows[:3])
    unique = {tuple(case[key] for key in PROTOCOL['uncertainty']): case for case in chosen}
    (OUT / args.output).write_text(json.dumps(list(unique.values()), indent=2) + '\n')
    print('active cases', len(unique))


if __name__ == '__main__':
    main()
