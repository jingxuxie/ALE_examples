import json
from pathlib import Path

source = Path('../../participant/input/spec.json')
spec = json.loads(source.read_text())
for family in spec['families']:
    targets = family['targets']
    values = [family['id'], family['n'], family['max_rounds'], family['max_cx'],
              targets['min_single'], targets['min_double'],
              targets['mean_single_milli'], targets['mean_double_milli'], len(family['edges'])]
    lines = [' '.join(map(str, values))]
    lines += [' '.join(map(str, edge)) for edge in family['edges']]
    Path(family['id']+'.cfg').write_text('\n'.join(lines)+'\n')
