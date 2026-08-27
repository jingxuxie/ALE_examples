import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
path = ROOT / 'concept_01/evaluator/evaluate.py'
specification = importlib.util.spec_from_file_location('private_evaluator', path)
evaluator = importlib.util.module_from_spec(specification)
specification.loader.exec_module(evaluator)
score_path = ROOT / 'concept_01/reference_evaluation.json'
record = json.loads(score_path.read_text())
work = Path(record['work_directory'])
submission = ROOT / 'concept_01/solution'
for variant, config in [('ablation', 'ablation_config.json'), ('refinement', 'refinement_config.json')]:
    record[variant + '_rerun_seconds'] = evaluator.run_submission(submission, ROOT / 'concept_01/participant/v_01/input/campaign.json', work / (variant + '_rerun'), submission / config)
record['evidence'] = evaluator.audit_evidence(submission, work / 'public_rerun')
record['overall_score'] = 0.85 * record['core_score'] + 0.10 * record['resource_score'] + 0.05 * record['evidence']['score']
score_path.write_text(json.dumps(record, indent=2))
print(json.dumps(dict(core=record['core_score'], overall=record['overall_score'], evidence=record['evidence']), indent=2))
