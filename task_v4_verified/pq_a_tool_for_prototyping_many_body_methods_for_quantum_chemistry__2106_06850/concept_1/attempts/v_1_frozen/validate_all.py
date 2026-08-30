import json
import math
import os
import random
import resource
import subprocess
import sys
import time
from pathlib import Path

from bench import PARTICIPANT, baseline, expanded, validate
from model import Graph
from solve import Planner, compact, solve
from stress import chain_case, mutated, random_case


def edge_cases():
    square = {'dimensions': {'o': 4}, 'tensors': {'A': ['o', 'o'], 'B': ['o', 'o']},
              'index_types': {axis: 'o' for axis in 'ijkl'}, 'memory_cap': 2,
              'terms': [{'inputs': [['A', 'ij'], ['B', 'ji'], ['A', 'kl'], ['B', 'lk']], 'output': ''}]}
    chain_square = {'dimensions': {'o': 4}, 'tensors': {name: ['o', 'o'] for name in 'ABC'},
                    'index_types': {axis: 'o' for axis in 'ijklmn'}, 'memory_cap': 32,
                    'terms': [{'inputs': [['A', 'ij'], ['B', 'jk'], ['C', 'kl'], ['A', 'lm'], ['B', 'mn'], ['C', 'ni']], 'output': ''}]}
    scalars = {'dimensions': {'o': 4}, 'tensors': {'': [], '_p0': [], 's2': []}, 'index_types': {},
               'memory_cap': 2, 'terms': [{'inputs': [['', ''], ['_p0', ''], ['s2', '']], 'output': ''}]}
    reduction = {'dimensions': {'particles': 12, 'holes': 4},
                 'tensors': {' ': ['particles'], '2': ['holes'], '_p0': []},
                 'index_types': {'α': 'particles', 'β': 'holes'}, 'memory_cap': 2,
                 'terms': [{'inputs': [[' ', 'α'], ['2', 'β'], ['_p0', '']], 'output': ''}]}
    elementwise = {'dimensions': {'o': 4, 'v': 12},
                   'tensors': {'a': ['v'], 'b': ['v'], 'c': ['o']},
                   'index_types': {'x': 'v', 'i': 'o'}, 'memory_cap': 60,
                   'terms': [{'inputs': [['a', 'x'], ['b', 'x'], ['c', 'i']], 'output': 'xi'},
                             {'inputs': [['c', 'i'], ['b', 'x'], ['a', 'x']], 'output': 'ix'}]}
    repeated_cache = {'dimensions': {'o': 4, 'v': 12},
                      'tensors': {'A': ['o', 'v'], 'B': ['v', 'v'], 'C': ['v', 'o'], 'D': ['v', 'o']},
                      'index_types': {axis: 'o' if axis in 'ijkl' else 'v' for axis in 'ijklabcd'},
                      'memory_cap': 288,
                      'terms': [{'inputs': [['A', 'ia'], ['B', 'ab'], ['D', 'bj']], 'output': 'ij'},
                                {'inputs': [['A', 'ia'], ['B', 'ab'], ['C', 'bj'], ['A', 'kc'], ['B', 'cd'], ['C', 'dl']],
                                 'output': 'ijkl'}]}
    return [('square', square), ('chain_square', chain_square), ('scalars', scalars),
            ('reduction', reduction), ('elementwise', elementwise), ('repeated_cache', repeated_cache)]


def direct_tests():
    count = 0
    for label, case in edge_cases():
        plan = solve(case)
        result = validate(case, plan)
        print('edge', label, result, flush=True)
        count += 1
    for seed in range(18):
        factors = 3 + seed % 4
        case = random_case(1471 + seed, 20 + seed % 3 * 10, factors)
        graph = Graph(case)
        basecost = validate(case, baseline.solve(case))['flops']
        for release in (False, True):
            for exponent, ordering in ((0, 0), (1, 0), (0.5, 1)):
                planner = Planner(graph, exponent, ordering, release=release)
                plan = planner.solve()
                plan, peak = compact(case, plan)
                result = validate(case, plan)
                assert result['flops'] == planner.work
                assert result['peak_elements'] == peak
                count += 1
        print('random', seed, factors, len(graph.nodes), 'validated', count, flush=True)
    return count


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (29, 29))


def cli_tests():
    directory = Path('experiments')
    directory.mkdir(exist_ok=True)
    cases = []
    for family in ('right_triples', 'left_density', 'linear_response', 'quadruples'):
        cases.append((family, json.load(open(PARTICIPANT / 'input' / (family + '.json')))))
        cases.append((family + '_expanded', expanded(family, 80, {'o': 20, 'v': 112}, 1.0, 431)))
        cases.append((family + '_mutated', mutated(family, 80, {'o': 8, 'v': 48}, 1.0, 592)))
    cases.extend([('chain3', chain_case(63, 80, 3)), ('random6', random_case(772, 80, 6))])
    results = []
    environment = os.environ.copy()
    environment.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    for label, case in cases:
        input_path = directory / (label + '.json')
        output_path = directory / (label + '.plan.json')
        input_path.write_text(json.dumps(case))
        started = time.monotonic()
        result = subprocess.run([sys.executable, 'solve.py', str(input_path), str(output_path)],
                                timeout=30, capture_output=True, text=True, env=environment, preexec_fn=limits)
        elapsed = time.monotonic() - started
        if result.returncode:
            raise RuntimeError((label, result.returncode, result.stdout, result.stderr))
        metrics = validate(case, json.load(open(output_path)))
        basecost = validate(case, baseline.solve(case))['flops']
        metrics.update(name=label, seconds=elapsed, speedup=basecost / metrics['flops'])
        results.append(metrics)
        print('cli', label, round(elapsed, 3), 'speedup', round(metrics['speedup'], 4), 'peak', metrics['peak_elements'], flush=True)
    (directory / 'validation_results.json').write_text(json.dumps(results, indent=2))
    return len(results)


if __name__ == '__main__':
    count = direct_tests()
    count += cli_tests()
    print('validated plans:', count, flush=True)
