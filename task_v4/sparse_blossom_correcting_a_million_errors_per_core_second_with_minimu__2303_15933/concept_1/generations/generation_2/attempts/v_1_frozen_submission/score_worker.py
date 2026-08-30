import json
import sys
from pathlib import Path
import numpy as np

prefix = sys.argv[1]
response = json.loads(Path(prefix + '_response.json').read_text())
results = []
for entry in response['cases']:
    case = entry['case_id']
    data = np.load('data_' + case + '_83724_512.npz')
    prediction = np.load(prefix + '_predictions_' + case + '.npz')['predictions']
    baseline_wrong = np.any(data['baseline'] != data['labels'], axis=1)
    wrong = np.any(prediction != data['labels'], axis=1)
    results.append(dict(entry, baseline_failures=int(baseline_wrong.sum()), candidate_failures=int(wrong.sum()), corrected=int((baseline_wrong & ~wrong).sum()), spoiled=int((~baseline_wrong & wrong).sum())))
baseline = sum(entry['baseline_failures'] for entry in results)
failures = sum(entry['candidate_failures'] for entry in results)
report = dict(kind='generated_development_validation', shots=3072, baseline_failures=baseline, candidate_failures=failures, error_reduction=1-failures/baseline, cpu_seconds=sum(entry['cpu_seconds'] for entry in results), cases=results)
Path(prefix + '_score.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
