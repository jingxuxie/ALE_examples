import hashlib
import json
import sys
from pathlib import Path

ASSETS = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/t_ket_a_retargetable_compiler_for_nisq_devices__2003_10611/concept_2/adversary/generation_3/participant/input')
sys.path.insert(0, str(ASSETS))
from validation import load_witness, validate

choices = []
for directory in sorted(Path('.').glob('triangle_*')):
    for result_path in sorted(directory.glob('*_result.json')):
        result = json.loads(result_path.read_text())
        if not result.get('valid') or not result.get('passed'):
            continue
        source = result_path.with_name(result_path.name.replace('_result.json', '_checked.json'))
        if not source.exists():
            if result_path.name != 'seed_result.json':
                continue
            source = directory / 'seed.json'
        witness = load_witness(source)
        count, edges, gates, reference = validate(witness)
        assert reference == result['reference'] and len(gates) == result['gate_count']
        assert len(result['families']) == 6
        assert all(len(family['settings']) == 62 for family in result['families'])
        margin = min(min(family['swap_ratio'] / 2.5, family['native_ratio'] / 1.35,
                         family['swap_gap'] / 16) for family in result['families'])
        choices.append((margin, -reference['swaps'], -len(gates), source, result_path, result))
if not choices:
    raise RuntimeError('No fully verified passing candidate')
choices.sort(key=lambda choice: choice[:3], reverse=True)
margin, _, _, source, result_path, result = choices[0]
Path('witness.json').write_bytes(source.read_bytes())
Path('selected_result.json').write_bytes(result_path.read_bytes())
summary = {
    'source': str(source),
    'result_source': str(result_path),
    'sha256': hashlib.sha256(Path('witness.json').read_bytes()).hexdigest(),
    'minimum_normalized_margin': margin,
    'reference': result['reference'],
    'gate_count': result['gate_count'],
    'minimum_portfolio_swaps': min(family['portfolio_swaps'] for family in result['families']),
    'minimum_swap_ratio': min(family['swap_ratio'] for family in result['families']),
    'minimum_native_ratio': min(family['native_ratio'] for family in result['families']),
    'minimum_swap_gap': min(family['swap_gap'] for family in result['families']),
    'passed': result['passed'],
}
Path('submission_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
for family in result['families']:
    print(family['name'], family['portfolio_swaps'], family['best_setting'])
