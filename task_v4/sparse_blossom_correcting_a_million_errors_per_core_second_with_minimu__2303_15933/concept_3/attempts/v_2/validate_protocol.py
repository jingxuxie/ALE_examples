import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import argparse
import json
from pathlib import Path
import resource
import select
import subprocess
import sys
import time
import numpy as np
from solution import Model

parser = argparse.ArgumentParser()
parser.add_argument('--sampler', choices=('events', 'multinomial'), default='events')
parser.add_argument('--seed-offset', type=int, default=9951)
parser.add_argument('--output', default='protocol_results.json')
parser.add_argument('worker', nargs=argparse.REMAINDER)
arguments = parser.parse_args()
worker = arguments.worker
if worker and worker[0] == '--':
    worker = worker[1:]
if not worker:
    worker = ['/usr/bin/python3', 'solution.py']
episodes = json.loads(Path('../../participant/input/training.json').read_text())['episodes']
records = []

def resource_limits():
    resource.setrlimit(resource.RLIMIT_CPU, (60, 61))
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024 ** 3, 3 * 1024 ** 3))

for episode in episodes:
    spec = episode['spec']
    truth = np.array(episode['rates'])
    model = Model(spec)
    probability = model.distribution(np.log(truth))
    probability /= probability.sum(axis=1, keepdims=True)
    masks = np.array([channel['masks'] for channel in spec['channels']])
    rng = np.random.default_rng(episode['sample_seed'] + arguments.seed_offset)
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.monotonic()
    process = subprocess.Popen(worker, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, preexec_fn=resource_limits)
    process.stdin.write(json.dumps({'type': 'hello', 'spec': spec}) + '\n')
    process.stdin.flush()
    queries = 0
    remaining = spec['shot_budget']
    try:
        while True:
            assert select.select([process.stdout], [], [], 900)[0], 'Wall timeout'
            line = process.stdout.readline()
            assert line, process.stderr.read()
            message = json.loads(line)
            if message['type'] == 'final':
                assert set(message) == {'type', 'rates'}
                estimated = np.array(message['rates'])
                assert estimated.shape == truth.shape
                assert np.all(np.isfinite(estimated)) and np.all(estimated > 0)
                process.stdin.close()
                assert process.wait(timeout=10) == 0
                assert process.stdout.read() == ''
                after = resource.getrusage(resource.RUSAGE_CHILDREN)
                cpu = after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime
                risks = np.sqrt(model.groups @ np.log(estimated / truth) ** 2)
                record = {'episode': episode['id'], 'regime': spec['regime'], 'queries': queries,
                          'shots': spec['shot_budget'] - remaining, 'cpu': cpu,
                          'wall': time.monotonic() - started, 'max_rss_kib': after.ru_maxrss,
                          'risks': risks.tolist()}
                records.append(record)
                print(json.dumps(record), flush=True)
                Path(arguments.output).write_text(json.dumps(records, indent=2))
                break
            assert message['type'] == 'query' and set(message) == {'type', 'action', 'shots'}
            action_id, shots = message['action'], message['shots']
            assert type(action_id) is int and 0 <= action_id < len(spec['actions'])
            assert type(shots) is int and 1 <= shots <= min(remaining, spec['max_shots_per_query'])
            assert queries < spec['max_queries']
            action = spec['actions'][action_id]
            if arguments.sampler == 'multinomial':
                counts = rng.multinomial(shots, probability[action_id])
            else:
                modes = rng.choice(2, size=shots, p=action['mode_weights'])
                exposures = np.array(action['exposures'])[modes]
                firings = rng.random(exposures.shape) < -np.expm1(-2 * exposures * truth) / 2
                alternate = rng.random(exposures.shape) < np.array(action['alternate_probability'])
                active_masks = np.where(alternate, masks[:, 1], masks[:, 0])
                syndromes = np.bitwise_xor.reduce(np.where(firings, active_masks, 0), axis=1)
                counts = np.bincount(syndromes, minlength=model.state_count)
            remaining -= shots
            queries += 1
            response = {'type': 'observation', 'action': action_id, 'shots': shots,
                        'counts': counts.tolist(), 'shots_remaining': remaining,
                        'queries_remaining': spec['max_queries'] - queries}
            process.stdin.write(json.dumps(response) + '\n')
            process.stdin.flush()
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
cells = []
for regime in ('chain_hooks', 'patch_crosstalk', 'burst_aliases'):
    risks = np.array([record['risks'] for record in records if record['regime'] == regime])
    cells.extend(np.sqrt(np.mean(risks ** 2, axis=0)))
print('mean', np.mean(cells), 'worst', np.max(cells), flush=True)
