import contextlib
import io
import json
import multiprocessing
import os
import sys
import time

sys.path.insert(0, os.environ['PART'] + '/workspace')
from verify import check
from subspace_synth import synthesize
from gauge import optimize


def objective(record):
    return sum(record['usage'][key] / record['caps'][key] for key in ('and', 'affine', 'ancilla'))


def worker(task):
    instance, seed, amount = task
    log = io.StringIO()
    try:
        with contextlib.redirect_stdout(log):
            circuit = synthesize(instance, seed, amount)
            if circuit is not None:
                circuit = optimize(circuit, instance['n'], seed=seed)
        return instance['id'], seed, amount, circuit, log.getvalue()
    except Exception as error:
        return instance['id'], seed, amount, None, log.getvalue() + repr(error)


if __name__ == '__main__':
    started = time.monotonic()
    suite = json.load(open(os.environ['PART'] + '/input/suite.json'))
    by_id = {instance['id']: instance for instance in suite['instances']}
    best = {circuit['id']: circuit for circuit in json.load(open('circuits.json'))['circuits']}
    scores = {identifier: objective(check(by_id[identifier], circuit)) for identifier, circuit in best.items()}
    for filename in ['subspace_circuits.json']:
        for circuit in json.load(open(filename))['circuits']:
            identifier = circuit['id']
            record = check(by_id[identifier], circuit)
            if record['exact'] and record['usage']['depth'] <= record['caps']['depth'] and objective(record) < scores[identifier]:
                best[identifier], scores[identifier] = circuit, objective(record)
    tasks = []
    for seed in [5, 23, 101, 137]:
        for instance in suite['instances']:
            for amount in {10: [48, 50, 52, 54, 56, 60, 64], 11: [104, 108, 112, 116, 120, 128], 12: [68, 72, 76, 80, 88, 96, 104, 112]}[instance['n']]:
                tasks.append((instance, seed, amount))
    with multiprocessing.Pool(3) as pool:
        results = pool.imap_unordered(worker, tasks)
        for completed in range(len(tasks)):
            remaining = 150 - (time.monotonic() - started)
            if remaining <= 0:
                break
            try:
                identifier, seed, amount, circuit, log = results.next(timeout=remaining)
            except multiprocessing.TimeoutError:
                break
            print('DONE', completed, identifier, seed, amount, flush=True)
            print(log, flush=True)
            if circuit is None:
                continue
            record = check(by_id[identifier], circuit)
            if not record['exact'] or record['usage']['depth'] > record['caps']['depth']:
                print('INVALID', record, flush=True)
                continue
            if objective(record) < scores[identifier]:
                best[identifier], scores[identifier] = circuit, objective(record)
                print('BEST', identifier, record['usage'], scores[identifier], flush=True)
                json.dump({'circuits': list(best.values())}, open('circuits.json', 'w'))
        pool.terminate()
    json.dump({'circuits': list(best.values())}, open('circuits.json', 'w'))
    records = [check(instance, best[instance['id']]) for instance in suite['instances']]
    json.dump(records, open('improvement_records.json', 'w'), indent=2)
    print('FINISHED', time.monotonic() - started, flush=True)
