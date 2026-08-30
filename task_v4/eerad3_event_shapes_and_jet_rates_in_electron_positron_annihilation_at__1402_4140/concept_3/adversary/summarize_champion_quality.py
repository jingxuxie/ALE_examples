from datetime import datetime, timezone
import json
from pathlib import Path
import time

import numpy as np

from search_champion_quality import DEADLINE, DESTINATION, ROOT, error_ratios
from conditioned_cases import validate_case
from oracle import check, geometric, dak_crosscheck
from prepare_generation_2 import put


def main():
    target = json.loads((ROOT / 'adversary/generation_1_snapshot/evaluator/hidden/target.json').read_text())
    report = {'quality_only': True, 'checked': 0, 'failures': [], 'independent_reference_checks': [],
              'largest_component_ratio': 0, 'largest_gate_ratio': 0, 'families': {},
              'deadline_utc': '2026-08-28T13:37:40+00:00'}
    datasets = []
    for seed in [98324761, 98324762]:
        cases = json.loads((DESTINATION / f'cases_{seed}.json').read_text())
        records = np.load(DESTINATION / f'records_{seed}.npy')
        datasets.append((cases, records))
        for index in [0, 1, 2, 99, 299]:
            reference, properties = validate_case(cases[index])
            higher = geometric(cases[index], 240)
            direct = dak_crosscheck(cases[index], 220)
            energy = sum(vector[3] for vector in cases[index]['p'])
            disagreement = max(float(np.max(np.abs(np.asarray(reference['mapped']) - higher['mapped'])) / energy),
                float(np.max(np.abs(np.asarray(reference['mapped'])[cases[index]['slots'][0] - 1] - direct)) / energy))
            properties['higher_precision_disagreement'] = disagreement
            properties['id'] = cases[index]['id']
            properties['errors'] = check(cases[index], reference, records[index], target)
            properties['ratios'] = error_ratios(cases[index], reference, records[index], target)
            report['independent_reference_checks'].append(properties)
    for index in list(range(300)) + list(range(300, 6000)):
        if time.time() > DEADLINE - 5:
            break
        for cases, records in datasets:
            case = cases[index]
            reference = geometric(case, 190)
            errors = check(case, reference, records[index], target)
            ratios = error_ratios(case, reference, records[index], target)
            report['checked'] += 1
            family = report['families'].setdefault(case['family'], {'checked': 0, 'failures': 0, 'largest_component_ratio': 0})
            family['checked'] += 1
            family['failures'] += bool(errors)
            family['largest_component_ratio'] = max(family['largest_component_ratio'], ratios.get('component_ratio', 0))
            report['largest_component_ratio'] = max(report['largest_component_ratio'], ratios.get('component_ratio', 0))
            gate_ratio = max((value for name, value in ratios.items() if name.endswith('_ratio')), default=0)
            if gate_ratio > report['largest_gate_ratio']:
                report['largest_gate_ratio'] = gate_ratio
                report['largest_gate_case'] = case['id']
                report['largest_gate_errors'] = errors
                report['largest_gate_details'] = ratios
            if errors:
                report['failures'].append({'id': case['id'], 'errors': errors, 'ratios': ratios})
            if errors and (ratios['nonfinite'] or gate_ratio > 2):
                confirmed, properties = validate_case(case)
                put(DESTINATION / 'additional_witness.json', {'case': case, 'reference': confirmed,
                    'record': records[index].tolist(), 'errors': errors, 'ratios': ratios, 'properties': properties})
    report['finished_utc'] = datetime.now(timezone.utc).isoformat()
    report['no_robust_quality_ratchet_found'] = not (DESTINATION / 'additional_witness.json').exists()
    put(DESTINATION / 'reference_summary.json', report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
