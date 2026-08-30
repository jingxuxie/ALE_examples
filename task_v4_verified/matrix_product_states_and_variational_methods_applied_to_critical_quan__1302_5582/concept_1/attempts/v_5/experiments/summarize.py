import json
from pathlib import Path

root = Path(__file__).resolve().parent
results = json.loads((root/'validation_results.json').read_text())
summary = dict(valid_runs=len(results), cases=len(results)//2,
    maximum_rss_bytes=max(result['max_rss_bytes'] for result in results),
    maximum_output_bytes=max(result['state_bytes'] for result in results),
    maximum_parity_error=max(abs(abs(result['parity'])-1) for result in results),
    budgets={})
for budget in [6, 40]:
    selected = [result for result in results if result['budget'] == budget]
    summary['budgets'][str(budget)] = dict(runs=len(selected),
        maximum_cpu_seconds=max(result['cpu_seconds'] for result in selected),
        maximum_wall_seconds=max(result['wall_seconds'] for result in selected))
summary['public_examples'] = []
for case in ['symmetric', 'odd', 'nonuniform']:
    baseline_lines = (root/('fast_original_'+case+'6.log')).read_text().splitlines()
    baseline = json.loads(next(line for line in reversed(baseline_lines) if line.startswith('RESULT ')).split(' ', 2)[2])
    short = next(result for result in results if result['case'] == case and result['budget'] == 6)
    long = next(result for result in results if result['case'] == case and result['budget'] == 40)
    summary['public_examples'].append(dict(case=case, baseline_short_energy=baseline['energy'],
        submitted_short_energy=short['energy'], submitted_long_energy=long['energy']))
summary['numerical_checks'] = json.loads((root/'checks_result.json').read_text())
summary['fallback_checks'] = json.loads((root/'fallback_checks_result.json').read_text())
(root/'summary.json').write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
