import argparse
import json
import math
import random
from collections import Counter
from pathlib import Path

from graph import Graph
from run_portfolio import run
from schedule import baseline_module
from solve import validate


def assemble(records, occupied, virtual, cap_factor):
    tensors = {}
    for record in records:
        tensors.update(record['tensors'])
    case = {'dimensions': {'o': occupied, 'v': virtual}, 'tensors': tensors,
            'index_types': {axis: 'o' if axis in 'ijklmn' else 'v' for axis in 'abcdefghijklmn'},
            'terms': [record['term'] for record in records], 'memory_cap': 10**30}
    baseline = baseline_module()
    peak = max(baseline.term_frontier(case, term)[0][1] for term in case['terms'])
    case['memory_cap'] = math.ceil(peak * cap_factor)
    metrics = validate(case, baseline.solve(case))
    return case, metrics


def choose(records, occupied, virtual, count, mode, seed):
    rng = random.Random(seed)
    if mode == 'random':
        return rng.sample(records, min(count, len(records)))
    pool, baseline = assemble(records, occupied, virtual, 1.1)
    graph = Graph(pool)
    active = [graph.reachable(graph.base_choices, [root[0]]) for root in graph.roots]
    frequency = Counter(node_id for nodes in active for node_id in nodes)
    chosen = []
    available = set(range(len(records)))
    retained = set()
    while available and len(chosen) < min(count, len(records)):
        scores = {}
        for index in available:
            shared = sum(graph.edges[graph.base_choices[node_id]].cost for node_id in active[index] & retained)
            potential = sum(graph.edges[graph.base_choices[node_id]].cost * (frequency[node_id] - 1) for node_id in active[index])
            cost = graph.minimum[graph.roots[index][0]]
            scores[index] = (shared + 0.1 * potential) / max(1, cost) + rng.random() * 1e-9
        index = max(available, key=lambda index: scores[index])
        chosen.append(index)
        available.remove(index)
        retained |= active[index]
    rng.shuffle(chosen)
    return [records[index] for index in chosen]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('challenge'))
    parser.add_argument('--seconds', type=float, default=15)
    parser.add_argument('--trials', type=int, default=8)
    args = parser.parse_args()
    source_path = Path(__file__).resolve().parents[2] / 'evaluator/hidden/source_terms.json'
    sources = json.loads(source_path.read_text())
    hidden = args.output / 'cases'
    hidden.mkdir(parents=True, exist_ok=True)
    presets = [(4, 12, 20, 1.05), (20, 12, 48, 1.10), (4, 112, 80, 1.20), (16, 16, 32, 1.50)]
    entries = []
    provenance = {}
    for family, records in sources.items():
        for preset, (occupied, virtual, count, cap_factor) in enumerate(presets):
            for mode in ('random', 'reuse_rich'):
                seed = 98216606850 + preset * 101 + len(entries)
                selected = choose(records, occupied, virtual, count, mode, seed)
                case, baseline = assemble(selected, occupied, virtual, cap_factor)
                name = family + '_' + str(preset) + '_' + mode + '.json'
                (hidden / name).write_text(json.dumps(case))
                entries.append({'file': name, 'family': family, 'baseline': baseline})
                provenance[name] = {'selection': mode, 'seed': seed, 'cap_factor': cap_factor,
                                    'source_records': [{key: value for key, value in record.items() if key not in {'term', 'tensors'}} for record in selected]}
    manifest = {'target_geomean_speedup': 1.75, 'target_worst_family_speedup': 1.15,
                'cases': entries, 'classification': 'private diagnostic source-family challenges, not hidden evaluation replacements'}
    (hidden / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (args.output / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    run(hidden, args.output / 'results', args.seconds, args.trials, seed=127, delayed=True)


if __name__ == '__main__':
    main()
