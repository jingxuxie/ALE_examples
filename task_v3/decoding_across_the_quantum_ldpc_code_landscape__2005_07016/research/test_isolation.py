import json
from pathlib import Path
from isolation import run_submission

root = Path(__file__).resolve().parents[1]
result = run_submission(root / 'research/baselines/local_weak', root / 'pilots/01_local_recovery/participant', root / 'pilots/01_local_recovery/participant/input/example.npz', timeout=30)
answer = result.pop('answer_bytes')
result['output_bytes'] = len(answer) if answer else 0
print(json.dumps(result, indent=2))
(root / 'research/isolation_smoke.json').write_text(json.dumps(result, indent=2))
if not answer:
    raise RuntimeError('Isolated numerical interface is unavailable')
