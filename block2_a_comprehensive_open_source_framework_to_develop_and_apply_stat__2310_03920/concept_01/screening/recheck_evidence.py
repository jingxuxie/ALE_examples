import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'evaluator'))
from evidence import verify

grade = ROOT / 'screening/attempt_v01_grade'
initial = grade / 'evaluation_initial.json'
if not initial.exists():
    initial.write_text((grade / 'evaluation.json').read_text())
result = json.loads(initial.read_text())
evidence = verify(ROOT / 'attempts/v_01', ROOT / 'participant/v_01', grade / 'evidence_reruns_corrected')
result['evidence'] = evidence
result['overall_score'] = result['core_score'] * (0.85 + 0.1 * result['efficiency'] + 0.05 * evidence['score'])
result['evidence_audit_note'] = 'Accepted distinct actual configurations sharing a profile label, physical ablations, mixed-source plots and matched-time comparisons. No hidden case, physical target, core metric or threshold changed.'
(grade / 'evaluation.json').write_text(json.dumps(result, indent=2))
print(json.dumps({'overall_score': result['overall_score'], 'core_score': result['core_score'], 'evidence': evidence}, indent=2))
