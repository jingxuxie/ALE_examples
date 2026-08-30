import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCORE_KEYS = ['core_score', 'worst_family_score', 'runtime_score', 'log_rmse',
              'worst_family_log_rmse', 'within_relative_tolerance', 'relative_error_tolerance',
              'cpu_seconds', 'cpu_budget_seconds', 'runtime_ratio', 'runtime_ratio_limit',
              'failed_case_count', 'y45_ratio', 'max_shape_error', 'passed', 'valid', 'reason']
FINAL_STATUSES = ['solved', 'hard_open_candidate', 'hard_verified_achievable', 'invalid', 'rejected']
MODES = {'B': 'counterexample or falsification', 'D': 'hidden prediction', 'F': 'workspace repair'}


def read(path):
    return json.loads(path.read_text())


def score_fields(score):
    return {name: score[name] for name in SCORE_KEYS if name in score}


def main():
    audit = read(ROOT / 'research/package_audit.json')
    assert audit['all_started_sessions_distinct']
    assert audit['all_finished_runs_valid']
    assert audit['all_packages_integral']
    concepts = []
    for number in range(1, 4):
        concept = ROOT / f'concept_{number}'
        status = read(concept / 'status.json')
        assert status['status'] in FINAL_STATUSES
        generation_scores = []
        for path in sorted((concept / 'adversary').glob('frozen_generation_*.json')):
            frozen = read(path)
            before = frozen['status_at_freeze']
            record = {'generation': frozen['generation'], 'baseline_champion_scores': {}}
            for name in ['baseline_score', 'public_baseline_score', 'private_incumbent_score',
                         'incumbent_score', 'privileged_score']:
                if isinstance(before.get(name), dict):
                    record['baseline_champion_scores'][name] = score_fields(before[name])
            if number == 1 and frozen['generation'] == 2:
                record['baseline_champion_scores']['public_baseline_score'] = score_fields(
                    read(concept / 'adversary/generation_2_weak_baseline_score.json'))
            generation_scores.append(record)
        fresh = []
        for path in sorted((concept / 'attempts').glob('v_*.run.json')):
            run = read(path)
            evaluation = concept / 'attempts' / f"v_{run['attempt']}.evaluation.json"
            assert run['status'] != 'running' and evaluation.is_file()
            fresh.append({'attempt': run['attempt'], 'generation': run['generation'],
                          'model': run['model'], 'authoring_seconds': run['wall_seconds'],
                          'participant_unchanged': run['participant_unchanged'],
                          'score': score_fields(read(evaluation))})
            audit = concept / 'attempts' / f"v_{run['attempt']}.audit_evaluation.json"
            if audit.is_file():
                fresh[-1]['audited_score'] = score_fields(read(audit))
        if status.get('audited_release_scores'):
            generation_scores.append({'generation': status['generation'],
                                      'instrumentation_audit': True,
                                      'baseline_champion_scores': {
                                          name: score_fields(score)
                                          for name, score in status['audited_release_scores'].items()}})
        concepts.append({'concept': concept.name, 'mission': status['name'],
                         'verification_mode': status['mode'] + ': ' + MODES[status['mode']],
                         'baseline_champion_scores': generation_scores,
                         'fresh_agent_scores': fresh,
                         'counterexample_search_results': status.get('counterexample_search', status.get('countersearch_summary')),
                         'ratchet_generations': status['ratchet_generations'],
                         'final_status': status['status'],
                         'solvability': status['solvability'],
                         'substantive_failed_capability': status.get('failed_capability')})
    retained = [entry['concept'] for entry in concepts
                if entry['final_status'] in ['hard_open_candidate', 'hard_verified_achievable']]
    report = {'concepts': concepts, 'retained_concepts': retained,
              'final_status': 'retained' if retained else 'rejected'}
    final_status = {'status': report['final_status'], 'retained_concepts': retained,
                    'built_concepts': len(concepts),
                    'verification_modes': [entry['verification_mode'] for entry in concepts],
                    'fresh_attempt_count': sum(len(entry['fresh_agent_scores']) for entry in concepts),
                    'ratchet_generations': sum(entry['ratchet_generations'] for entry in concepts),
                    'reason': 'Empirically hard concept retained' if retained else
                              'Every valid tested generation was solved; no trustworthy hard concept survived.',
                    'report': 'FINAL_REPORT.json', 'audit': 'research/package_audit.json'}
    (ROOT / 'status.json').write_text(json.dumps(final_status, indent=2) + '\n')
    (ROOT / 'FINAL_REPORT.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    lines = ['# Empirical hardness report', '']
    for concept in concepts:
        lines.extend([f"## {concept['concept']}: {concept['mission']}",
                      f"- Verification mode: {concept['verification_mode']}."])
        for generation in concept['baseline_champion_scores']:
            label = 'instrumentation audit ' if generation.get('instrumentation_audit') else ''
            for name, score in generation['baseline_champion_scores'].items():
                lines.append(f"- Generation {generation['generation']} {label}{name}: `{json.dumps(score)}`")
        for attempt in concept['fresh_agent_scores']:
            lines.append(f"- Fresh attempt {attempt['attempt']} / generation {attempt['generation']} "
                         f"({attempt['model']}, {attempt['authoring_seconds']:.1f} s): `{json.dumps(attempt['score'])}`")
            if 'audited_score' in attempt:
                lines.append(f"- Attempt {attempt['attempt']} audited resource measurement: "
                             f"`{json.dumps(attempt['audited_score'])}`")
        lines.extend([f"- Counterexample search: {json.dumps(concept['counterexample_search_results'])}",
                      f"- Ratchet generations: {concept['ratchet_generations']}.",
                      f"- Final status: **{concept['final_status']}**.",
                      f"- Solvability: {concept['solvability']}.",
                      f"- Substantive failed capability: {concept['substantive_failed_capability'] or 'None demonstrated.'}", ''])
    lines.append('Retained concepts: ' + (', '.join(retained) if retained else 'none') + '.')
    (ROOT / 'FINAL_REPORT.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'retained_concepts': retained, 'concept_statuses':
                      {entry['concept']: entry['final_status'] for entry in concepts}}, indent=2))


if __name__ == '__main__':
    main()
