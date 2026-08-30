import json
import os
import random
import resource
import string
import subprocess
import sys
import time

from benchmark import ARTIFACTS, REPORTS, ROOT, validate
from stress import randomized_case, set_budget


def limit_process():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_CPU, (28, 28))
    if hasattr(os, 'sched_setaffinity'):
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})


def main():
    cases = []
    tensors = {}
    terms = []
    for number in range(80):
        factors = []
        for position in range(6):
            name = 'tensor_' + str(number) + '_' + str(position)
            tensors[name] = ['v', 'v']
            factors.append([name, string.ascii_lowercase[position:position + 2]])
        terms.append({'inputs': factors, 'output': 'ag'})
    cases.append(('unique_chain', {'dimensions': {'o': 20, 'v': 112}, 'tensors': tensors,
                                  'index_types': dict.fromkeys(string.ascii_lowercase, 'v'),
                                  'terms': terms, 'memory_cap': 10 ** 18}))
    case = json.loads(json.dumps(cases[-1][1]))
    case['tensors'] = {'identical': ['v', 'v']}
    for term in case['terms']:
        for factor in term['inputs']:
            factor[0] = 'identical'
    cases.append(('identical_chain', case))
    generator = random.Random(410932)
    case = randomized_case(generator)
    case['terms'] = []
    while len(case['terms']) < 80:
        generated = randomized_case(generator)
        case['terms'].extend(term for term in generated['terms'] if len(term['inputs']) == 6)
    case['terms'] = case['terms'][:80]
    case['dimensions'] = {'o': 20, 'v': 112}
    set_budget(case, 1.01)
    cases.append(('mixed_six_factor', case))
    results = []
    for name, case in cases:
        source = ARTIFACTS / (name + '.case.json')
        destination = ARTIFACTS / (name + '.limit.plan.json')
        source.write_text(json.dumps(case))
        started = time.monotonic()
        process = subprocess.run([sys.executable, str(ROOT / 'solve.py'), str(source), str(destination)],
                                 preexec_fn=limit_process, timeout=30, capture_output=True, text=True)
        elapsed = time.monotonic() - started
        if process.returncode:
            raise RuntimeError(process.stderr)
        result = validate(case, json.loads(destination.read_text()))
        result.update(name=name, seconds=elapsed,
                      child_max_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
        print(json.dumps(result), flush=True)
        results.append(result)
    (REPORTS / 'limit_results.json').write_text(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
