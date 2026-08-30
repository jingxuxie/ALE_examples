import json
from pathlib import Path

from common import CASES, verify
from reorder import optimize


def metrics(case, gates):
    report = verify(case, gates)
    return max(report['count'] / case['max_cnots'], report['depth'] / case['max_depth']) + 0.00001 * report['count']


def cross(case):
    circuits = []
    for source in Path('.').glob('*_' + case['id'] + '.txt'):
        try:
            gates = [tuple(map(int, line.split())) for line in source.read_text().splitlines()]
            report = verify(case, gates)
        except Exception:
            continue
        if report['exact'] and not report['missing']:
            circuits.append(gates)
    record = min(metrics(case, gates) for gates in circuits)
    for iteration in range(10):
        groups = {}
        prepared = []
        parity_bits = {mask: 1 << index for index, mask in enumerate(case['required_parities'])}
        complete = (1 << len(parity_bits)) - 1
        for circuit_index, gates in enumerate(circuits):
            rows = [1 << wire for wire in range(case['n'])]
            rows_history = [tuple(rows)]
            prefix_clocks = [[0] * case['n']]
            prefix_visits = [sum(parity_bits.get(mask, 0) for mask in rows)]
            for control, target in gates:
                rows[target] ^= rows[control]
                rows_history.append(tuple(rows))
                clocks = prefix_clocks[-1][:]
                clocks[control] = clocks[target] = 1 + max(clocks[control], clocks[target])
                prefix_clocks.append(clocks)
                prefix_visits.append(prefix_visits[-1] | parity_bits.get(rows[target], 0))
            suffix_clocks = [[0] * case['n'] for _ in range(len(gates) + 1)]
            suffix_visits = [0] * (len(gates) + 1)
            suffix_visits[-1] = sum(parity_bits.get(mask, 0) for mask in rows)
            for index in reversed(range(len(gates))):
                control, target = gates[index]
                clocks = suffix_clocks[index + 1][:]
                clocks[control] = clocks[target] = 1 + max(clocks[control], clocks[target])
                suffix_clocks[index] = clocks
                suffix_visits[index] = suffix_visits[index + 1] | parity_bits.get(rows_history[index][target], 0)
            prepared.append((prefix_clocks, prefix_visits, suffix_clocks, suffix_visits))
            for index, basis in enumerate(rows_history):
                groups.setdefault(basis, []).append((circuit_index, index))
        improvements = []
        for endpoints in groups.values():
            for first_circuit, first_index in endpoints:
                front_clock, front_visits, _, _ = prepared[first_circuit]
                for last_circuit, last_index in endpoints:
                    if first_circuit == last_circuit:
                        continue
                    _, _, back_clock, back_visits = prepared[last_circuit]
                    if front_visits[first_index] | back_visits[last_index] != complete:
                        continue
                    count = first_index + len(circuits[last_circuit]) - last_index
                    depth = max(first + last for first, last in zip(front_clock[first_index], back_clock[last_index]))
                    score = max(count / case['max_cnots'], depth / case['max_depth']) + 0.00001 * count
                    if score >= record:
                        continue
                    candidate = circuits[first_circuit][:first_index] + circuits[last_circuit][last_index:]
                    candidate = optimize(case, candidate, 5)
                    report = verify(case, candidate)
                    assert report['exact'] and not report['missing']
                    score = metrics(case, candidate)
                    if score < record:
                        record = score
                        improvements.append(candidate)
                        Path('cross_' + case['id'] + '.txt').write_text(''.join(f'{control} {target}\n' for control, target in candidate))
                        print(case['id'], iteration, report['count'], report['depth'], flush=True)
        if not improvements:
            break
        circuits.extend(improvements)


if __name__ == '__main__':
    for case in CASES:
        cross(case)
