import contextlib
import io
import json
import multiprocessing
import os
import sys
import time

from gauge import optimize

sys.path.insert(0, os.environ['PART'] + '/workspace')
from verify import check


def worker(task):
    instance, circuit, seed = task
    with contextlib.redirect_stdout(io.StringIO()):
        result = optimize(circuit, instance['n'], seed=seed, temperature=1.5)
    return instance['id'], result


if __name__ == '__main__':
    started = time.monotonic()
    suite = json.load(open(os.environ['PART'] + '/input/suite.json'))
    instances = {instance['id']: instance for instance in suite['instances']}
    circuits = {circuit['id']: circuit for circuit in json.load(open('circuits.json'))['circuits']}
    costs = {identifier: check(instances[identifier], circuit)['usage']['affine'] for identifier, circuit in circuits.items()}
    tasks = [(instance, circuits[instance['id']], seed) for seed in range(10, 40) for instance in suite['instances']]
    with multiprocessing.Pool(3) as pool:
        results = pool.imap_unordered(worker, tasks)
        for completed in range(len(tasks)):
            remaining = 20 - (time.monotonic() - started)
            if remaining <= 0:
                break
            try:
                identifier, circuit = results.next(timeout=remaining)
            except multiprocessing.TimeoutError:
                break
            record = check(instances[identifier], circuit)
            if record['exact'] and record['usage']['depth'] <= record['caps']['depth'] and record['usage']['affine'] < costs[identifier]:
                print(identifier, costs[identifier], record['usage']['affine'], flush=True)
                circuits[identifier], costs[identifier] = circuit, record['usage']['affine']
        pool.terminate()
    json.dump({'circuits': list(circuits.values())}, open('circuits.json', 'w'))
