import importlib.util
import json
import os
import random
import subprocess
import sys
import time

assets = os.environ['ASSETS']
sys.path.insert(0, assets + '/workspace')
from phase_model import check
spec = importlib.util.spec_from_file_location('baseline', assets + '/baseline/solution.py')
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)


def generate(family, size, count, seed):
    randomizer = random.Random(seed)
    links = set()
    width = 4 if size >= 16 else 3
    if family == 1:
        middle = size // 2
        for lower, upper in ((0, middle), (middle, size)):
            for qubit in range(lower, upper):
                if qubit + 1 < upper and (qubit - lower + 1) % width:
                    links.add((qubit, qubit + 1))
                if qubit + width < upper:
                    links.add((qubit, qubit + width))
        links.add((middle - 1, middle))
    else:
        for qubit in range(size):
            if qubit + 1 < size and (qubit + 1) % width:
                links.add((qubit, qubit + 1))
            if qubit + width < size:
                links.add((qubit, qubit + width))
        if family == 3:
            for unused in range(size // 5):
                first, second = randomizer.sample(range(size), 2)
                links.add(tuple(sorted((first, second))))
    permutation = list(range(size))
    randomizer.shuffle(permutation)
    neighbors = [[] for unused in range(size)]
    edges = []
    for first, second in sorted(links):
        first, second = permutation[first], permutation[second]
        neighbors[first].append(second)
        neighbors[second].append(first)
        for control, target in ((first, second), (second, first)):
            weight = randomizer.randint(1, 12 if family == 2 else 5)
            duration = randomizer.randint(1, 6)
            edges.append([control, target, weight, duration])
    bases = []
    for unused in range(max(4, count // 8)):
        current = randomizer.randrange(size)
        support = {current}
        length = randomizer.randint(2, 7) if family != 3 else randomizer.randint(size // 3, 3 * size // 4)
        while len(support) < length:
            current = randomizer.choice(neighbors[current])
            support.add(current)
        bases.append(sum(1 << qubit for qubit in support))
    terms = set()
    while len(terms) < count:
        if randomizer.random() < 0.7:
            mask = randomizer.choice(bases)
            for unused in range(randomizer.randrange(3)):
                if randomizer.random() < 0.8:
                    nearby = set()
                    for qubit in range(size):
                        if mask >> qubit & 1:
                            nearby.update(neighbors[qubit])
                    qubit = randomizer.choice(sorted(nearby)) if nearby else randomizer.randrange(size)
                else:
                    qubit = randomizer.randrange(size)
                mask ^= 1 << qubit
        else:
            current = randomizer.randrange(size)
            mask = 1 << current
            for unused in range(randomizer.randint(1, 5)):
                current = randomizer.choice(neighbors[current])
                mask |= 1 << current
        if mask:
            terms.add(mask)
    terms = list(terms)
    randomizer.shuffle(terms)
    return {'n': size, 'edges': edges, 'terms': terms}


def run(instance, budget):
    base_started = time.monotonic()
    base = check(instance, baseline.compile_circuit(instance))
    base_time = time.monotonic() - base_started
    values = [instance['n'], len(instance['edges']), len(instance['terms'])]
    values.extend(value for edge in instance['edges'] for value in edge)
    values.extend(instance['terms'])
    started = time.monotonic()
    process = subprocess.run(['./engine', str(budget)], input=' '.join(map(str, values)), text=True, capture_output=True, check=True)
    result = check(instance, json.loads(process.stdout))
    return {'base': base['cost'], 'cost': result['cost'], 'reduction': 1-result['cost']/base['cost'], 'base_time': base_time, 'wall': time.monotonic()-started, 'details': process.stderr.strip()}


if __name__ == '__main__':
    budget = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    results = []
    with open('stress_cases.jsonl', 'w') as output:
        for family in range(4):
            for case, (size, count) in enumerate(((12, 24), (20, 60), (28, 96))):
                instance = generate(family, size, count, 9237 + family * 123 + case)
                output.write(json.dumps(instance) + '\n')
                output.flush()
                result = run(instance, budget)
                result.update(family=family, case=case, size=size, terms=count)
                results.append(result)
                print(json.dumps(result), flush=True)
    print('mean', sum(result['reduction'] for result in results)/len(results))
    for family in range(4):
        reductions = [result['reduction'] for result in results if result['family'] == family]
        print('family', family, 'mean', sum(reductions)/len(reductions))
