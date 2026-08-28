import hashlib
import json
import math
from pathlib import Path

from run_pilots import snapshot


ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = ['01_local_recovery', '02_biased_pauli', '03_analog_memory', '04_circuit_compiler']


def load_json(path):
    return json.loads(path.read_text())


def main():
    records = []
    for concept in CONCEPTS:
        pilot = ROOT / 'pilots' / concept
        metadata_path = ROOT / 'research/runs/tournament' / (concept + '.metadata.json')
        report_path = ROOT / 'research/scores/tournament' / (concept + '.json')
        summary_path = ROOT / 'research/scores/tournament' / (concept + '.summary.json')
        metadata = load_json(metadata_path)
        report = load_json(report_path)
        summary = load_json(summary_path)
        participant_hashes = snapshot(pilot / 'participant')
        submission_hashes = snapshot(pilot / 'attempt')
        required_paths = ['participant/TASK.md', 'participant/input', 'participant/workspace',
                          'private/reference', 'private/challenge_pool', 'private/evaluator.py', 'attempt']
        checks = {
            'complete_minimal_layout': all((pilot / path).exists() for path in required_paths),
            'requested_model': metadata['model_requested'] == 'ultima-alpha',
            'one_hour_limit': metadata['time_limit_seconds'] == 3600,
            'finished_within_limit': metadata['elapsed_seconds'] <= 3600,
            'model_exit_success': metadata['returncode'] == 0,
            'submitted_solver': metadata['submitted_solver'],
            'participant_unchanged': participant_hashes == metadata['participant_sha256_before']
                == metadata['participant_sha256_after'],
            'submission_unchanged_since_model_exit': submission_hashes == metadata['submission_sha256'],
            'evaluator_exit_success': summary['evaluator_returncode'] == 0,
            'finite_core_scores': all(math.isfinite(report[key]) for key in ['mean_core', 'worst_family']),
            'summary_matches_report': all(summary[key] == report[key] for key in ['mean_core', 'worst_family']),
            'paper_not_named_in_mission': '2005.07016' not in (pilot / 'participant/TASK.md').read_text()
                and 'decoding across the quantum ldpc code landscape' not in (pilot / 'participant/TASK.md').read_text().lower(),
        }
        record = {
            'concept': concept,
            'passed': all(checks.values()),
            'checks': checks,
            'participant_file_count': len(participant_hashes),
            'submission_file_count': len(submission_hashes),
            'model_elapsed_seconds': metadata['elapsed_seconds'],
            'mean_core': report['mean_core'],
            'worst_family': report['worst_family'],
            'metadata_sha256': hashlib.sha256(metadata_path.read_bytes()).hexdigest(),
            'report_sha256': hashlib.sha256(report_path.read_bytes()).hexdigest(),
        }
        if not checks['submission_unchanged_since_model_exit']:
            recorded = metadata['submission_sha256']
            record['submission_differences'] = sorted(name for name in set(recorded) | set(submission_hashes)
                                                    if recorded.get(name) != submission_hashes.get(name))
        records.append(record)
    result = {
        'schema_version': 1,
        'passed': all(record['passed'] for record in records),
        'scored_fresh_attempts': len(records),
        'records': records,
        'initial_hardness_screening_order': [record['concept'] for record in
            sorted(records, key=lambda record: (record['worst_family'], record['mean_core']))],
        'screening_order_is_not_acceptance': True,
    }
    path = ROOT / 'research/scores/final_integrity.json'
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({key: result[key] for key in ['passed', 'scored_fresh_attempts',
                                                   'initial_hardness_screening_order']}))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
