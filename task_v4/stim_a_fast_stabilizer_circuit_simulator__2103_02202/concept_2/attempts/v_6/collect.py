import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent.parent
model = json.loads((ROOT / 'participant/input/model.json').read_text())
columns = [int(value, 16) for value in model['columns']]
best = None
for path in OUT.rglob('*.json'):
    if not (path.name.startswith('candidate_') or 'witness' in path.name or path.name in ('exact.json', 'success.json', 'baseline_long.json')):
        continue
    try:
        artifact = json.loads(path.read_text())
        if type(artifact) is not dict or set(artifact) != {'faults'}:
            continue
        faults = artifact['faults']
        if type(faults) is not list or not faults or any(type(fault) is not int or not 0 <= fault < 512 for fault in faults) or len(set(faults)) != len(faults):
            continue
    except (OSError, ValueError):
        continue
    syndrome = 0
    logical = 0
    for fault in faults:
        syndrome ^= columns[fault]
        logical ^= model['observable'][fault]
    weight = len(faults)
    detector_weight = syndrome.bit_count()
    valid = weight <= 36 and detector_weight == 0 and logical == 1
    score = 1.0 if valid else 0.10 + 0.15 * min(1, 36 / weight) + 0.45 * (1 - detector_weight / 192) + 0.10 * logical
    rank = (valid, score, -weight, -detector_weight)
    if best is None or rank > best[0]:
        best = (rank, sorted(faults), {'source': str(path.relative_to(OUT)), 'valid': valid, 'score': score, 'weight': weight, 'detector_weight': detector_weight, 'logical_parity': logical})
if best is None:
    raise SystemExit('No well-formed nonempty candidate')
content = json.dumps({'faults': best[1]}, separators=(',', ':'))+'\n'
(OUT / 'selected_witness.json').write_text(content)
(OUT / 'witness.tmp').write_text(content)
(OUT / 'witness.tmp').replace(OUT / 'witness.json')
(OUT / 'selection.json').write_text(json.dumps(best[2], indent=2)+'\n')
print(json.dumps(best[2], sort_keys=True))
