import argparse
from pathlib import Path

from common import CASES, verify
from reorder import optimize


def bridge(case):
    corpus = []
    for source in Path('.').glob('*_' + case['id'] + '.txt'):
        try:
            gates = [tuple(map(int, line.split())) for line in source.read_text().splitlines()]
            report = verify(case, gates)
        except Exception:
            continue
        if report['exact'] and not report['missing']:
            corpus.append((gates, report))
    best = min(corpus, key=lambda item: (item[1]['depth'], item[1]['count']))[1]
    record = (best['depth'], best['count'])
    directed = [tuple(edge) for edge in case['edges']] + [tuple(reversed(edge)) for edge in case['edges']]
    parity_bits = {mask: 1 << index for index, mask in enumerate(case['required_parities'])}
    complete = (1 << len(parity_bits)) - 1
    all_states = []
    for gates, report in corpus:
        rows = [1 << wire for wire in range(case['n'])]
        basis = [tuple(rows)]
        front_clocks = [[0] * case['n']]
        front_visits = [sum(parity_bits.get(row, 0) for row in rows)]
        for control, target in gates:
            rows[target] ^= rows[control]
            basis.append(tuple(rows))
            clocks = front_clocks[-1][:]
            clocks[control] = clocks[target] = 1 + max(clocks[control], clocks[target])
            front_clocks.append(clocks)
            front_visits.append(front_visits[-1] | parity_bits.get(rows[target], 0))
        clocks = [0] * case['n']
        visits = sum(parity_bits.get(row, 0) for row in rows)
        back_clocks = [None] * (len(gates) + 1)
        back_visits = [None] * (len(gates) + 1)
        for index in reversed(range(len(gates) + 1)):
            if index < len(gates):
                control, target = gates[index]
                clocks = clocks[:]
                clocks[control] = clocks[target] = 1 + max(clocks[control], clocks[target])
                visits |= parity_bits.get(basis[index][target], 0)
            back_clocks[index] = clocks
            back_visits[index] = visits
        for index, state in enumerate(basis):
            all_states.append((state, gates, index, front_clocks[index], front_visits[index], back_clocks[index], back_visits[index]))
    neighbors = {}
    for state_index, (basis, gates, index, front_clock, front_visit, back_clock, back_visit) in enumerate(all_states):
        if max(back_clock) >= record[0]:
            continue
        for direction, (control, target) in enumerate(directed):
            changed = list(basis)
            changed[target] ^= changed[control]
            neighbors.setdefault(tuple(changed), []).append((state_index, direction))
        neighbors.setdefault(basis, []).append((state_index, -1))
    print(case['id'], 'states', len(all_states), 'neighbors', len(neighbors), flush=True)
    for state_index, (basis, gates, index, front_clock, front_visit, _, _) in enumerate(all_states):
        if max(front_clock) >= record[0]:
            continue
        for first_direction in range(-1, len(directed)):
            changed = list(basis)
            first_clocks = front_clock[:]
            visits = front_visit
            prefix_gates = []
            if first_direction >= 0:
                control, target = directed[first_direction]
                changed[target] ^= changed[control]
                visits |= parity_bits.get(changed[target], 0)
                first_clocks[control] = first_clocks[target] = 1 + max(first_clocks[control], first_clocks[target])
                prefix_gates.append((control, target))
            for other_index, second_direction in neighbors.get(tuple(changed), []):
                _, other_gates, other_position, _, _, back_clock, back_visit = all_states[other_index]
                if visits | back_visit != complete:
                    continue
                clocks = first_clocks[:]
                middle = prefix_gates[:]
                if second_direction >= 0:
                    control, target = directed[second_direction]
                    clocks[control] = clocks[target] = 1 + max(clocks[control], clocks[target])
                    middle.append((control, target))
                count = index + len(middle) + len(other_gates) - other_position
                depth = max(first + last for first, last in zip(clocks, back_clock))
                if (depth, count) >= record:
                    continue
                candidate = gates[:index] + middle + other_gates[other_position:]
                candidate = optimize(case, candidate, 10)
                report = verify(case, candidate)
                assert report['exact'] and not report['missing']
                if (report['depth'], report['count']) < record:
                    record = (report['depth'], report['count'])
                    Path('bridge_' + case['id'] + '.txt').write_text(''.join(f'{control} {target}\n' for control, target in candidate))
                    print(case['id'], 'count', report['count'], 'depth', report['depth'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('case', type=int)
    args = parser.parse_args()
    bridge(CASES[args.case])
