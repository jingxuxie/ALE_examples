import json
from pathlib import Path
import fermion


root = Path(__file__).resolve().parent
circuits = []
for case in fermion.load_cases():
    saved = json.loads((root / (case.case_id + '_best.json')).read_text())
    circuits.append({'case_id': case.case_id, 'gates': saved['gates']})
output = root / 'submission.json'
output.write_text(json.dumps({'schema_version': 1, 'circuits': circuits}, separators=(',', ':'), allow_nan=False) + '\n')
print(json.dumps(fermion.evaluate_path(output), indent=2))
