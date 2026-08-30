import argparse
import json
import time
from pathlib import Path

import numpy as np

import fast_features
from fast_features import ROOT, FAMILIES, sample_parameters, fisher_features
from optimize import BASELINE, CANDIDATES, CONTRACT, sparse_risks
from physics import risks, score_risks, validate_batches


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('designs', nargs='+')
    parser.add_argument('--count', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=574893102)
    parser.add_argument('--output', default='validation_summary.json')
    args = parser.parse_args()
    designs = {}
    summaries = {}
    for filename in args.designs:
        payload = json.loads(Path(filename).read_text())
        assert set(payload) == {'batches'}
        batch, cost = validate_batches(payload['batches'], CANDIDATES, CONTRACT)
        designs[filename] = batch
        summaries[filename] = {'execution_ticks': cost, 'distinct_circuits': int(np.count_nonzero(batch)),
                               'batches': int(batch.sum()), 'shots': int(batch.sum() * 64),
                               'max_batches': int(batch.max()), 'feasible': True}
        development = np.load(ROOT / 'input/development.npz')
        core, family = score_risks(sparse_risks(development['features'], batch),
                                  sparse_risks(development['features'], BASELINE), development['families'])
        summaries[filename]['development'] = {'overall_reduction': core, 'family_reductions': family,
                                              'worst_family_reduction': min(family.values())}
    selected = np.flatnonzero(BASELINE + sum(designs.values()))
    fast_features.CANDIDATES = [CANDIDATES[index] for index in selected]
    generator = np.random.default_rng(args.seed)
    parameters = np.array([sample_parameters(generator, family) for family in FAMILIES for _ in range(args.count)])
    families = np.repeat(FAMILIES, args.count)
    baseline_risks = []
    design_risks = {filename: [] for filename in designs}
    started = time.time()
    discrepancy = 0
    for start in range(0, len(parameters), 32):
        features = fast_features.features_fast(parameters[start:start + 32])
        if start % args.count < 32:
            exact = fisher_features(parameters[start], fast_features.CANDIDATES)
            discrepancy = max(discrepancy, float(np.max(np.abs(features[0] - exact))))
            assert np.allclose(features[0], exact, rtol=2e-5, atol=2e-8)
        baseline_risks.extend(risks(features, BASELINE[selected]).tolist())
        for filename, batch in designs.items():
            design_risks[filename].extend(risks(features, batch[selected]).tolist())
    baseline_risks = np.array(baseline_risks)
    saved = {'parameters': parameters, 'families': families, 'baseline_risks': baseline_risks}
    bootstrap_generator = np.random.default_rng(args.seed + 1)
    bootstrap_indices = bootstrap_generator.integers(args.count, size=(2000, args.count))
    for filename in designs:
        current = np.array(design_risks[filename])
        assert np.isfinite(current).all() and (current > 0).all()
        overall, family_scores = score_risks(current, baseline_risks, families)
        family_stats = {}
        baseline_bootstrap = []
        current_bootstrap = []
        for family in FAMILIES:
            mask = families == family
            ratios = current[mask] / baseline_risks[mask]
            current_means = current[mask][bootstrap_indices].mean(axis=1)
            baseline_means = baseline_risks[mask][bootstrap_indices].mean(axis=1)
            baseline_bootstrap.append(baseline_means)
            current_bootstrap.append(current_means)
            family_stats[family] = {'reduction': family_scores[family],
                                    'baseline_mean_risk': float(baseline_risks[mask].mean()),
                                    'design_mean_risk': float(current[mask].mean()),
                                    'reduction_bootstrap_95_interval': np.quantile(1-current_means/baseline_means, [.025, .975]).tolist(),
                                    'local_risk_ratio_quantiles_50_90_99_100': np.quantile(ratios, [.5, .9, .99, 1]).tolist()}
        bootstrap_overall = 1 - np.sum(current_bootstrap, axis=0) / np.sum(baseline_bootstrap, axis=0)
        summaries[filename]['independent_validation'] = {
            'points_per_family': args.count, 'total_points': len(parameters), 'seed': args.seed,
            'overall_reduction': overall, 'worst_family_reduction': min(family_scores.values()),
            'overall_reduction_bootstrap_95_interval': np.quantile(bootstrap_overall, [.025, .975]).tolist(),
            'families': family_stats}
        saved[Path(filename).stem + '_risks'] = current
        print(filename, 'overall', overall, 'worst family', min(family_scores.values()), family_scores, flush=True)
    result = {'designs': summaries, 'maximum_feature_discrepancy': discrepancy,
              'elapsed_seconds': time.time() - started}
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
    np.savez(Path(args.output).with_suffix('.npz'), **saved)
    print('validation completed', result['elapsed_seconds'], 'seconds', flush=True)


if __name__ == '__main__':
    main()
