import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONCEPT = ROOT / 'concept_01'
SCREEN = CONCEPT / 'screening' / 'v_01'


def main():
    evaluation = json.loads((SCREEN / 'evaluation.json').read_text())
    runtime = json.loads((SCREEN / 'runtime.json').read_text())
    reference = json.loads((CONCEPT / 'screening' / 'reference_evaluation.json').read_text())
    transcript = (SCREEN / 'transcript.txt').read_text()
    assert evaluation['status'] == reference['status'] == 'ok'
    assert evaluation['core_score'] >= 0.90
    assert runtime['returncode'] == 0 and not runtime['timed_out']
    assert runtime['participant_sha256_before'] == runtime['participant_sha256_after']
    session = re.search(r'session id: ([a-f0-9-]+)', transcript)
    tokens = re.search(r'tokens used\s*\n([\d,]+)', transcript)
    attempt = {
        'model': runtime['model'],
        'reasoning_effort': runtime['reasoning_effort'],
        'session_id': session.group(1) if session else None,
        'runtime_seconds': runtime['runtime_seconds'],
        'time_limit_seconds': runtime['time_limit_seconds'],
        'timed_out': runtime['timed_out'],
        'returncode': runtime['returncode'],
        'tokens_reported': int(tokens.group(1).replace(',', '')) if tokens else None,
        'overall_score': evaluation['score'],
        'core_score': evaluation['core_score'],
        'per_family_score': {name: result['accuracy'] for name, result in evaluation['families'].items()},
        'per_family_resources': {
            name: {'seconds': result['total_seconds'], 'peak_rss_mb': result['max_peak_rss_mb']}
            for name, result in evaluation['families'].items()
        },
        'efficiency_score': evaluation['efficiency_score'],
        'evidence_score': evaluation['evidence_score'],
        'failure_classification': 'no_substantial_core_failure',
        'difficulty_classification': 'too_easy',
        'valid_for_core_screen': True,
        'participant_inputs_unchanged': True,
        'output_directory': str(CONCEPT / 'attempts' / 'v_01'),
        'transcript': str(SCREEN / 'transcript.txt'),
        'evaluator_json': str(SCREEN / 'evaluation.json'),
        'artifact_audit_note': 'Raw evidence deductions include supplementary-table and figure-source-schema limitations; none are treated as scientific failures or hardness evidence.',
    }
    (SCREEN / 'assessment.json').write_text(json.dumps(attempt, indent=2) + '\n')
    reference_summary = {
        'overall_score': reference['score'], 'core_score': reference['core_score'],
        'evidence_score': reference['evidence_score'],
        'per_family_score': {name: result['accuracy'] for name, result in reference['families'].items()},
        'evaluation': str(CONCEPT / 'screening' / 'reference_evaluation.json'),
        'qualification': str(CONCEPT / 'screening' / 'reference_validation.json'),
    }
    concept_status = {
        'status': 'rejected',
        'reason': 'fresh_agent_core_score_at_least_0_90',
        'concept': 'Release audit of a correlated-noise quantum process predictor',
        'archetype': 'A_real_workspace_diagnosis_repair_performance_validation',
        'version': 'v_01',
        'participant_directory': str(CONCEPT / 'participant' / 'v_01'),
        'reference': reference_summary,
        'attempts': [attempt],
        'fundamental_redesigns': 0,
        'post_screen_hidden_case_changes': 0,
        'post_screen_threshold_changes': 0,
        'retained_as_frontier_hard': False,
    }
    (CONCEPT / 'status.json').write_text(json.dumps(concept_status, indent=2) + '\n')
    status = {
        'paper': 'Filter Function Formalism and Software Package to Compute Quantum Processes of Gate Sequences for Classical Non-Markovian Noise',
        'arxiv': '2103.02403',
        'status': 'rejected',
        'reason': 'paper_did_not_yield_frontier_hard_task',
        'selected_task': None,
        'screened_concept': 'concept_01',
        'candidate_concepts_considered': 5,
        'built_concepts': 1,
        'screened_concepts': 1,
        'remaining_prebuild_rejections': 4,
        'fundamental_redesigns': 0,
        'reference': reference_summary,
        'attempts': [attempt],
        'stop_rationale': 'The screened task was solved. No genuinely different remaining concept passed both central-paper and standard-shortcut gates; a second built pilot would knowingly violate those gates. No additional spectral cases, dimensions, thresholds, or formats were added to the rejected concept.',
    }
    (ROOT / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    record = CONCEPT / 'attempts' / 'v_01' / '_screen_record'
    record.mkdir(exist_ok=True)
    for name in ('transcript.txt', 'runtime.json', 'evaluation.json', 'assessment.json'):
        shutil.copy2(SCREEN / name, record / name)
    print(json.dumps({'status': status['status'], 'core_score': evaluation['core_score'],
                      'overall_score': evaluation['score'], 'runtime_seconds': runtime['runtime_seconds']}, indent=2))


if __name__ == '__main__':
    main()
