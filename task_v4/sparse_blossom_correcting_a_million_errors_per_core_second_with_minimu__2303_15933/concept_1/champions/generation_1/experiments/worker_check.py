import argparse
import json
import os
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    directory = root / 'experiments'
    participant = Path(os.environ['P']).resolve()
    if args.prepare:
        items = []
        for path in sorted((participant / 'input/cases').iterdir()):
            with np.load(directory / f'{path.name}_2048_95173027.npz') as data:
                syndromes = data['syndromes']
            for split in range(2):
                input_path = directory / f'worker_in_{path.name}_{split}.npz'
                output_path = directory / f'worker_out_{path.name}_{split}.npz'
                np.savez_compressed(input_path, syndromes=syndromes[split * 1024:(split + 1) * 1024])
                items.append(dict(case_id=path.name, syndromes=str(input_path), predictions=str(output_path)))
        request = dict(submission=str(root / 'submission.py'), participant_root=str(participant),
                       items=items, limits=dict(address_bytes=6 * 1024 ** 3, cpu_seconds=180))
        (directory / 'worker_request.json').write_text(json.dumps(request, indent=2))
        return
    response = json.loads((directory / 'worker_response.json').read_text())
    cases = []
    for path in sorted((participant / 'input/cases').iterdir()):
        with np.load(directory / f'{path.name}_2048_95173027.npz') as data:
            labels, baseline = data['labels'], data['baseline']
        pieces = []
        for split in range(2):
            with np.load(directory / f'worker_out_{path.name}_{split}.npz') as data:
                pieces.append(data['predictions'])
        predictions = np.concatenate(pieces)
        expected = np.load(directory / f'final_independent_{path.name}_predictions.npy')
        assert np.array_equal(predictions, expected)
        wrong_base = np.any(baseline != labels, axis=1)
        wrong = np.any(predictions != labels, axis=1)
        cases.append(dict(case_id=path.name, shots=len(labels), baseline_failures=int(wrong_base.sum()),
                          candidate_failures=int(wrong.sum()), corrected=int((wrong_base & ~wrong).sum()),
                          spoiled=int((~wrong_base & wrong).sum()),
                          cpu_seconds=sum(item['cpu_seconds'] for item in response['cases'] if item['case_id'] == path.name)))
    shots = sum(item['shots'] for item in cases)
    corrected = sum(item['corrected'] for item in cases)
    spoiled = sum(item['spoiled'] for item in cases)
    baseline = sum(item['baseline_failures'] for item in cases)
    failures = sum(item['candidate_failures'] for item in cases)
    improvement = (corrected - spoiled) / shots
    standard_error = np.sqrt(((corrected + spoiled) / shots - improvement ** 2) / shots)
    report = dict(kind='independent_public_model_samples', seed=95173027, shots=shots, cases=cases,
                  baseline_failures=baseline, candidate_failures=failures,
                  relative_error_reduction=1 - failures / baseline,
                  paired_absolute_ci95=[improvement - 1.96 * standard_error, improvement + 1.96 * standard_error],
                  worker_cpu_seconds=sum(item['cpu_seconds'] for item in cases),
                  split_batch_predictions_equal=True)
    (root / 'validation_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
