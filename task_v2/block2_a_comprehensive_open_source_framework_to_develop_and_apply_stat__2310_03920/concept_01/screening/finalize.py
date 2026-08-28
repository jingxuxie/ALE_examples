import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
paper_root = ROOT.parent
reference = json.loads((ROOT / 'screening/reference_grade/evaluation.json').read_text())
attempt = json.loads((ROOT / 'screening/attempt_v01_grade/evaluation.json').read_text())
launch = json.loads((ROOT / 'screening/launch_v01.json').read_text())
manifest = json.loads((ROOT / 'screening/participant_v01_manifest.json').read_text())
changed = []
for relative, expected in manifest.items():
    path = ROOT / 'participant/v_01' / relative
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1048576), b''):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        changed.append(relative)
assert not changed, changed
assert launch['returncode'] == 0
assert 0.60 <= attempt['core_score'] < 0.90
assert attempt['evidence']['score'] == 1
assert all(record['status'] == 'ok' for record in attempt['per_family'].values())
classification = {
    'classification': 'moderate',
    'failure_type': 'bounded_vibronic_precision_shortfall_not_substantial_frontier_failure',
    'deadline_failure': False,
    'infrastructure_or_specification_failure': False,
    'evidence_audit_corrected_without_core_changes': True,
    'core_score': attempt['core_score'],
    'overall_score': attempt['overall_score'],
    'per_family': attempt['per_family'],
    'evidence_score': attempt['evidence']['score'],
    'model': launch['model'],
    'runtime_seconds': launch['runtime_seconds'],
    'participant_manifest_unchanged': True,
    'participant_files_checked': len(manifest),
    'transcript': 'screening/transcript_v01.txt',
    'outputs': 'attempts/v_01',
    'evaluator_json': 'screening/attempt_v01_grade/evaluation.json'
}
(ROOT / 'screening/failure_classification_v01.json').write_text(json.dumps(classification, indent=2))
status = {
    'status': 'rejected',
    'reason': 'valid_fresh_attempt_is_moderate_not_frontier_hard',
    'concept': 'transport_pipeline_reliability_across_conservation_laws',
    'archetype': 'A: real workspace diagnosis, repair, and performance validation',
    'version': 'v_01', 'redesigns': 0, 'built': True,
    'reference_core_score': reference['core_score'],
    'reference_overall_score': reference['overall_score'],
    'reference_evaluation_seconds': reference['evaluation_seconds'],
    'independent_exact_check': 'passed_all_five_families',
    'fresh_attempts': [classification]
}
(ROOT / 'status.json').write_text(json.dumps(status, indent=2))
paper_status = {
    'paper': 'Block2: a comprehensive open source framework to develop and apply state-of-the-art DMRG algorithms in electronic structure and beyond',
    'arxiv': '2310.03920',
    'status': 'rejected',
    'reason': 'paper_did_not_yield_frontier_hard_task',
    'selected_task': None,
    'screened_task_directory': str(ROOT / 'participant/v_01'),
    'built_concepts': 1,
    'redesigns': 0,
    'fresh_agents': 1,
    'reference_core_score': reference['core_score'],
    'reference_overall_score': reference['overall_score'],
    'fresh_attempts': [classification],
    'alternative_disposition': 'concept_02 rejected at source gates before construction; no second pilot or empirical attempt is claimed',
    'decision_record': 'concept_01/screening/hardness_decision.md'
}
(paper_root / 'status.json').write_text(json.dumps(paper_status, indent=2))
print(json.dumps({'status': paper_status['status'], 'reference': reference['overall_score'],
                  'attempt': attempt['overall_score'], 'core': attempt['core_score'],
                  'runtime_seconds': launch['runtime_seconds'], 'unchanged_files': len(manifest)}, indent=2))
