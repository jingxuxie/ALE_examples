import gzip
import json
import os
import struct
from pathlib import Path


source = Path(os.environ['P'])
for scale in range(1, 4):
    with gzip.open(source / f'input/scale_{scale}.json.gz', 'rt') as stream:
        case = json.load(stream)
    words = (max(int(value, 16).bit_length() for triple in case['columns'] for value in triple) + 63) // 64
    with open(f'case_{scale}.bin', 'wb') as stream:
        stream.write(struct.pack('II', len(case['columns']), words))
        for cell, triple in zip(case['slot_cells'], case['columns']):
            stream.write(struct.pack('I', cell))
            for value in triple:
                stream.write(int(value, 16).to_bytes(8 * words, 'little'))
