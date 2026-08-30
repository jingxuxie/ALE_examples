import importlib.util
import json
import os
from pathlib import Path
import random
import resource
import subprocess
import sys
import time

assets = Path(os.environ['ASSETS'])
sys.path.insert(0, str(assets / 'workspace'))
from phase_model import check
import solution

spec = importlib.util.spec_from_file_location('baseline', assets / 'baseline/solution.py')
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)


def fuzz_instance(seed):
    randomizer = random.Random(seed)
    size = randomizer.randint(12, 28)
    count = randomizer.randint(24, 96)
    kind = seed % 6
    links = set()
    for qubit in range(1, size):
        parent = qubit - 1 if kind == 0 else 0 if kind == 1 else randomizer.randrange(qubit)
        links.add((parent, qubit))
    if kind >= 2:
        for first in range(size):
            for second in range(first + 1, size):
                if randomizer.random() < (0.65 if kind == 5 else 0.10):
                    links.add((first, second))
    edges = []
    for first, second in sorted(links):
        for control, target in ((first, second), (second, first)):
            weight = randomizer.randint(1, 12)
            if kind == 2:
                weight = 1 if control < target else 12
            edges.append([control, target, weight, randomizer.randint(1, 6)])
    terms = set()
    while len(terms) < count:
        weight = randomizer.randint(1, min(size, 4)) if kind <= 2 else randomizer.randint(1, size)
        terms.add(sum(1 << qubit for qubit in randomizer.sample(range(size), weight)))
    return {'n': size, 'edges': edges, 'terms': sorted(terms)}


def engine_response(instance, budget):
    values = [instance['n'], len(instance['edges']), len(instance['terms'])]
    values.extend(value for edge in instance['edges'] for value in edge)
    values.extend(instance['terms'])
    started = time.monotonic()
    process = subprocess.run(['./engine', str(budget)], input=' '.join(map(str, values)), text=True, capture_output=True, check=True, timeout=14)
    return json.loads(process.stdout), time.monotonic() - started, process.stderr.strip()


def main():
    report = {'fuzz': [], 'public': [], 'maximum_size': []}
    for seed in range(60):
        instance = fuzz_instance(38100 + seed)
        response, elapsed, details = engine_response(instance, 0.08)
        metrics = check(instance, response)
        report['fuzz'].append({'seed': seed, 'seconds': elapsed, **metrics})
        if seed % 10 == 9:
            print('fuzz valid', seed + 1, flush=True)
    singleton = fuzz_instance(38100)
    singleton['n'] = 28
    singleton['edges'] = [edge for qubit in range(27) for edge in ([qubit, qubit + 1, 2, 3], [qubit + 1, qubit, 1, 6])]
    singleton['terms'] = [1 << qubit for qubit in range(24)]
    response, elapsed, details = engine_response(singleton, 0.1)
    check(singleton, response)
    check(singleton, solution.fallback(singleton))
    report['singleton_seconds'] = elapsed
    for seed in range(12):
        instance = fuzz_instance(39800 + seed)
        check(instance, solution.fallback(instance))
    report['fallback_valid'] = 13
    print('singletons and fallback valid', flush=True)
    public = [json.loads(line) for line in (assets / 'input/examples.jsonl').read_text().splitlines() if line.strip()]
    process = subprocess.Popen([sys.executable, 'solution.py'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    with open('circuits.jsonl', 'w') as circuits:
        for index, instance in enumerate(public):
            started = time.monotonic()
            process.stdin.write(json.dumps(instance) + '\n')
            process.stdin.flush()
            line = process.stdout.readline()
            elapsed = time.monotonic() - started
            response = json.loads(line)
            metrics = check(instance, response)
            baseline_cost = check(instance, baseline.compile_circuit(instance))['cost']
            entry = {'case': index, 'seconds': elapsed, 'baseline_cost': baseline_cost, 'reduction': 1 - metrics['cost'] / baseline_cost, **metrics}
            report['public'].append(entry)
            circuits.write(line)
            print('public', json.dumps(entry), flush=True)
    process.stdin.close()
    assert process.wait(timeout=5) == 0
    assert not process.stdout.read()
    assert not process.stderr.read()
    large = [json.loads(line) for line in Path('stress_cases.jsonl').read_text().splitlines() if line.strip()]
    for family, instance in enumerate(large[2::3]):
        response, elapsed, details = engine_response(instance, 8.3)
        metrics = check(instance, response)
        baseline_cost = check(instance, baseline.compile_circuit(instance))['cost']
        entry = {'family': family, 'seconds': elapsed, 'baseline_cost': baseline_cost, 'reduction': 1 - metrics['cost'] / baseline_cost, **metrics, 'details': details}
        report['maximum_size'].append(entry)
        print('maximum_size', json.dumps(entry), flush=True)
    report['peak_child_rss_kib'] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    report['public_mean_reduction'] = sum(entry['reduction'] for entry in report['public']) / len(report['public'])
    report['public_worst_reduction'] = min(entry['reduction'] for entry in report['public'])
    Path('validation_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('validation complete', report['public_mean_reduction'], report['public_worst_reduction'], 'peak_child_rss_kib', report['peak_child_rss_kib'], flush=True)


if __name__ == '__main__':
    main()
