import json
from pathlib import Path
from validate import validate

path = Path('submission/witness.json')
witness = json.loads(path.read_text())
cases = json.loads(Path('dev/instances.json').read_text())['instances']
for case in cases:
    candidates = [(path, witness['circuits'][case['id']])]
    for extension in ('gates', 'optimized', 'local', 'satlocal', 'beam', 'satgates', 'global', 'hot', 'layers', 'population', 'scheduled', 'structural', 'balanced'):
        candidate = Path('dev') / (case['id'] + '.' + extension)
        if candidate.exists():
            gates = [list(map(int, line.split())) for line in candidate.read_text().splitlines()]
            candidates.append((candidate, gates))
    best = None
    for source, gates in candidates:
        result = validate(case, gates)
        if not result['valid']:
            raise ValueError((source, result))
        efficiency = (min(1, case['max_cnots'] / max(1, len(gates))) +
                      min(1, case['max_depth'] / max(1, result['depth']))) / 2
        rank = (result['passed'], efficiency, -result['depth'], -len(gates))
        if best is None or rank > best[0]:
            best = (rank, source, gates, result)
    witness['circuits'][case['id']] = best[2]
    print(best[1], best[3]['count'], best[3]['depth'], 'PASS' if best[3]['passed'] else 'over budget')
temporary = path.with_suffix('.json.tmp')
temporary.write_text(json.dumps(witness, separators=(',', ':')) + '\n')
temporary.replace(path)
