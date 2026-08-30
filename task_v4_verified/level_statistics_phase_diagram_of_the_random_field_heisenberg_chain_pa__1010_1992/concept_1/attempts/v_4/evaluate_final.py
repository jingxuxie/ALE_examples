import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[variable] = '1'
import gzip
import hashlib
import json
import pickle
from pathlib import Path
import numpy as np
from data_io import read, metrics
from predict import predict_chunk


def main():
    simulated = read('simulated.jsonl')
    heldout = sorted([case for case in simulated if int(case['id'].split('_')[-1]) >= 1600], key=lambda case: case['id'])
    assert len(heldout) == 200
    assert {case['id'] for case in heldout} == {f'simulation_{index:05d}' for index in range(1600, 1800)}
    with gzip.open('model.pkl.gz', 'rb') as stream:
        bundle = pickle.load(stream)
    model = bundle[0]['model']
    assert model['training_count'] == 4000 and model['target_training_count'] == 2080
    estimates = predict_chunk(bundle, heldout)
    scores = metrics(heldout, estimates)
    families = {family: value for family, value in scores.items() if family != 'overall'}
    counts = {family: sum(case['family'] == family for case in heldout) for family in families}
    report = {
        'heldout_records': len(heldout), 'heldout_simulation_indices': [1600, 1799],
        'heldout_used_for_fit_or_preprocessing': False,
        'overall_rmse': scores['overall'], 'by_family_rmse': families,
        'worst_family_rmse': max(families.values()),
        'balanced_family_rmse': float(np.sqrt(np.mean(np.array(list(families.values())) ** 2))),
        'family_counts': counts,
        'training_records': model['training_count'],
        'L14_training_records': model['target_training_count'],
        'public_training_records': 2400, 'additional_training_simulations': 1600,
        'model_sha256': hashlib.sha256(Path('model.pkl.gz').read_bytes()).hexdigest(),
        'meets_local_accuracy_targets': scores['overall'] <= .035 and max(families.values()) <= .05,
        'hidden_test_evaluated': False,
    }
    Path('validation_metrics.json').write_text(json.dumps(report, indent=2) + '\n')
    Path('heldout_cases.jsonl').write_text(''.join(json.dumps(case) + '\n' for case in heldout))
    public = read(Path(os.environ['SRC']) / 'input' / 'validation.jsonl')
    runtime_cases = heldout + public[:120]
    np.random.default_rng(280826).shuffle(runtime_cases)
    Path('runtime_cases.jsonl').write_text(''.join(json.dumps(case) + '\n' for case in runtime_cases))
    Path('heldout_predictions.json').write_text(json.dumps({'predictions': [
        {'id': case['id'], 'f': float(estimate)} for case, estimate in zip(heldout, estimates)]}, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
