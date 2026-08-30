import json
import os
import random
import resource
import select
import subprocess
import sys
import time

from phase_model import check
from solution import compile_circuit, fallback, valid


def fixture(size, topology, term_count, seed):
    randomizer = random.Random(seed)
    links = [(vertex, vertex + 1) for vertex in range(size - 1)]
    if topology == 'star':
        links = [(0, vertex) for vertex in range(1, size)]
    elif topology == 'complete':
        links = [(first, second) for first in range(size) for second in range(first + 1, size)]
    edges = []
    for first, second in links:
        for control, target in ((first, second), (second, first)):
            edges.append([control, target, randomizer.randint(1, 12), randomizer.randint(1, 6)])
    terms = set()
    while len(terms) < term_count:
        terms.add(randomizer.randrange(1, 1 << size))
    return {'n': size, 'edges': edges, 'terms': list(terms)}


results = []
for size, topology, count, seed in ((12, 'path', 96, 101), (28, 'path', 96, 102),
                                     (28, 'star', 96, 103), (28, 'complete', 96, 104)):
    instance = fixture(size, topology, count, seed)
    assert valid(instance, fallback(instance))
    check(instance, fallback(instance))
    started = time.monotonic()
    response = compile_circuit(instance, budget=11.8 if topology == 'path' and size == 28 else 0.8)
    elapsed = time.monotonic() - started
    result = check(instance, response)
    assert elapsed < 15
    result.update(n=size, topology=topology, terms=count, seconds=elapsed)
    results.append(result)
    print(json.dumps(result), flush=True)

assets = os.environ['ASSETS']
instance = json.loads(open(assets + '/input/examples.jsonl').readline())
process = subprocess.Popen([sys.executable, 'solution.py'], stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
started = time.monotonic()
process.stdin.write('\n' + json.dumps(instance) + '\n')
process.stdin.flush()
assert select.select([process.stdout], [], [], 14.9)[0], 'unflushed or late response'
response = json.loads(process.stdout.readline())
elapsed = time.monotonic() - started
assert elapsed < 15
result = check(instance, response)
result.update(protocol='streaming', seconds=elapsed)
results.append(result)
singletons = fixture(28, 'path', 24, 105)
singletons['terms'] = [1 << qubit for qubit in range(24)]
started = time.monotonic()
process.stdin.write(json.dumps(singletons) + '\n')
process.stdin.flush()
assert select.select([process.stdout], [], [], 2)[0], 'second response was not flushed'
response = json.loads(process.stdout.readline())
result = check(singletons, response)
result.update(protocol='second_request', seconds=time.monotonic() - started)
results.append(result)
process.stdin.close()
assert process.wait(timeout=2) == 0
assert not process.stderr.read()
report = {'cases': results, 'peak_rss_mib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024}
with open('resource_report.json', 'w') as output:
    json.dump(report, output, indent=2)
print(json.dumps(report), flush=True)
