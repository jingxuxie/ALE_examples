import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
PARTS = ['serial', 'conditional_forward64', 'heldout_forward64', 'heldout_reverse64']


def main():
    merged = {}
    for part in PARTS:
        if part != 'serial' and (HERE / f'refinement_audit_{part}.exit').read_text().strip() != '0':
            raise AssertionError(f'Refinement worker failed: {part}')
        for record in json.loads((HERE / f'refinement_audit_{part}.json').read_text()):
            key = record['pool'], record['id']
            if key in merged:
                raise AssertionError(f'Duplicate refinement: {key}')
            merged[key] = record
    records = list(merged.values())
    if len(records) != 10:
        raise AssertionError(f'Expected 10 transport references, found {len(records)}')
    (HERE / 'refinement_audit.json').write_text(json.dumps(records, indent=2) + '\n')
    (HERE / 'refinement_audit_execution.json').write_text(json.dumps({
        'status': 'complete', 'completed_cases': len(records),
        'serial_cases': 7, 'parallel_cases': 3,
        'serial_interruption': 'Author intentionally interrupted remaining serial computation to parallelize independent cases; seven completed records preserved',
        'parallel_cores': {'conditional_forward64': [88, 89, 90, 91],
                           'heldout_forward64': [92, 93, 94, 95],
                           'heldout_reverse64': [96, 97, 98, 99]},
        'scoring_changed': False, 'integration_arithmetic_changed': False,
    }, indent=2) + '\n')
    print(f'Merged {len(records)} independent transport refinement records')


if __name__ == '__main__':
    main()
