import json
import os
from pathlib import Path
import sys

participant = Path(os.environ['P'])
sys.path.insert(0, str(participant / 'workspace'))
import checker

suite = json.load(open(participant / 'input/instances.json'))
solution = json.load(open('solution.json'))
for target in suite['targets']:
    name = target['name']
    best_gates = solution['circuits'][name]
    report = checker.score_target(target, best_gates)
    best_quality = (not report['solved'], max(report['cx_count']/target['max_cx'], report['weighted_depth']/target['max_weighted_depth']), report['cx_count']+report['weighted_depth'])
    best_path = 'solution.json'
    for path in Path('.').glob(name + '_*.txt'):
        try:
            gates = [list(map(int, line.split())) for line in path.read_text().splitlines()[1:]]
            report = checker.score_target(target, gates)
            if not report['correct']:
                continue
            quality = (not report['solved'], max(report['cx_count']/target['max_cx'], report['weighted_depth']/target['max_weighted_depth']), report['cx_count']+report['weighted_depth'])
        except (ValueError, checker.ContractError, IndexError):
            continue
        if quality < best_quality:
            best_quality, best_gates, best_path = quality, gates, str(path)
    solution['circuits'][name] = best_gates
    result = checker.score_target(target, best_gates)
    print(name, best_path, result['cx_count'], result['weighted_depth'], 'PASS' if result['solved'] else 'pending')
Path('solution.json').write_text(json.dumps(solution, separators=(',', ':')) + '\n', encoding='utf-8')
report = checker.evaluate_document(solution, suite)
Path('validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('passed', report['passed'])
