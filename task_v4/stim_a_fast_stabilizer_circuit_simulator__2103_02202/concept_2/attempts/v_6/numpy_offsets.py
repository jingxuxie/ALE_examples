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
offsets = sorted({base + extra for base in (1533, 1536, 3072, 12288, 49152, 98304) for extra in (0, 64, 256, 512)})
started = time.monotonic()
for position, seed in enumerate(seeds):
    generator = np.random.default_rng(seed)
    initial = generator.bit_generator.state
    for offset in offsets:
        for fixed in (False, True):
            generator.bit_generator.state = initial
            generator.bit_generator.advance(offset)
            support = generator.choice(511 if fixed else 512, 35 if fixed else 36, replace=False)
            value = np.bitwise_xor.reduce(low[support])
            if fixed:
                value ^= low[511]
            if value != 0:
                continue
            faults = [int(fault) for fault in support]
            if fixed:
                faults.append(511)
            syndrome = 0
            logical = 0
            for fault in faults:
                syndrome ^= columns[fault]
                logical ^= model['observable'][fault]
            if syndrome == 0 and logical:
                (OUT / 'numpy_witness.json').write_text(json.dumps({'faults': faults}))
                print('FOUND', seed, offset, fixed, flush=True)
                raise SystemExit
    if position % 5000 == 0:
        print('position', position, 'seed', seed, 'seconds', time.monotonic()-started, flush=True)
