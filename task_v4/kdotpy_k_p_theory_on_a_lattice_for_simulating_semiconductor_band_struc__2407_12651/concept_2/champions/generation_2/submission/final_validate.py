import json
import subprocess
from pathlib import Path

import numpy as np
from model import LOWER, UPPER, diagnose
from audit import margins


parameters = np.array(json.loads(Path('final_candidate.json').read_text())['parameters'])
assert parameters.shape == (25,) and np.isfinite(parameters).all()
assert np.all(parameters >= LOWER) and np.all(parameters <= UPPER)
shifts = [(0.137, 0.271), (0.319, 0.173), (0.223, 0.417)]
nominal = [diagnose(parameters, size, shift) for size in [49, 73, 97] for shift in shifts]
for result in nominal:
    assert min(margins(result).values()) >= -1e-10, result
fine_responses = np.array([result['windows'] + [result['full']] for result in nominal[3:]])
fine_difference = float(np.ptp(fine_responses, axis=0).max())
assert fine_difference <= .0008, fine_difference
extra_fine = diagnose(parameters, 145, (.413, .293))
assert min(margins(extra_fine).values()) >= -1e-10
assert np.max(np.abs(np.array(extra_fine['windows']) - nominal[-1]['windows'])) <= .0008
audit = json.loads(Path('final_candidate_audit_739271.json').read_text())
assert len(audit['robust']) == 8234
failed = [(index, margins(result, True)) for index, result in enumerate(audit['robust'])
          if min(margins(result, True).values()) < -1e-10]
assert not failed, failed
payload = json.dumps({'parameters': parameters.tolist()}, indent=2) + '\n'
patch = '*** Begin Patch\n*** Add File: witness.json\n' + ''.join('+' + line + '\n' for line in payload.splitlines()) + '*** End Patch\n'
subprocess.run(['apply_patch'], input=patch, text=True, check=True)
summary = {
    'nominal': nominal,
    'additional_145_mesh': extra_fine,
    'fine_mesh_maximum_difference': fine_difference,
    'axial_probe_count': 42,
    'independent_simultaneous_probe_count': 8192,
    'robust_mesh': 73,
    'minimum_robust_margins': audit['minimum_margins'],
    'scope': 'Local independent probes; frozen checker probes are unavailable.'
}
Path('validation_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
