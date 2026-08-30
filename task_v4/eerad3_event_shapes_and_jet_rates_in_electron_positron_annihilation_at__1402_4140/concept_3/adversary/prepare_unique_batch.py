from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'adversary'))
from conditioned_cases import make_cases, validate_case
from prepare_generation_2 import digest, put


def main():
    destination = ROOT / 'adversary/unique_production_batch'
    if destination.exists():
        raise RuntimeError('Unique production batch already exists; refusing overwrite')
    cases = json.loads((ROOT / 'evaluator/hidden/cases.json').read_text())
    references = json.loads((ROOT / 'evaluator/hidden/references.json').read_text())
    assert len(cases) == len(references) == 1724
    prefix_cases, prefix_references = list(cases), list(references)
    new_cases = make_cases(seed=354732819, samples=920)
    diagnostics = []
    for index, case in enumerate(new_cases):
        case['id'] = 'production-' + case['id']
        reference, diagnostic = validate_case(case)
        cases.append(case)
        references.append(reference)
        diagnostics.append(diagnostic)
        if (index + 1) % 500 == 0:
            print('unique production references validated', index + 1, flush=True)
    identities = {json.dumps([case['p'], case['labels'], case['slots'], case['axis']], separators=(',', ':')) for case in cases}
    physical_inputs = {json.dumps(case['p'], separators=(',', ':')) for case in cases}
    assert len(cases) == len(references) == len(identities) == len(physical_inputs) == 10004
    assert cases[:1724] == prefix_cases and references[:1724] == prefix_references
    put(destination / 'cases.json', cases)
    put(destination / 'references.json', references)
    put(destination / 'validation.json', {
        'case_count': len(cases), 'distinct_full_inputs': len(identities),
        'distinct_momentum_inputs': len(physical_inputs), 'preserved_prefix_count': 1724,
        'new_seed': 354732819, 'new_samples_per_family': 920,
        'family_counts': dict(Counter(case['family'] for case in cases)),
        'case_sha256': digest(destination / 'cases.json'), 'reference_sha256': digest(destination / 'references.json'),
        'methods': ['geometric at 140 and 190 digits', 'direct DAK at 160 digits', 'rest-frame sphere at 180 digits'],
        'max_new_reference_disagreement': max(item['oracle_disagreement'] for item in diagnostics),
        'max_new_input_cm_residual': max(item['input_cm_residual'] for item in diagnostics),
        'max_new_input_null_residual': max(item['input_null_residual'] for item in diagnostics),
        'max_new_rest_frame_shell_residual': max(item['rest_frame_shell_residual'] for item in diagnostics),
        'selection': 'All generated events retained; no performance-based rejection sampling.'})
    print('unique production batch ready:', len(cases), flush=True)


if __name__ == '__main__':
    main()
