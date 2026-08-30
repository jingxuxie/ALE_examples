import argparse
import random
from pathlib import Path

from common import CASES, verify
from reorder import commute, optimize


def relocate(case, source, rounds):
    gates = [tuple(map(int, line.split())) for line in Path(source + case['id'] + '.txt').read_text().splitlines()]
    neighbors = [[] for _ in range(case['n'])]
    directed = []
    for first, second in case['edges']:
        neighbors[first].append(second)
        neighbors[second].append(first)
        directed.extend(((first, second), (second, first)))
    rng = random.Random(711)
    record = verify(case, gates)
    best = gates
    for iteration in range(rounds):
        candidates = []
        for first, gate in enumerate(gates):
            for second in range(first + 1, len(gates)):
                if gates[second] == gate:
                    reduced = gates[:first] + gates[first + 1:second] + gates[second + 1:]
                    report = verify(case, reduced)
                    if len(report['missing']) == 1:
                        candidates.append((reduced, report['missing'][0]))
                    elif not report['missing']:
                        candidates.append((reduced, 0))
                    break
                if not commute(gate, gates[second]):
                    break
        rng.shuffle(candidates)
        choices = []
        for reduced, missing in candidates:
            if not missing:
                choices.append(reduced)
                continue
            suffix = [[0] * case['n'] for _ in range(len(reduced) + 1)]
            for index in reversed(range(len(reduced))):
                control, target = reduced[index]
                clocks = suffix[index + 1][:]
                clocks[control] = clocks[target] = 1 + max(clocks[control], clocks[target])
                suffix[index] = clocks
            rows = [1 << wire for wire in range(case['n'])]
            prefix = [0] * case['n']
            placements = []
            for index in range(len(reduced) + 1):
                for control, target in directed:
                    value = rows[control] ^ rows[target]
                    computes = []
                    if value == missing:
                        computes.append([(control, target)])
                    for neighbor in neighbors[target]:
                        if neighbor != control and value ^ rows[neighbor] == missing:
                            computes.append([(control, target), (target, neighbor)])
                            computes.append([(control, target), (neighbor, target)])
                    for compute in computes:
                        loop = compute + compute[::-1]
                        clocks = prefix[:]
                        for first_wire, second_wire in loop:
                            clocks[first_wire] = clocks[second_wire] = 1 + max(clocks[first_wire], clocks[second_wire])
                        depth = max(first_clock + last_clock for first_clock, last_clock in zip(clocks, suffix[index]))
                        count = len(reduced) + len(loop)
                        if depth <= record['depth'] + 1 and count <= case['max_cnots']:
                            placements.append((depth, count, rng.random(), index, loop))
                if index < len(reduced):
                    control, target = reduced[index]
                    rows[target] ^= rows[control]
                    prefix[control] = prefix[target] = 1 + max(prefix[control], prefix[target])
            for depth, count, noise, index, loop in sorted(placements)[:8]:
                choices.append(reduced[:index] + loop + reduced[index:])
        rng.shuffle(choices)
        updated = False
        for candidate in choices:
            report = verify(case, candidate)
            assert report['exact'] and not report['missing']
            if report['depth'] <= record['depth']:
                candidate = optimize(case, candidate, 4)
                report = verify(case, candidate)
                if (report['depth'], report['count']) < (record['depth'], record['count']):
                    record = report
                    best = candidate
                    print(case['id'], iteration, report['count'], report['depth'], flush=True)
                    Path('relocated_' + case['id'] + '.txt').write_text(''.join(f'{control} {target}\n' for control, target in best))
                if report['depth'] <= record['depth'] and report['count'] <= record['count'] + 8 and rng.random() < 0.2:
                    gates = candidate
                    updated = True
        if not updated or iteration % 5 == 0:
            gates = best
        if not candidates:
            break
    Path('relocated_' + case['id'] + '.txt').write_text(''.join(f'{control} {target}\n' for control, target in best))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('case', type=int)
    parser.add_argument('--source', default='hot_')
    parser.add_argument('--rounds', type=int, default=100)
    args = parser.parse_args()
    relocate(CASES[args.case], args.source, args.rounds)
