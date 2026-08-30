import importlib.util
import json
import os
import random
import time

from phase_model import check
from solution import compile_circuit


assets = os.environ['ASSETS']
specification = importlib.util.spec_from_file_location('reference_baseline', assets + '/baseline/solution.py')
baseline = importlib.util.module_from_spec(specification)
specification.loader.exec_module(baseline)
public = [json.loads(line) for line in open(assets + '/input/examples.jsonl')]
fixtures = [('public_' + str(index), index // 2, instance) for index, instance in enumerate(public)]
for variant in range(2):
    for index, instance in enumerate(public):
        randomizer = random.Random(1000 + 193 * variant + index)
        permutation = list(range(instance['n']))
        randomizer.shuffle(permutation)
        edges = [[permutation[control], permutation[target], weight, duration]
                 for control, target, weight, duration in instance['edges']]
        terms = [sum(1 << permutation[qubit] for qubit in range(instance['n']) if mask & (1 << qubit))
                 for mask in instance['terms']]
        randomizer.shuffle(edges)
        randomizer.shuffle(terms)
        fixtures.append(('permuted_' + str(variant) + '_' + str(index), index // 2,
                         {'n': instance['n'], 'edges': edges, 'terms': terms}))
results = []
with open('validation_circuits.jsonl', 'w') as circuits:
    for name, family, instance in fixtures:
        baseline_result = check(instance, baseline.compile_circuit(instance))
        started = time.monotonic()
        response = compile_circuit(instance)
        elapsed = time.monotonic() - started
        result = check(instance, response)
        result.update(name=name, family=family, seconds=elapsed,
                      baseline_cost=baseline_result['cost'],
                      reduction=1 - result['cost'] / baseline_result['cost'])
        assert elapsed < 15, result
        results.append(result)
        circuits.write(json.dumps(response) + '\n')
        circuits.flush()
        with open('validation_report.json', 'w') as output:
            json.dump(results, output, indent=2)
        print(json.dumps(result), flush=True)
for group in (results[:4], results):
    print('SUMMARY', len(group), 'mean', sum(result['reduction'] for result in group) / len(group),
          'families', [sum(result['reduction'] for result in group if result['family'] == family)
                       / sum(result['family'] == family for result in group) for family in range(2)],
          'max_seconds', max(result['seconds'] for result in group), flush=True)
