import copy
import importlib.util
import json
import math
import random
import string
import sys
import time

from benchmark import PARTICIPANT, REPORTS, validate
from solve import solve

spec = importlib.util.spec_from_file_location('reference_baseline', PARTICIPANT / 'baseline' / 'solve.py')
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)


def set_budget(case, slack):
    frontiers = [reference.term_frontier(case, term) for term in case['terms']]
    case['memory_cap'] = math.ceil(max(min(entry[1] for entry in frontier) for frontier in frontiers) * slack)
    return sum(min(entry[0] for entry in frontier if entry[1] <= case['memory_cap']) for frontier in frontiers)


def permute(term, types, generator):
    groups = {}
    for axis, kind in types.items():
        groups.setdefault(kind, []).append(axis)
    mapping = {}
    for group in groups.values():
        shuffled = list(group)
        generator.shuffle(shuffled)
        mapping.update(zip(group, shuffled))
    factors = [[name, ''.join(mapping[axis] for axis in axes)] for name, axes in term['inputs']]
    generator.shuffle(factors)
    output = [mapping[axis] for axis in term['output']]
    generator.shuffle(output)
    return {'inputs': factors, 'output': ''.join(output)}


def randomized_case(generator):
    shapes = [('o', 'o'), ('o', 'v'), ('v', 'o'), ('v', 'v'),
              ('o', 'o', 'v', 'v'), ('o', 'v', 'v', 'o'), ('v', 'v', 'o', 'o')]
    tensors = {'intermediate_' + str(number): list(shape) for number, shape in enumerate(shapes)}
    labels = {'o': string.ascii_lowercase, 'v': string.ascii_uppercase}
    types = {axis: kind for kind, axes in labels.items() for axis in axes}
    templates = []
    for template in range(generator.randint(5, 20)):
        selected = generator.choices(list(tensors), k=generator.randint(3, 6))
        ports = {kind: [] for kind in labels}
        factor_axes = [[''] * len(tensors[name]) for name in selected]
        for position, name in enumerate(selected):
            for axis, kind in enumerate(tensors[name]):
                ports[kind].append((position, axis))
        output = []
        for kind, available in ports.items():
            generator.shuffle(available)
            serial = 0
            while available:
                factor, axis = available.pop()
                label = labels[kind][serial]
                serial += 1
                factor_axes[factor][axis] = label
                compatible = [position for position, port in enumerate(available) if port[0] != factor]
                if compatible and generator.random() < 0.85:
                    other_factor, other_axis = available.pop(generator.choice(compatible))
                    factor_axes[other_factor][other_axis] = label
                else:
                    output.append(label)
        templates.append({'inputs': [[name, ''.join(axes)] for name, axes in zip(selected, factor_axes)],
                          'output': ''.join(output)})
    case = {'tensors': tensors, 'index_types': types,
            'dimensions': {'o': generator.randint(4, 20), 'v': generator.randint(12, 112)},
            'terms': [permute(generator.choice(templates), types, generator) for term in range(generator.randint(20, 80))],
            'memory_cap': 1}
    return case


def main():
    generator = random.Random(893941)
    results = []
    cases = []
    for path in sorted((PARTICIPANT / 'input').glob('*.json')):
        if 'baseline' in path.name:
            continue
        original = json.loads(path.read_text())
        for count in (40, 80):
            case = copy.deepcopy(original)
            case['dimensions'] = {'o': generator.randint(4, 20), 'v': generator.randint(12, 112)}
            case['terms'] = [permute(original['terms'][number % 20], case['index_types'], generator)
                             for number in range(count)]
            generator.shuffle(case['terms'])
            cases.append((path.stem + '_' + str(count), case))
    for number in range(int(sys.argv[1]) if len(sys.argv) > 1 else 25):
        cases.append(('random_' + str(number), randomized_case(generator)))
    for name, case in cases:
        baseline = set_budget(case, generator.choice((1, 1.01, 1.05, 1.2, 2)))
        started = time.monotonic()
        plan = solve(case)
        elapsed = time.monotonic() - started
        result = validate(case, plan)
        result.update(name=name, speedup=baseline / result['flops'], seconds=elapsed)
        results.append(result)
        print(json.dumps(result), flush=True)
    (REPORTS / 'stress_results.json').write_text(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
