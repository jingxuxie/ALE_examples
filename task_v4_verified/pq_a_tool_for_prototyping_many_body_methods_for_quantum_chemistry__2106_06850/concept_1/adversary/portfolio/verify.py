import argparse
import json
import math
import os
import random
import resource
import subprocess
import sys
import time
from pathlib import Path

from certificate import integer_lower_bound
from graph import Graph
from optimize import feasible_edges
from schedule import Scheduler
from solve import baseline_module, validate


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (31, 31))


def audit_edge(graph, edge_id):
    edge = graph.edges[edge_id]
    parent = graph.nodes[edge.parent]
    alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    inputs = [[name, ''.join(alphabet[index] for index in labels)] for name, labels in parent.key[1]]
    types = {}
    for name, axes in inputs:
        types.update(zip(axes, graph.case['tensors'][name]))
    output = alphabet[:parent.rank]
    case = {'dimensions': graph.case['dimensions'], 'tensors': graph.case['tensors'], 'index_types': types,
            'terms': [{'inputs': inputs, 'output': output}], 'memory_cap': 10**100}
    choices = dict(graph.base_choices)
    choices[edge.parent] = edge_id
    steps = []
    live = {}

    def build(node_id):
        node = graph.nodes[node_id]
        if node.tensor:
            return node.tensor
        if node_id in live:
            return live[node_id]
        operation = graph.edges[choices[node_id]]
        references = [[build(child), axes] for child, axes in zip(operation.children, operation.inputs)]
        name = 'audit_' + str(len(live))
        steps.append({'id': name, 'inputs': references, 'output': operation.output})
        live[node_id] = name
        return name

    name = build(edge.parent)
    steps.append({'emit': 0, 'input': [name, output], 'output': output})
    return validate(case, {'steps': steps})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', type=Path, default=Path('expanded'))
    parser.add_argument('--output', type=Path, default=Path('verification'))
    parser.add_argument('--runtime', action='store_true')
    parser.add_argument('--fallback', action='store_true')
    parser.add_argument('--edge-samples', type=int, default=200)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[2]
    hidden = root / 'evaluator/hidden'
    manifest = json.loads((hidden / 'manifest.json').read_text())
    records = []
    started = time.monotonic()
    for entry in manifest['cases']:
        name = Path(entry['file']).stem
        case = json.loads((hidden / entry['file']).read_text())
        record = {'file': entry['file'], 'baseline_flops': entry['baseline']['flops']}
        plan = json.loads((args.results / (name + '.plan.json')).read_text())
        record['result'] = validate(case, plan)
        baseline = baseline_module()
        record['recomputed_baseline'] = validate(case, baseline.solve(case))
        if record['recomputed_baseline']['flops'] != entry['baseline']['flops']:
            raise ValueError('frozen baseline cost changed')
        certificate = json.loads((args.results / (name + '.bound.json')).read_text())
        graph = Graph(case, delayed=certificate['delayed_summation'])
        record['verified_integer_lower_flops'] = integer_lower_bound(graph, feasible_edges(graph), certificate)
        record['verified_graph_upper_speedup'] = entry['baseline']['flops'] / record['verified_integer_lower_flops']
        for root_node, axes, output in graph.roots:
            if graph.minimum[root_node] < 0:
                raise ValueError('invalid independent tree cost')
        if graph.statistics()['independent_minimum'] != entry['baseline']['flops']:
            raise ValueError('enumerated tree optimum disagrees with exact baseline')
        possible = [edge_id for edge_id, edge in enumerate(graph.edges) if all(graph.minimum[child] < math.inf for child in edge.children)]
        chosen = random.Random(210606850).sample(possible, min(args.edge_samples, len(possible)))
        for edge_id in chosen:
            audit_edge(graph, edge_id)
        record['semantically_checked_edges'] = len(chosen)
        if args.fallback:
            ordinary = Graph(case)
            forced = dict(ordinary.base_choices)
            for node_id, node in enumerate(ordinary.nodes):
                if node.edges:
                    forced[node_id] = max(node.edges, key=lambda edge_id: sum(ordinary.nodes[child].size for child in ordinary.edges[edge_id].children))
            fallback_plan, fallback_stats = Scheduler(ordinary, forced, list(range(len(ordinary.roots)))).run()
            record['forced_memory_fallback'] = {'result': validate(case, fallback_plan), **fallback_stats}
        if args.runtime:
            output = args.output / (name + '.runtime.plan.json')
            report = args.output / (name + '.runtime.search.json')
            command = [sys.executable, str(Path(__file__).resolve().parent / 'solve.py'), str(hidden / entry['file']),
                       str(output), '--seconds', '20', '--trials', '8', '--delayed', '--report', str(report)]
            environment = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
            wall_started = time.monotonic()
            try:
                process = subprocess.run(command, capture_output=True, text=True, timeout=30, preexec_fn=limits, env=environment)
                wall_seconds = time.monotonic() - wall_started
                if process.returncode:
                    raise ValueError(process.stderr[-4000:])
                result = validate(case, json.loads(output.read_text()))
                record['cold_runtime'] = {'wall_seconds': wall_seconds, 'result': result,
                                           'speedup': entry['baseline']['flops'] / result['flops'],
                                           'address_space_bytes': 2 * 1024**3, 'timeout_seconds': 30,
                                           'threads': 1, 'isolation': 'resource-limited local subprocess, not evaluator bubblewrap'}
            except Exception as error:
                record['cold_runtime'] = {'valid': False, 'reason': str(error), 'wall_seconds': time.monotonic() - wall_started}
        records.append(record)
        print(name, 'valid', record['result']['valid'], 'certified_bound', record['verified_integer_lower_flops'],
              'edges_checked', record['semantically_checked_edges'], 'runtime', record.get('cold_runtime', {}).get('wall_seconds'), flush=True)
        (args.output / 'summary.json').write_text(json.dumps({'cases': records, 'elapsed_seconds': time.monotonic() - started}, indent=2) + '\n')


if __name__ == '__main__':
    main()
