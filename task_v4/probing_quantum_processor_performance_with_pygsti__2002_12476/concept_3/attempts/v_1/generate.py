import json

import numpy as np

from model import ROOT, SCALE, load, predict, report, select
from validate import reference


def main():
    queries = load('queries')
    development = load('development')
    probabilities = np.empty(len(queries['ids']))
    development_probabilities = np.empty(len(development['ids']))
    diagnostics = {}
    rng = np.random.default_rng(7281)
    for device in range(4):
        fit = np.load(ROOT / f'fit_d{device}_all.npz')
        params = fit['params']
        train_params = np.load(ROOT / f'fit_d{device}_train.npz')['params']
        selected = queries['device'] == device
        device_queries = select(queries, selected)
        predicted, jacobian = predict(params, device_queries, True)
        probabilities[selected] = predicted
        covariance = np.linalg.inv(fit['jacobian'].T @ fit['jacobian'])
        scaled_jacobian = jacobian*SCALE
        variance = np.einsum('ni,ij,nj->n', scaled_jacobian, covariance, scaled_jacobian)
        train_predicted = predict(train_params, device_queries)
        samples = select(device_queries, rng.choice(len(predicted), 16, replace=False))
        difference = np.max(np.abs(reference(params, samples)-predict(params, samples)))
        assert difference < 1e-10
        selected_development = development['device'] == device
        device_development = select(development, selected_development)
        development_probabilities[selected_development] = predict(train_params, device_development)
        diagnostics[str(device)] = {
            'heldout_development': report(train_params, device_development),
            'test_reference_max_abs_difference': float(difference),
            'test_families': {},
        }
        for family in np.unique(device_queries['family']):
            family_mask = device_queries['family'] == family
            diagnostics[str(device)]['test_families'][str(family)] = {
                'linearized_estimation_rmse': float(np.sqrt(np.mean(variance[family_mask]))),
                'train_to_combined_prediction_rmse': float(np.sqrt(np.mean((predicted[family_mask]-train_predicted[family_mask])**2))),
            }
    document = {'ids': queries['ids'].tolist(), 'p1': probabilities.tolist()}
    submission = ROOT / 'predictions.json'
    submission.write_text(json.dumps(document, separators=(',', ':'), allow_nan=False)+'\n')
    (ROOT / 'development_heldout.json').write_text(json.dumps({'ids': development['ids'].tolist(), 'p1': development_probabilities.tolist()}, allow_nan=False)+'\n')
    (ROOT / 'diagnostics.json').write_text(json.dumps(diagnostics, indent=2, allow_nan=False)+'\n')
    parsed = json.loads(submission.read_text())
    assert set(parsed) == {'ids', 'p1'}
    assert len(parsed['ids']) == len(parsed['p1']) == len(queries['ids'])
    assert all(type(identifier) is int for identifier in parsed['ids'])
    assert len(set(parsed['ids'])) == len(parsed['ids'])
    assert set(parsed['ids']) == set(queries['ids'].tolist())
    assert all(type(probability) is float and np.isfinite(probability) and 0 <= probability <= 1 for probability in parsed['p1'])
    assert submission.is_file() and not submission.is_symlink()
    assert submission.stat().st_size <= 2097152
    print(json.dumps({'submission': str(submission), 'rows': len(probabilities), 'bytes': submission.stat().st_size,
                      'probability_min': float(probabilities.min()), 'probability_max': float(probabilities.max()),
                      'max_cell_linearized_estimation_rmse': max(cell['linearized_estimation_rmse'] for item in diagnostics.values() for cell in item['test_families'].values()),
                      'max_cell_heldout_noise_corrected_rmse': max(cell['noise_corrected_rmse'] for item in diagnostics.values() for key, cell in item['heldout_development'].items() if key != 'deviance_per_row')}, indent=2))


if __name__ == '__main__':
    main()
