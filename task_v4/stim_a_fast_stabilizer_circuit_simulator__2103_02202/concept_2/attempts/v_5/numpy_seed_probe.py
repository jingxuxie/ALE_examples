import sys
import time
import numpy as np
from probe import COLUMNS


def main():
    first_seed = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    last_seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1000000
    columns = COLUMNS
    rows = [sum(((column >> row) & 1) << fault for fault, column in enumerate(columns)) for row in range(192)]
    targets = {(column >> shift) & ((1 << 64) - 1) for column in columns for shift in range(0, 192, 64)}
    targets.update((row >> shift) & ((1 << 64) - 1) for row in rows for shift in range(0, 512, 64))
    targets.update(int.from_bytes(value.to_bytes(8, 'little'), 'big') for value in list(targets))
    weights = [column.bit_count() for column in columns]
    started = time.monotonic()
    for seed in range(first_seed, last_seed):
        for generator_type in [np.random.PCG64, np.random.PCG64DXSM]:
            generator = generator_type(seed)
            values = generator.random_raw(36)
            if int(values[0]) in targets:
                print('RAW MATCH', generator_type.__name__, seed, int(values[0]), flush=True)
            mismatches = 0
            for fault in range(12):
                weight = int(values[fault * 3]).bit_count() + int(values[fault * 3 + 1]).bit_count() + int(values[fault * 3 + 2]).bit_count()
                mismatches += weight != weights[fault]
                if mismatches > 1:
                    break
            if mismatches <= 1:
                print('WEIGHT MATCH', generator_type.__name__, seed, mismatches, flush=True)
        if seed % 100000 == 0:
            print('progress', seed, time.monotonic() - started, flush=True)


if __name__ == '__main__':
    main()
