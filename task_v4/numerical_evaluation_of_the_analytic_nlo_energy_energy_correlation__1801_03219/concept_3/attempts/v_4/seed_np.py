import argparse
import ctypes
import json
from pathlib import Path
import time

import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('--mode',type=int,default=0)
parser.add_argument('--engine',type=int,default=0)
parser.add_argument('--start',type=int,default=0)
parser.add_argument('--stop',type=int,default=100000)
parser.add_argument('--batch',action='store_true')
arguments = parser.parse_args()
root = Path(__file__).resolve().parent
library = ctypes.CDLL(str(root/'seedlib.so'))
array_type = np.ctypeslib.ndpointer(dtype=np.int64,ndim=1,flags='C_CONTIGUOUS')
library.select_support.argtypes = [array_type,array_type,ctypes.c_int]
library.test_support.argtypes = [array_type,array_type,array_type]
library.test_support.restype = ctypes.c_bool
positions = np.empty(768,dtype=np.int64)
weights_base = np.repeat(np.array([1,2],dtype=np.int64),[512,256])
result = np.zeros(4096,dtype=np.int64)
increments = np.arange(768,dtype=np.int64)
started = time.monotonic()
base_mode = arguments.mode % 5
seeds = range(arguments.start,arguments.stop)
if arguments.batch:
    import itertools
    special = [int(value) for value in (root/'special_seeds.txt').read_text().split()]
    if arguments.engine:
        special = [value for value in special if value < 2**32]
    seeds = itertools.chain(special,range(20200101,20270101),seeds)
for seed in seeds:
    generator = np.random.default_rng(seed) if not arguments.engine else np.random.RandomState(seed)
    initial_weights = weights_base.copy()
    if arguments.mode >= 10:
        if arguments.mode in range(15,20) or arguments.mode >= 25:
            initial_weights = initial_weights[::-1].copy()
        generator.shuffle(initial_weights)
    if base_mode == 0:
        positions[0] = 0
        positions[1:] = np.sort(generator.choice(3327,767,replace=False)) + increments[1:] + 1
    elif base_mode == 1:
        positions[:] = np.sort(generator.choice(3328,768,replace=False)) + increments
    elif base_mode == 2:
        ordering = generator.permutation(4096).astype(np.int64)
        library.select_support(ordering,positions,len(ordering))
    elif base_mode == 3:
        ordering = generator.choice(4096,4096,replace=False).astype(np.int64)
        library.select_support(ordering,positions,len(ordering))
    elif base_mode == 4:
        state = generator.bit_generator.state if not arguments.engine else generator.get_state()
        integers = generator.integers if not arguments.engine else generator.randint
        ordering = integers(4096,size=4096).astype(np.int64)
        consumed = library.select_support(ordering,positions,len(ordering))
        if consumed < 0:
            continue
        if not arguments.engine:
            generator.bit_generator.state = state
        else:
            generator.set_state(state)
        integers(4096,size=consumed)
    state = generator.bit_generator.state if not arguments.engine else generator.get_state()
    if arguments.mode in range(5,10) or arguments.mode >= 20:
        positions.sort()
    for label_mode in range(1 if arguments.mode >= 10 else 8):
        if not arguments.engine:
            generator.bit_generator.state = state
        else:
            generator.set_state(state)
        weights = weights_base.copy()
        if label_mode == 1:
            weights = weights[::-1].copy()
        if label_mode < 2:
            generator.shuffle(weights)
        elif label_mode == 2:
            weights.fill(1)
            weights[generator.choice(768,256,replace=False)] = 2
        elif label_mode == 3:
            weights.fill(1)
            weights[generator.permutation(768)[:256]] = 2
        elif label_mode == 4:
            weights.fill(2)
            weights[generator.choice(768,512,replace=False)] = 1
        elif label_mode == 6:
            weights = weights[::-1].copy()
        elif label_mode == 7:
            weights.fill(1)
            weights[generator.permutation(768)[-256:]] = 2
        if arguments.mode >= 10:
            weights = initial_weights
        if library.test_support(positions,weights,result):
            candidate = root/f'np_candidate_{arguments.engine}_{arguments.mode}.json'
            candidate.write_text(json.dumps({'schema_version':1,'a':result.tolist()}))
            print('MATCH',seed,arguments.engine,arguments.mode,label_mode,flush=True)
            raise SystemExit
    if seed % 10000 == 0:
        print(seed,round(time.monotonic()-started,2),flush=True)
