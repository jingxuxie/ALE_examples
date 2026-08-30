import gzip
import json
import os
import sys
from pathlib import Path

source = Path(os.environ['P'])
sys.path.insert(0, str(source / 'workspace'))
from design_common import generate_supports, load_case

for scale in range(1, 4):
    case = load_case(source / f'input/scale_{scale}.json.gz')
    with open(f'case{scale}.txt', 'w') as stream:
        stream.write(f"{len(case['columns'])}\n")
        for cell, triple in zip(case['slot_cells'], case['columns']):
            stream.write(str(cell) + ' ' + ' '.join(f'{value:x}' for value in triple) + '\n')
    records = generate_supports(case, 731 + 37 * (scale - 1), 512)
    with open(f'check{scale}.txt', 'w') as stream:
        stream.write(f'{len(records)}\n')
        for record in records:
            stream.write(str(len(record['support'])) + ' ' + ' '.join(map(str, record['support'])) + '\n')
