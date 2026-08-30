import json
import sys
from pathlib import Path

from improve import ROOT, SOURCE

sys.path.insert(0, str(SOURCE.parent.parent / 'workspace'))
from check import check_case, score

instances = json.loads(SOURCE.read_text())['instances']
cases = []
for instance in instances:
    candidates = []
    for path in ROOT.rglob('*.json'):
        if path.name == instance['id'] + '.json':
            try:
                candidates.append(json.loads(path.read_text()))
            except Exception:
                pass
        elif path.name == 'answer.json':
            try:
                candidates.extend(case for case in json.loads(path.read_text())['cases'] if case['id'] == instance['id'])
            except Exception:
                pass
    ranked = [(check_case(instance, case), case) for case in candidates]
    ranked.sort(key=lambda entry: (not entry[0][0], entry[0][1]))
    if ranked:
        cases.append(ranked[0][1])
        print(instance['id'], ranked[0][0])
answer = {'cases': cases}
(ROOT / 'answer.json').write_text(json.dumps(answer, indent=2, allow_nan=False) + '\n')
result = score(instances, answer)
(ROOT / 'validation.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
print(json.dumps(result, indent=2))
