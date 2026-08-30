import os
import sys
from pathlib import Path

participant = Path(os.environ['P'])
sys.path.insert(0, str(participant / 'workspace'))
from design_common import generate_supports, load_case

case = load_case(participant / 'input/scale_1.json.gz')
records = generate_supports(case, 942617, 32)
with open('public_search.txt', 'w') as stream:
    stream.write(str(len(records)) + '\n')
    for record in records:
        support = record['support']
        stream.write(str(len(support)) + ' ' + ' '.join(map(str, support)) + '\n')
