import copy
import importlib.util
import json
import math
import random
import string
import sys
import time
from pathlib import Path

from model import Graph
from solve import Planner, solve


PARTICIPANT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/pq_a_tool_for_prototyping_many_body_methods_for_quantum_chemistry__2106_06850/concept_1/participant')
sys.dont_write_bytecode = True
sys.path.insert(0, str(PARTICIPANT / 'workspace'))
from contract import validate

spec = importlib.util.spec_from_file_location('baseline', PARTICIPANT / 'baseline/solve.py')
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)


def expanded(family, count, dimensions, multiplier, seed):
    generator = random.Random(seed)
    case = json.load(open(PARTICIPANT / 'input' / (family + '.json')))
    originals = case['terms']
    terms = []
    for position in range(count):
        term = copy.deepcopy(originals[position % len(originals)] if position < len(originals) else generator.choice(originals))
        labels = set(''.join(axes for name, axes in term['inputs']) + term['output'])
        mapping = {}
        for kind in case['dimensions']:
            source = sorted(label for label in labels if case['index_types'][label] == kind)
            targets = [label for label in case['index_types'] if case['index_types'][label] == kind]
            generator.shuffle(targets)
            mapping.update(zip(source, targets))
        term['inputs'] = [[name, ''.join(mapping[axis] for axis in axes)] for name, axes in term['inputs']]
        term['output'] = ''.join(mapping[axis] for axis in term['output'])
        generator.shuffle(term['inputs'])
        if position >= len(originals):
            output = list(term['output'])
            generator.shuffle(output)
            term['output'] = ''.join(output)
        terms.append(term)
    generator.shuffle(terms)
    case['terms'] = terms
    case['dimensions'] = dimensions
    peaks = [min(entry[1] for entry in baseline.term_frontier(case, term)) for term in terms]
    case['memory_cap'] = math.ceil(max(peaks) * multiplier)
    return case


def check(case):
    started = time.monotonic()
    baseplan = baseline.solve(case)
    basecost = validate(case, baseplan)['flops']
    baseline_time = time.monotonic() - started
    started = time.monotonic()
    plan = solve(case)
    elapsed = time.monotonic() - started
    result = validate(case, plan)
    return (round(basecost / result['flops'], 4), round(elapsed, 3),
            round(result['peak_elements'] / case['memory_cap'], 4), round(baseline_time, 3))


def main():
    families = ('right_triples', 'left_density', 'linear_response', 'quadruples')
    for count, dimensions, multiplier in ((80, {'o': 5, 'v': 15}, 1.2),
                                          (80, {'o': 8, 'v': 48}, 1.0),
                                          (80, {'o': 16, 'v': 112}, 1.1),
                                          (40, {'o': 4, 'v': 12}, 1.0)):
        ratios = []
        for family in families:
            case = expanded(family, count, dimensions, multiplier, 431 + count)
            result = check(case)
            ratios.append(result[0])
            print(family, count, dimensions, multiplier, result, flush=True)
        print('geomean', math.prod(ratios) ** 0.25, flush=True)


if __name__ == '__main__':
    main()
