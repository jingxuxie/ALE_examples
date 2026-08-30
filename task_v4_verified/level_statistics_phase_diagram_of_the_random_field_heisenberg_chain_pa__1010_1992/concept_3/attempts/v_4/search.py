import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[variable] = '1'
import argparse
import concurrent.futures
import fcntl
import json
from pathlib import Path
import sys
import time
import numpy as np

SOURCE = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/level_statistics_phase_diagram_of_the_random_field_heisenberg_chain_pa__1010_1992/concept_3/generations/generation_2/participant')
sys.path.insert(0, str(SOURCE / 'workspace'))
from exact import spectrum, proxy_statistics, validate_fields

ROOT = Path(__file__).resolve().parent
SCALES = np.array([1., 1., .96, 1.04])
AMPLITUDES = np.array([.04, .12, .08, .08])

def discrepancy(fields):
    return proxy_statistics(spectrum(fields))['difference']

def noise_bank(seed, count):
    random = np.random.default_rng(seed)
    offsets = random.uniform(-1, 1, (4, count, 12))
    offsets -= offsets.mean(axis=2, keepdims=True)
    return offsets * AMPLITUDES[:, None, None]

def evaluate(job):
    fields, seed, count, cutoff = job
    fields = np.asarray(fields)
    try:
        validate_fields(fields)
        base = discrepancy(fields)
        orientation = 1 if base >= 0 else -1
        if abs(base) < cutoff:
            return None
        offsets = noise_bank(seed, count)
        values = np.zeros((4, count))
        for member in range(count):
            for family in range(4):
                values[family, member] = orientation * discrepancy(SCALES[family] * fields + offsets[family, member])
            if member == 0 and values[:, 0].mean() < cutoff * .55:
                return None
        means = values.mean(axis=1)
        core = float(means.mean())
        worst = float(means.min())
        score = .65 * core + .35 * worst
        return dict(fields=fields.tolist(), orientation=orientation, base=abs(base), core=core,
                    worst=worst, means=means.tolist(), score=score,
                    coverage=(values >= .025).sum(axis=1).tolist(), count=count, seed=seed)
    except ValueError:
        return None

def generate(random, count):
    fields_list = []
    while len(fields_list) < count:
        mode = random.integers(10)
        width = np.exp(random.uniform(np.log(.7), np.log(6.0)))
        if mode < 4:
            fields = random.uniform(-1, 1, 12) * width
        elif mode == 4:
            fields = random.normal(size=12) * width
        elif mode == 5:
            fields = np.sin(np.arange(12) * random.uniform(.25, 3.1) + random.uniform(0, 6.3)) * width
            fields += random.normal(size=12) * random.uniform(.12, .5)
        elif mode == 6:
            fields = random.choice([-1., 1.], size=12) * width + random.normal(size=12) * random.uniform(.15, .8)
        elif mode == 7:
            fields = random.uniform(-.5, .5, 12)
            locations = random.choice(12, size=int(random.integers(1, 5)), replace=False)
            fields[locations] += random.uniform(-7, 7, len(locations))
        elif mode == 8:
            fields = np.arange(12) * width / 6 + random.normal(size=12) * random.uniform(.12, .7)
        else:
            fields = np.repeat(random.uniform(-width, width, 4), 3) + random.normal(size=12) * .25
        fields -= fields.mean()
        try:
            validate_fields(fields)
        except ValueError:
            continue
        fields_list.append(fields.tolist())
    return fields_list

def main():
    lock = (ROOT / '.workers.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX)
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['screen', 'refine', 'evolve'], default='screen')
    parser.add_argument('--count', type=int, default=3000)
    parser.add_argument('--seed', type=int, default=872332)
    parser.add_argument('--name', default='screen')
    parser.add_argument('--source', default='screen.json')
    parser.add_argument('--samples', type=int, default=2)
    parser.add_argument('--rounds', type=int, default=10)
    arguments = parser.parse_args()
    random = np.random.default_rng(arguments.seed)
    started = time.monotonic()
    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        if arguments.mode == 'screen':
            candidates = generate(random, arguments.count)
        else:
            previous = json.loads((ROOT / arguments.source).read_text())
            candidates = [row['fields'] for row in previous[:arguments.count]]
        rounds = arguments.rounds if arguments.mode == 'evolve' else 1
        for iteration in range(rounds):
            if arguments.mode == 'evolve':
                parents = previous[:min(len(previous), 24)]
                candidates = []
                for index in range(arguments.count):
                    parent = parents[int(random.exponential(5)) % len(parents)]
                    fields = np.array(parent['fields'])
                    magnitude = random.choice([.015, .03, .06, .10, .18, .3, .5])
                    fields += random.normal(size=12) * magnitude
                    if random.random() < .25:
                        fields *= random.uniform(.93, 1.07)
                    fields -= fields.mean()
                    candidates.append(fields.tolist())
            jobs = [(fields, int(random.integers(2**32)), arguments.samples, .065 if arguments.mode == 'screen' else .055) for fields in candidates]
            for index, result in enumerate(executor.map(evaluate, jobs)):
                if result is not None:
                    results.append(result)
                    results.sort(key=lambda row: row['score'], reverse=True)
                    results = results[:300]
                    if result == results[0]:
                        print(json.dumps(dict(event='best', index=index, iteration=iteration, elapsed=time.monotonic()-started, **result)), flush=True)
                if index % 100 == 0:
                    (ROOT / (arguments.name + '.json')).write_text(json.dumps(results, indent=2))
                    print(json.dumps(dict(event='progress', index=index, iteration=iteration, elapsed=time.monotonic()-started, survivors=len(results))), flush=True)
            (ROOT / (arguments.name + '.json')).write_text(json.dumps(results, indent=2))
            previous = results
    print(json.dumps(dict(event='finished', elapsed=time.monotonic()-started, candidates=len(candidates), survivors=len(results))), flush=True)

if __name__ == '__main__':
    main()
