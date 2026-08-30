import json
import time
from pathlib import Path

root = Path('/tmp/cascade-c2-g2-v3-mirk7s27')
deployment = json.loads((root / 'participant/input/deployment.json').read_text())
started = time.monotonic()
for block_size in [4]:
    basis = {}
    for pass_index, specification in enumerate(deployment['passes']):
        permutation = specification['permutation']
        for start in range(0, 8192, block_size):
            row = sum(1 << position for position in permutation[start:start + block_size])
            while row:
                pivot = row.bit_length() - 1
                if pivot not in basis:
                    basis[pivot] = row
                    break
                row ^= basis[pivot]
        print('SIZE', block_size, 'PASS', pass_index, 'RANK', len(basis), 'SECONDS', time.monotonic() - started, flush=True)
    free = [position for position in range(8192) if position not in basis]
    for position in free:
        solution = 1 << position
        for pivot in sorted(basis):
            if (basis[pivot] & solution).bit_count() % 2:
                solution |= 1 << pivot
        errors = [position for position in range(8192) if solution >> position & 1]
        print('KERNEL', len(errors), errors[:30], flush=True)
        if 8 <= len(errors) <= 18:
            (root / 'attempts/v_3/subblock_core.json').write_text(json.dumps({'errors': errors}) + '\n')
