import argparse
import ctypes
import json
import time
from pathlib import Path
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('--seconds', type=float, default=1500)
parser.add_argument('--start', type=int, default=0)
parser.add_argument('--stop', type=int, default=2000000)
parser.add_argument('--kind', type=str, default='pcg')
parser.add_argument('--methods', type=str, default='0,1,2,3')
parser.add_argument('--special-only', action='store_true')
parser.add_argument('--seed-file', type=str)
arguments = parser.parse_args()
root = Path(__file__).resolve().parent
expected = np.array(json.loads((root.parent.parent / 'participant/input/target.json').read_text())['cyclic_autocorrelation'], dtype=np.int64)
library = ctypes.CDLL(str(root / 'numpy_seeds.so'))
array_type = np.ctypeslib.ndpointer(dtype=np.int64, ndim=1, flags='C_CONTIGUOUS')
library.test_order.argtypes = [array_type, array_type, array_type, array_type]
library.consumed.argtypes = [array_type]
library.test_compressed.argtypes = [array_type, array_type, array_type]
candidate = np.zeros(4096, dtype=np.int64)
weights = np.r_[np.ones(512, dtype=np.int64), np.full(256, 2, dtype=np.int64)]
started = time.monotonic()
special = [1701, 1702, 8192, 4096, 180103219, 1801032, 1801, 3219, 314159, 271828, 8675309, 123456, 1234567, 12345678, 123456789, 314159265, 271828182, 2024, 2025, 2026, 20260101, 202601, 202602, 202603, 202604, 202605, 202606, 202607, 202608, 20250308, 20260828, 0xEEC, 0xEEC2025, 0xEEC2026, 0xEEC8192, 0xEEC4096, 20250319, 20260319]
special += [0xC0FFEE, 0xDEADBEEF, 0xBADC0DE, 0xBAD5EED, 0xCAFEBABE, 0xFEEDFACE, 0x180103219, 18013219, 20180109, 20180110, 20180321, 20260601, 20260615, 20260701, 20260801, 20260901, 2026011701, 202608281, 424242, 42424242, 31415926, 27182818, 987654321, 12345, 54321]
seeds = special + list(range(20200000, 20270000)) + list(range(arguments.start, arguments.stop))
if arguments.special_only: seeds = special
if arguments.seed_file: seeds = json.loads(Path(arguments.seed_file).read_text())
for seed in seeds:
    for method in map(int, arguments.methods.split(',')):
        if arguments.kind == 'mt' and seed >= 2**32: continue
        generator = np.random.default_rng(seed) if arguments.kind == 'pcg' else np.random.RandomState(seed)
        preweights = None
        if method >= 8:
            preweights = generator.permutation(weights)
            method -= 5
        initial_state = generator.bit_generator.state if arguments.kind == 'pcg' else generator.get_state()
        if method == 6 or method == 7:
            order = generator.permutation(3328) if method == 6 else generator.choice(3328, 3328, replace=False)
            if library.test_compressed(order, candidate, expected):
                (root / 'design.json').write_text(json.dumps({'schema_version': 1, 'a': candidate.tolist()}, separators=(',', ':')) + '\n')
                print('EXACT COMPRESSED', seed, method, arguments.kind, flush=True)
                raise SystemExit
            continue
        if method == 4 or method == 5:
            while True:
                support = np.sort(generator.choice(3328 if method == 4 else 3329, 768, replace=False)) + np.arange(768)
                if support[0] != 0 or support[-1] != 4095: break
            order = np.zeros(4096, dtype=np.int64)
            order[:768] = support
            saved_state = generator.bit_generator.state if arguments.kind == 'pcg' else generator.get_state()
            shuffled_weights = generator.permutation(weights)
        elif method == 3:
            order = generator.integers(0, 4096, size=4096, dtype=np.int64) if arguments.kind == 'pcg' else generator.randint(0, 4096, size=4096, dtype=np.int64)
            used = library.consumed(order)
            if arguments.kind == 'pcg': generator.bit_generator.state = initial_state
            else: generator.set_state(initial_state)
            if arguments.kind == 'pcg': generator.integers(0, 4096, size=used, dtype=np.int64)
            else: generator.randint(0, 4096, size=used, dtype=np.int64)
            saved_state = generator.bit_generator.state if arguments.kind == 'pcg' else generator.get_state()
            shuffled_weights = generator.permutation(weights)
        elif method == 2:
            shuffled_weights = generator.permutation(weights)
            order = generator.permutation(4096)
            saved_state = generator.bit_generator.state if arguments.kind == 'pcg' else generator.get_state()
        else:
            order = generator.permutation(4096) if method == 0 else generator.choice(4096, 4096, replace=False)
            saved_state = generator.bit_generator.state if arguments.kind == 'pcg' else generator.get_state()
            shuffled_weights = generator.permutation(weights)
        result = library.test_order(order, preweights if preweights is not None else shuffled_weights, candidate, expected)
        if result:
            (root / 'design.json').write_text(json.dumps({'schema_version': 1, 'a': candidate.tolist()}, separators=(',', ':')) + '\n')
            print('EXACT NUMPY', seed, method, result, arguments.kind, flush=True)
            raise SystemExit
        chosen_weights = np.ones(768, dtype=np.int64)
        if arguments.kind == 'pcg': generator.bit_generator.state = saved_state
        else: generator.set_state(saved_state)
        chosen_weights[generator.choice(768, 256, replace=False)] = 2
        result = library.test_order(order, chosen_weights, candidate, expected)
        if result:
            (root / 'design.json').write_text(json.dumps({'schema_version': 1, 'a': candidate.tolist()}, separators=(',', ':')) + '\n')
            print('EXACT NUMPY CHOICE', seed, method, result, arguments.kind, flush=True)
            raise SystemExit
    if seed % 10000 == 0:
        print('SEED', seed, 'SECONDS', time.monotonic() - started, arguments.kind, flush=True)
    if time.monotonic() - started > arguments.seconds:
        break
print('FINISHED', time.monotonic() - started, flush=True)
