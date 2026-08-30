import search
import argparse
import concurrent.futures
import json
import numpy as np
import time

def ranking(row):
    fraction = min(row['coverage']) / row['count']
    return row['score'] - .06 * max(0., .85 - fraction)

def align(fields, reference):
    variants = [sign * np.roll(source, shift) for source in (fields, fields[::-1])
                for shift in range(12) for sign in (-1, 1)]
    return min(variants, key=lambda candidate: np.mean((candidate-reference)**2))

def run_batch(executor, fields_list, random, count):
    jobs = [(fields, int(random.integers(2**32)), count, .055) for fields in fields_list]
    return sorted([row for row in executor.map(search.evaluate, jobs) if row is not None], key=ranking, reverse=True)

def main():
    lock = (search.ROOT / '.workers.lock').open('a')
    search.fcntl.flock(lock, search.fcntl.LOCK_EX)
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='refined.json')
    parser.add_argument('--name', default='evolution')
    parser.add_argument('--rounds', type=int, default=15)
    parser.add_argument('--count', type=int, default=600)
    parser.add_argument('--seed', type=int, default=907326)
    arguments = parser.parse_args()
    random = np.random.default_rng(arguments.seed)
    parents = json.loads((search.ROOT / arguments.source).read_text())[:16]
    started = time.monotonic()
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        parents = run_batch(executor, [row['fields'] for row in parents], random, 32)
        for iteration in range(arguments.rounds):
            fields_list = []
            for index in range(arguments.count):
                parent = parents[int(random.exponential(3)) % min(12, len(parents))]
                fields = np.array(parent['fields'])
                mutation = random.choice([.02, .04, .07, .12, .2, .35, .6], p=[.10,.15,.20,.20,.15,.15,.05])
                mode = random.random()
                if mode < .65:
                    fields += random.normal(size=12) * mutation
                elif mode < .8:
                    positions = random.choice(12, int(random.integers(1, 5)), replace=False)
                    fields[positions] += random.normal(size=len(positions)) * mutation * 2
                elif mode < .9:
                    domains = np.sign(fields)
                    fields += domains * random.normal() * mutation
                    fields += random.normal(size=12) * .025
                else:
                    other = np.array(parents[int(random.integers(len(parents)))]['fields'])
                    other = align(other, fields)
                    weight = random.uniform(.1, .9)
                    fields = weight * fields + (1-weight) * other + random.normal(size=12) * .04
                if random.random() < .2:
                    fields *= random.uniform(.94, 1.06)
                fields -= fields.mean()
                fields_list.append(fields.tolist())
            screened = run_batch(executor, fields_list, random, 2)
            print(json.dumps(dict(event='screened', iteration=iteration, elapsed=time.monotonic()-started,
                                  survivors=len(screened), best=screened[0] if screened else None)), flush=True)
            refined = run_batch(executor, [row['fields'] for row in screened[:64]], random, 12)
            merged = refined[:20] + parents[:8]
            parents = run_batch(executor, [row['fields'] for row in merged], random, 32)
            (search.ROOT / (arguments.name + '.json')).write_text(json.dumps(parents, indent=2))
            (search.ROOT / (arguments.name + f'.round{iteration:02}.json')).write_text(json.dumps(parents, indent=2))
            best = parents[0]
            witness = {key: best[key] for key in ('fields', 'orientation')}
            witness['schema_version'] = 1
            (search.ROOT / 'witness.json').write_text(json.dumps(witness, indent=2) + '\n')
            print(json.dumps(dict(event='round', iteration=iteration, elapsed=time.monotonic()-started, best=best)), flush=True)

if __name__ == '__main__':
    main()
