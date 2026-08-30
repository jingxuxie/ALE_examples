import collections
import json
import math
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(os.environ['PARTICIPANT']) / 'workspace'))
from model import baseline_order, graph_arrays, improvement, metrics


def dfs_order(case, rng, mode):
    successors, predecessors, incoming, outgoing, _ = graph_arrays(case)
    count = len(case['nodes'])
    seen = [False] * count
    order = []
    ranks = [rng.random() for _ in range(count)]
    if mode == 1:
        ranks = [outgoing[node] - incoming[node] for node in range(count)]
    elif mode == 2:
        ranks = [-(outgoing[node] - incoming[node]) for node in range(count)]
    elif mode == 3:
        ranks = [incoming[node] for node in range(count)]
    elif mode == 4:
        ranks = [-incoming[node] for node in range(count)]

    def visit(node):
        if seen[node]:
            return
        seen[node] = True
        for predecessor in sorted(predecessors[node], key=lambda pred: ranks[pred]):
            visit(predecessor)
        order.append(node)

    for sink in sorted((node for node in range(count) if not successors[node]), key=lambda node: ranks[node]):
        visit(sink)
    return order


def score(record):
    return 0.7 * math.log(record['peak']) + 0.3 * math.log(record['qubit_time'])


def main():
    cases = json.loads(Path(os.environ['INPUT']).read_text())['cases']
    rng = random.Random(49231)
    schedules = {}
    families = collections.defaultdict(list)
    seeds = []
    for case in cases:
        baseline = baseline_order(case)
        before = metrics(case, baseline)
        best_order = baseline
        best = before
        candidates = [(score(before), baseline)]
        for trial in range(1000):
            order = dfs_order(case, rng, trial if trial < 5 else 0)
            result = metrics(case, order)
            if result['peak'] <= 1.05 * before['peak']:
                candidates.append((score(result), order))
                if score(result) < score(best):
                    best = result
                    best_order = order
        ratio = improvement(before, best)
        families[case['family']].append(math.log(ratio))
        schedules[case['id']] = best_order
        candidates.sort(key=lambda candidate: candidate[0])
        distinct = []
        seen = set()
        for _, order in candidates:
            identity = tuple(order)
            if identity not in seen:
                distinct.append(order)
                seen.add(identity)
            if len(distinct) >= 16:
                break
        seeds.append(distinct)
        print(case['id'], before, '=>', best, 'ratio', round(ratio, 4), flush=True)
    Path('schedules.json').write_text(json.dumps({'schedules': schedules}))
    with open('graphs.txt', 'w') as handle:
        print(len(cases), file=handle)
        for case, orders in zip(cases, seeds):
            before = metrics(case, baseline_order(case))
            print(case['id'], len(case['nodes']), len(case['edges']), before['peak'], before['qubit_time'], file=handle)
            for node in case['nodes']:
                print(node['duration'], node['workspace'], file=handle)
            for edge in case['edges']:
                print(*edge, file=handle)
            print(len(orders), file=handle)
            for order in orders:
                print(*order, file=handle)
    print('families', {family: math.exp(sum(values) / len(values)) for family, values in families.items()})
    values = sum(families.values(), [])
    print('core', math.exp(sum(values) / len(values)))


if __name__ == '__main__':
    main()
