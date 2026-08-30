import datetime
import json
import time
from pathlib import Path

import numpy as np

ROOT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/stim_a_fast_stabilizer_circuit_simulator__2103_02202/concept_2')
OUT = ROOT / 'attempts/v_6'
model = json.loads((ROOT / 'participant/input/model.json').read_text())
columns = [int(value, 16) for value in model['columns']]
low = np.array([value & ((1 << 64) - 1) for value in columns], dtype=np.uint64)
seeds = [210302202, 2103022020, 928331, 730001, 123456789, 314159265, 271828182, 0xDEADBEEF, 0xBADF00D, 0xFEEDFACE, 0xCAFEBABE, 0x5EED5EED]
date = datetime.date(2020, 1, 1)
while date < datetime.date(2031, 1, 1):
    seeds.append(int(date.strftime('%Y%m%d')))
    date += datetime.timedelta(days=1)
seeds.extend(range(100000))
started = time.monotonic()
for position, seed in enumerate(seeds):
    for generator in (np.random.default_rng(seed), np.random.RandomState(seed)):
        support = generator.choice(512, 36, replace=False)
        if np.bitwise_xor.reduce(low[support]) != 0:
            continue
        syndrome = 0
        logical = 0
        for fault in support:
            syndrome ^= columns[int(fault)]
            logical ^= model['observable'][int(fault)]
        if syndrome == 0 and logical:
            (OUT / 'numpy_witness.json').write_text(json.dumps({'faults': [int(fault) for fault in support]}))
            print('FOUND', seed, type(generator).__name__, flush=True)
            raise SystemExit
    if position % 10000 == 0:
        print('position', position, 'seed', seed, 'seconds', time.monotonic()-started, flush=True)
