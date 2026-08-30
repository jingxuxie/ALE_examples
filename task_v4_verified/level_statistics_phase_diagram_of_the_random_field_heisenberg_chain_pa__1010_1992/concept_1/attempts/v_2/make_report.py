import hashlib
import json
from pathlib import Path

from predict import Predictor
from test_stream import metrics


def main():
    public_runs = json.loads(Path('submission_public_validation.json').read_text())
    fresh_runs, cases, predictions = [], [], []
    for batch in range(5):
        fresh_runs.extend(json.loads(Path(f'fresh_result_{batch}.json').read_text()))
        cases.extend(json.loads(line) for line in Path(f'fresh_validation_{batch}.jsonl').read_text().splitlines())
        predictions.extend(json.loads(Path(f'fresh_result_{batch}.predictions.json').read_text())['predictions'])
    fresh_metrics = metrics(cases, {'predictions': predictions})
    predictor = Predictor()
    fallback_metrics = metrics(cases, predictor.predict(cases, exact_limit=0))
    runs = public_runs + fresh_runs
    result = {
        'public_validation_runs': public_runs,
        'fresh_validation': dict(records=len(cases), label_precision='float64', **fresh_metrics),
        'fresh_validation_surrogate_only': fallback_metrics,
        'fresh_validation_runs': fresh_runs,
        'resources': {'cpu_affinity_cores': 4, 'address_space_mib': 2048,
                      'max_startup_seconds': max(run['startup_seconds'] for run in runs),
                      'max_response_seconds': max(run['response_seconds'] for run in runs),
                      'max_total_inference_seconds': max(run['total_inference_seconds'] for run in runs),
                      'tested_batches': len(runs), 'all_runs_passed': all(run['passed'] for run in runs)},
        'models': {f'model{length}.pkl.gz': hashlib.sha256(Path(f'model{length}.pkl.gz').read_bytes()).hexdigest()
                   for length in (10, 12)},
        'hidden_evaluation_performed': False,
        'validation_labels_used_for_fitting': False,
    }
    Path('submission_report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('public_validation_runs', 'fresh_validation_runs')}, indent=2))


if __name__ == '__main__':
    main()
