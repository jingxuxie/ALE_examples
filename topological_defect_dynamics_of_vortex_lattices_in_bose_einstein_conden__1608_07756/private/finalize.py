import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
concept = ROOT / 'concept_01'
reference = json.loads((concept / 'reference_evaluation.json').read_text())
evaluation_path = concept / 'screening/v_02/evaluator.json'
evaluation = json.loads(evaluation_path.read_text())
runtime = json.loads((concept / 'screening/v_02/runtime.json').read_text())
invalid = json.loads((concept / 'screening/v_01/evaluator.json').read_text())
frozen = json.loads((ROOT / 'private/screen_v02_frozen_hashes.json').read_text())
changed = [name for name, digest in frozen.items() if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
assert not changed, changed
assert evaluation['core_score'] >= 0.90
assert evaluation['evidence']['score'] == 1.0
assert runtime['participant_unchanged']
evaluation.update(model=runtime['model'], agent_runtime_seconds=runtime['runtime_seconds'], agent_timed_out=runtime['timed_out'], counts_as_hardness_attempt=True, failure_classification='too_easy_core_solved_despite_session_timeout', substantive_deliverables_complete=True, frozen_inputs_unchanged=True, scientific_report_audit='supported_with_finite_size_and_finite_window_caveats')
evaluation_path.write_text(json.dumps(evaluation, indent=2))
families = {name: record['score'] for name, record in evaluation['per_family'].items()}
attempts = [dict(version='v_01', model=invalid['model'], runtime_seconds=invalid['runtime_seconds'], core_score=None, overall_score=None, per_family_score={}, classification=invalid['failure_classification'], counts_as_hardness_attempt=False), dict(version='v_02', model=runtime['model'], runtime_seconds=runtime['runtime_seconds'], core_score=evaluation['core_score'], overall_score=evaluation['overall_score'], per_family_score=families, hidden_runtime_seconds=evaluation['runtime_seconds'], peak_rss_kib=evaluation['measured_peak_rss_kib'], evidence_score=evaluation['evidence']['score'], timed_out=runtime['timed_out'], classification=evaluation['failure_classification'], counts_as_hardness_attempt=True)]
record = dict(status='rejected', reason='paper_did_not_yield_frontier_hard_task', paper=dict(title='Topological defect dynamics of vortex lattices in Bose-Einstein condensates', arxiv='1608.07756', url='https://arxiv.org/abs/1608.07756'), screened_concept='concept_01', selected_concept=None, concept_title='CPU migration acceptance investigation for phase-engineered vortex lattices', archetype='A: workspace diagnosis, repair, and performance validation', contribution='Phase-imprinted vortex vacancies, signed subgrid core extraction, Delaunay defect dynamics, and orientational-order retention', participant_directory=str(concept / 'participant/v_02'), reference=dict(core_score=reference['core_score'], overall_score=reference['overall_score'], hidden_runtime_seconds=reference['runtime_seconds'], evidence_score=reference['evidence']['score']), attempts=attempts, considered_concepts=5, built_concepts=1, fundamental_redesigns=0, infrastructure_revisions=1, second_pilot_built=False, second_pilot_omission_reason='All four distinct remaining concepts fail centrality or standard-shortcut gates; no eligible alternative remains.', decision='Reject: the valid fresh submission solves the core across all five families. Its timeout does not reflect missing scientific work. Established numerical and geometric algorithms suffice.', private_audit='private/post_screen_audit.md')
(ROOT / 'status.json').write_text(json.dumps(record, indent=2))
(concept / 'status.json').write_text(json.dumps(record, indent=2))
(ROOT / 'private/integrity_audit.json').write_text(json.dumps(dict(frozen_file_count=len(frozen), changed_files=changed, participant_unchanged=runtime['participant_unchanged'], reference_evidence_checks=reference['evidence']['checks'], participant_evidence_checks=evaluation['evidence']['checks']), indent=2))
print(json.dumps(dict(status=record['status'], reference=record['reference'], attempts=attempts, built_concepts=1, fundamental_redesigns=0), indent=2))
