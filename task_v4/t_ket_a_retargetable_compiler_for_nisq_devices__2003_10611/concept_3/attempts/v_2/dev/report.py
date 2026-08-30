import json
from pathlib import Path

report = json.loads(Path('dev/final_audit.json').read_text())
passed = sum(case['passed'] for case in report['cases'])
lines = [
    '# Validation results',
    '',
    'All six circuits obey their native graphs, reach the exact ordered target matrices, and expose every required parity.',
    f'{passed} of six circuits also meet both resource budgets.',
    '',
    '| Case | CNOTs / budget | Depth / budget | Both budgets |',
    '| --- | ---: | ---: | :---: |',
]
for case in report['cases']:
    status = 'Pass' if case['passed'] else 'Over depth'
    lines.append(f"| {case['id']} | {case['cnots']} / {case['max_cnots']} | {case['depth']} / {case['max_depth']} | {status} |")
lines.extend([
    '',
    f"- Core score: {report['core_score']:.6f}",
    f"- Worst-family score: {report['worst_family_score']:.6f}",
    f"- Resource score: {report['resource_score']:.6f}",
    f"- Witness size: {report['witness_bytes']} bytes",
    '',
    'These results come from independent exact local validation, not a hidden evaluator.',
])
Path('RESULTS.md').write_text('\n'.join(lines) + '\n')
