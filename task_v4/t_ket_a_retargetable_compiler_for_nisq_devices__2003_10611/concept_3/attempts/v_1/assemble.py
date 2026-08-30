import importlib.util
import json
from pathlib import Path

from common import CASES, verify, write_witness


circuits = {}
reports = []
for case in CASES:
    candidates = []
    for path in Path('.').glob('*_' + case['id'] + '.txt'):
        try:
            gates = [list(map(int, line.split())) for line in path.read_text().splitlines()]
            report = verify(case, gates)
        except Exception:
            continue
        if report['exact'] and not report['missing']:
            count_ratio = report['count'] / case['max_cnots']
            depth_ratio = report['depth'] / case['max_depth']
            score = max(count_ratio, depth_ratio) + 0.001 * (count_ratio + depth_ratio)
            candidates.append((score, str(path), gates, report))
    if not candidates:
        source = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/t_ket_a_retargetable_compiler_for_nisq_devices__2003_10611/concept_3/participant/baseline/synthesize.py')
        spec = importlib.util.spec_from_file_location('baseline', source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        gates = module.synthesize_case(case)
        candidates.append((1e9, 'baseline', gates, verify(case, gates)))
    score, source, gates, report = min(candidates)
    circuits[case['id']] = gates
    report['source'] = source
    reports.append(report)
    print(case['id'], source, report['count'], report['depth'], report['passed'])
write_witness(circuits)
Path('validation.json').write_text(json.dumps(reports, indent=2) + '\n')
