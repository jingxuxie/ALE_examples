import ast
import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / 'concept_01'


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2))


def main():
    reference = read(CONCEPT / 'screening/reference_corrected_eval/evaluation.json')
    evaluation = read(CONCEPT / 'screening/v_01/fresh_01/evaluation_corrected/evaluation.json')
    runtime = read(CONCEPT / 'screening/v_01/fresh_01/runtime.json')
    independent = read(CONCEPT / 'screening/reference_independent_checks.json')
    pole = read(CONCEPT / 'screening/independent_long_lead_pole.json')
    assert reference['core_score'] >= .9 and reference['evidence']['all_checks_pass']
    assert independent['all_pass'] and pole['central_density_error'] < 1e-8
    assert evaluation['core_score'] >= .9 and not evaluation['infrastructure_failure']
    assert evaluation['evidence']['all_checks_pass']
    assert runtime['participant_unchanged'] and not runtime['timeout'] and runtime['returncode'] == 0
    frozen = read(CONCEPT / 'screening/v_01/frozen_manifest.json')['files']
    changes = []
    for relative, digest in frozen.items():
        path = CONCEPT / relative
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            changes.append(relative)
    allowed = {
        'evaluator/evaluate.py',
        'solution/v_01/workspace/transport/spectral.py',
        'evaluator/hidden/gold/ring_holdout.npz',
        'evaluator/hidden/gold/ring_holdout.json',
        'evaluator/hidden/gold/results.csv',
    }
    assert set(changes).issubset(allowed), changes
    assert not any(relative.startswith('participant/') or relative == 'evaluator/hidden/cases.json' for relative in changes)
    original = CONCEPT / 'screening/v_01/evaluate_original.py'
    current = CONCEPT / 'evaluator/evaluate.py'
    def core_ast(path):
        return ast.dump(next(node for node in ast.parse(path.read_text()).body if isinstance(node, ast.FunctionDef) and node.name == 'score_case'))
    assert core_ast(original) == core_ast(current)
    audit = dict(participant_unchanged=True, hidden_inputs_unchanged=True, numerical_scoring_unchanged=True,
                 declared_postfreeze_repairs=changes, attempt_valid=True, timeout_based_hardness_claim=False,
                 conclusions='All 336 evidence checks pass. Five initially near-perfect families plus an independently corrected missing reference pole give near-perfect agreement in all six. No scientific failure is attributable to the participant.',
                 remaining_concepts='private/remaining_concepts.md')
    write(CONCEPT / 'screening/v_01/final_audit.json', audit)
    attempt = dict(attempt_id='fresh_01', model=runtime['model'], reasoning_effort='xhigh',
                   runtime_seconds=runtime['runtime_seconds'], timeout=False, returncode=0,
                   core_score=evaluation['core_score'], overall_score=evaluation['overall_score'],
                   per_family=evaluation['per_family'], resources=evaluation['resources'],
                   evidence_score=evaluation['evidence']['score'], evidence_checks=evaluation['evidence']['total'],
                   failure_classification='none_solved_core_concept_too_easy',
                   evaluation='screening/v_01/fresh_01/evaluation_corrected/evaluation.json',
                   transcript='screening/v_01/fresh_01/transcript.txt',
                   output='attempts/v_01/fresh_01/output',
                   original_grade_superseded_for_reference_error=True)
    reference_summary = dict(core_score=reference['core_score'], overall_score=reference['overall_score'],
                             per_family=reference['per_family'], resources=reference['resources'],
                             evidence_score=reference['evidence']['score'],
                             evaluation='screening/reference_corrected_eval/evaluation.json',
                             independent_validation_passed=True)
    concept_status = dict(status='rejected', reason='frontier_agent_solved_core',
                          concept='Transient transport release qualification',
                          archetype='A: real-workspace diagnosis, repair, and performance validation',
                          participant_version='v_01', participant_directory='participant/v_01',
                          fundamental_redesigns=0, reference=reference_summary, fresh_attempts=[attempt],
                          task_complete=True, no_frontier_hardness_claim=True,
                          reference_correction='screening/v_01/reference_correction.md',
                          final_audit='screening/v_01/final_audit.json')
    write(CONCEPT / 'status.json', concept_status)
    reserve = dict(status='rejected', concept='Automatic absorbing-boundary qualification across multiband leads',
                   archetype='C: method selection under shift and budget', built=False,
                   reason='standard_shortcut_before_construction', fresh_attempts=[],
                   audit='private/remaining_concepts.md')
    write(ROOT / 'concept_02/status.json', reserve)
    root_status = dict(status='rejected', reason='paper_did_not_yield_frontier_hard_task',
                       paper='Tkwant: a software package for time-dependent quantum transport', arxiv='2009.03132',
                       selected_task_concept=None, screened_concept='concept_01',
                       screened_archetype=concept_status['archetype'],
                       participant_task_directory='concept_01/participant/v_01',
                       central_contribution='Lead-resolved many-body scattering-state evolution with open-lead boundary treatment, spectral quadrature, and local transient observables.',
                       concepts_considered=5, built_task_concepts=1,
                       reserve_concept_rejected_before_construction=True,
                       fundamental_redesigns=0, reference=reference_summary, fresh_attempts=[attempt],
                       known_good_solution_passes=True, public_task_complete=True,
                       valid_substantial_frontier_failures=0,
                       decision='Reject rather than tighten thresholds, add hidden cases, or count a reference error as agent failure.',
                       remaining_concept_audit='private/remaining_concepts.md')
    write(ROOT / 'status.json', root_status)
    previous = CONCEPT / 'screening/v_01/fresh_01/evaluation/evaluation.json'
    superseded = read(previous)
    superseded.update(superseded=True, valid_for_hardness=False,
                      superseded_by='../evaluation_corrected/evaluation.json',
                      reason='Reference omitted an independently verified occupied shallow bound state; not an agent failure.')
    write(previous, superseded)
    for name in ['reference_final_eval', 'reference_eval']:
        path = CONCEPT / 'screening' / name / 'evaluation.json'
        if path.exists():
            value = read(path)
            value.update(superseded=True, valid_for_hardness=False, superseded_by='../reference_corrected_eval/evaluation.json')
            write(path, value)
    specification = importlib.util.spec_from_file_location('pilot_evaluator', current)
    evaluator = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(evaluator)
    weak_path = CONCEPT / 'screening/weak_baseline_eval/evaluation.json'
    weak = read(weak_path)
    cases = read(CONCEPT / 'evaluator/hidden/cases.json')['cases']
    weak['per_case'] = {
        case['id']: evaluator.score_case(case,
            CONCEPT / 'screening/weak_baseline_eval/hidden_run' / ('withheld_' + str(index) + '.npz'),
            CONCEPT / 'evaluator/hidden/gold' / (case['id'] + '.npz'))
        for index, case in enumerate(cases)}
    weak['per_family'] = {value['family']: value['score'] for value in weak['per_case'].values()}
    scores = list(weak['per_family'].values())
    weak['core_score'] = .7 * sum(scores) / len(scores) + .3 * min(scores)
    weak['overall_score'] = .9 * weak['core_score'] + .07 * weak['resource_score']
    weak['recomputed_from_unchanged_execution'] = 'weak_baseline_eval/hidden_run'
    weak['reference_revision'] = 'corrected_scalar_bound_spectrum'
    write(CONCEPT / 'screening/weak_baseline_corrected_eval/evaluation.json', weak)
    print(json.dumps(root_status, indent=2))


if __name__ == '__main__':
    main()
