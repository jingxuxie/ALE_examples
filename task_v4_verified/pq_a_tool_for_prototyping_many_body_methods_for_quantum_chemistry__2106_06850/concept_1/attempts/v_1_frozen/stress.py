import copy
import json
import math
import random
import string
import time

from bench import baseline, check, expanded, validate
from model import Graph
from solve import Planner, independent, solve
from optimize import optimize, score
from global_lp import optimize_lp


def mutated(family, count, dimensions, multiplier, seed):
    generator = random.Random(seed)
    case = expanded(family, count, dimensions, multiplier, seed)
    for term in case['terms']:
        for name, axes in term['inputs']:
            pass
        for position, (name, axes) in enumerate(term['inputs']):
            changed = list(axes)
            for kind in dimensions:
                slots = [slot for slot, axis in enumerate(axes) if case['index_types'][axis] == kind]
                labels = [axes[slot] for slot in slots]
                generator.shuffle(labels)
                for slot, label in zip(slots, labels):
                    changed[slot] = label
            term['inputs'][position] = [name, ''.join(changed)]
    peaks = [min(entry[1] for entry in baseline.term_frontier(case, term)) for term in case['terms']]
    case['memory_cap'] = math.ceil(max(peaks) * multiplier)
    return case


def random_case(seed, count=50, factors_count=6, tensors=None):
    generator = random.Random(seed)
    if tensors is None:
        tensors = {'_p0': 'ov', 'B': 'vv', 'C': 'oo', 'D': 'ovv', 'E': 'ovvo', 'F': 'vvoo', 'G': 'vo'}
    dimensions = {'o': 4, 'v': 12}
    labels = {'o': string.ascii_lowercase, 'v': string.ascii_uppercase}
    kinds = {axis: kind for kind, axes in labels.items() for axis in axes}
    names = list(tensors)
    terms = []
    for position in range(count):
        factor_names = [generator.choice(names) for unused in range(factors_count)]
        slots = [(factor, axis, kind) for factor, name in enumerate(factor_names) for axis, kind in enumerate(tensors[name])]
        generator.shuffle(slots)
        groups = []
        while slots:
            slot = slots.pop()
            alternatives = [other for other in slots if other[0] != slot[0] and other[2] == slot[2]]
            if alternatives and (len(slots) > 5 or generator.random() < 0.7):
                other = generator.choice(alternatives)
                slots.remove(other)
                groups.append([slot, other])
            else:
                groups.append([slot])
        operands = [[None] * len(tensors[name]) for name in factor_names]
        counters = {'o': 0, 'v': 0}
        output = []
        for group in groups:
            kind = group[0][2]
            label = labels[kind][counters[kind]]
            counters[kind] += 1
            for factor, axis, unused in group:
                operands[factor][axis] = label
            if len(group) == 1:
                output.append(label)
        terms.append({'inputs': [[name, ''.join(axes)] for name, axes in zip(factor_names, operands)], 'output': ''.join(output)})
    case = {'dimensions': dimensions, 'tensors': tensors, 'index_types': kinds, 'terms': terms, 'memory_cap': 10**100}
    peaks = [min(entry[1] for entry in baseline.term_frontier(case, term)) for term in terms]
    case['memory_cap'] = math.ceil(max(peaks) * 1.05)
    return case


def chain_case(seed, count=80, slots=3):
    generator = random.Random(seed)
    names = ['M' + str(position) for position in range(9)]
    tensors = {name: ['v', 'v'] for name in names}
    pairs = [(generator.choice(names), generator.choice(names)) for unused in range(12)]
    terms = []
    for position in range(count):
        factors = sum((list(generator.choice(pairs)) for unused in range(3)), [])
        inputs = [[name, string.ascii_lowercase[position:position + 2]] for position, name in enumerate(factors)]
        generator.shuffle(inputs)
        terms.append({'inputs': inputs, 'output': 'ag'})
    return {'dimensions': {'v': 12}, 'tensors': tensors, 'index_types': {axis: 'v' for axis in string.ascii_lowercase},
            'terms': terms, 'memory_cap': slots * 144}


def report(case, label):
    graph_start = time.monotonic()
    graph = Graph(case)
    graph_time = time.monotonic() - graph_start
    started = time.monotonic()
    baseplan = baseline.solve(case)
    basecost = validate(case, baseplan)['flops']
    base_time = time.monotonic() - started
    started = time.monotonic()
    oldplan = solve(case)
    oldresult = validate(case, oldplan)
    oldtime = time.monotonic() - started
    print(label, 'nodes', len(graph.nodes), 'ops', sum(len(node.ops) for node in graph.nodes),
          'roots', len(graph.roots), 'graph', round(graph_time, 3), 'baseline', round(base_time, 3),
          'initial', round(basecost / oldresult['flops'], 3), round(oldtime, 3), flush=True)
    started = time.monotonic()
    choices = optimize(graph, started + 2)
    lpchoice = optimize_lp(graph, choices[0], time.monotonic() + 3)
    if score(graph, lpchoice) <= score(graph, choices[0]):
        choices.insert(0, lpchoice)
    print('global', [score(graph, choice) for choice in choices], 'time', round(time.monotonic() - started, 3), flush=True)
    best = oldresult['flops']
    for choice in choices[:2]:
        for exponent, ordering in ((0, 0), (0, 1), (0.7, 0), (0.7, 1)):
            started = time.monotonic()
            planner = Planner(graph, exponent, ordering, preferred=choice)
            plan = planner.solve()
            result = validate(case, plan)
            best = min(best, result['flops'])
            print(exponent, ordering, round(basecost / result['flops'], 3), round(time.monotonic() - started, 3), flush=True)
    print('best', round(basecost / best, 4), 'improvement', round(oldresult['flops'] / best, 4), flush=True)


if __name__ == '__main__':
    for family in ('right_triples', 'left_density', 'linear_response', 'quadruples'):
        report(mutated(family, 80, {'o': 6, 'v': 30}, 1, 827), family)
    report(random_case(772, 80, 6), 'random')
