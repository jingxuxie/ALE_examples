import collections
import json
from pathlib import Path
import random
import subprocess
import sys


assets = Path('/tmp/cascade-c2-g2-v2-d5teuwjq/participant')
deployment = json.loads((assets / 'input/deployment.json').read_text())
seed_info = list(map(int, Path('seed_found.txt').read_text().split()))
seed, offset = seed_info[:2]
mode = seed_info[2] if len(seed_info) > 2 else 0
sample = mode == 1
numpy_mode = mode >= 2
if numpy_mode:
    import numpy as np
    generator = np.random.RandomState(seed)
    draw32 = lambda: int(generator.randint(0, 2 ** 32, dtype=np.uint32))
    get_state = generator.get_state
    set_state = generator.set_state
else:
    generator = random.Random(seed)
    draw32 = lambda: generator.getrandbits(32)
    get_state = generator.getstate
    set_state = generator.setstate
for step in range(offset):
    draw32()
changed = collections.Counter()
for pass_index in range(1, 6):
    actual = deployment['passes'][pass_index]['permutation']
    if pass_index > 1:
        state = get_state()
        words = [draw32() for step in range(100000)]
        pattern = actual[:8] if sample else actual[-8:][::-1]
        match = None
        for position in range(len(words) - 12):
            first_value = words[position] & 8191 if numpy_mode else words[position] >> 18
            if first_value != pattern[0]:
                continue
            cursor = position + 1
            matched = 1
            while matched < 8:
                value = words[cursor] & 8191 if numpy_mode else words[cursor] >> 19
                cursor += 1
                if value >= 8192 - matched:
                    continue
                if value != pattern[matched]:
                    break
                matched += 1
            if matched == 8:
                match = position
                break
        if match is None:
            print('No next-pass match', pass_index, flush=True)
            break
        set_state(state)
        for step in range(match):
            draw32()
    if sample:
        raw = generator.sample(range(8192), 8192)
    else:
        raw = list(range(8192))
        generator.shuffle(raw)
    differences = {bit for bit, other in zip(actual, raw) if bit != other}
    print('Recovered pass', pass_index, 'differences', len(differences), flush=True)
    if len(differences) > 1000:
        break
    changed.update(differences)
pool = [bit for bit, frequency in changed.most_common()]
Path('recovered_pool.json').write_text(json.dumps(pool))
print('Pool', pool, flush=True)
if not pool:
    raise SystemExit('No repair differences recovered')
subprocess.run(['./projection', 'recovered_pool.json', '350', '8192', '9999'], check=True)
print('Recovery projection complete', flush=True)
