import os
import sys
from pathlib import Path


sys.path.insert(0, os.environ['P'] + '/workspace')
from design_common import generate_supports, load_case


case = load_case(Path(os.environ['P']) / 'input/scale_1.json.gz')
records = generate_supports(case, 1492039, 256, {'dense_iid': [.32]})
with open('public_256.bin', 'wb') as stream:
    for record in records:
        flags = bytearray(24)
        for slot in record['support']:
            flags[slot % 24] |= 1 << (slot // 24)
        stream.write(flags)

records = generate_supports(case, 39280517, 64, {'dense_iid': [.28, .30, .32]})
with open('public_mixed_192.bin', 'wb') as stream:
    for record in records:
        flags = bytearray(24)
        for slot in record['support']:
            flags[slot % 24] |= 1 << (slot // 24)
        stream.write(flags)
