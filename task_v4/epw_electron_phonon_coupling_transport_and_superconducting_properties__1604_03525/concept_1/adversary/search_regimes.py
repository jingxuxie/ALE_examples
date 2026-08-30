import argparse
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'evaluator'))
from evaluate import evaluate
from generate import make_split, KB, INDICES, OMEGA, WIDTH


def regime_split(seed, per_family, regime):
    inputs, labels = make_split(seed, per_family)
    generator = np.random.default_rng(seed + 583929)
    count = len(labels['family'])
    if regime != 'original':
        inputs['temperature_k'] = generator.uniform(4, 6, count)
    if regime == 'warm_noisy_weak':
        old_coupling = np.sum(labels['alpha2f'] * (2 * WIDTH / OMEGA), axis=1)
        labels['alpha2f'] *= (generator.uniform(0.55, 1.1, count) / old_coupling)[:, None]
    inputs['nu_mev'] = 2 * np.pi * KB * inputs['temperature_k'][:, None] * INDICES
    lower_noise = 0.0012 if regime in ('warm_noisy', 'warm_noisy_weak') else 0.0003
    scale = np.exp(generator.uniform(np.log(lower_noise), np.log(0.002), count))
    inputs['noise_std'] = scale[:, None] * (0.35 + 0.65 / (1 + (inputs['nu_mev'] / 75) ** 0.7))
    mass = labels['alpha2f'] * (2 * WIDTH / OMEGA)
    kernel = OMEGA ** 2 / (OMEGA ** 2 + inputs['nu_mev'][..., None] ** 2)
    clean = np.einsum('brj,bj->br', kernel, mass)
    separation = np.abs(np.arange(40)[:, None] - np.arange(40))
    for row in range(count):
        rho = inputs['noise_rho'][row]
        covariance = (1 - rho) * np.eye(40) + rho * np.exp(-separation / inputs['noise_length'][row])
        clean[row] += inputs['noise_std'][row] * (np.linalg.cholesky(covariance) @ generator.normal(size=40))
    clean[~inputs['mask']] = 0
    inputs['interaction'] = clean
    return inputs, labels


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission', type=Path, required=True)
    args = parser.parse_args()
    output = ROOT / 'adversary/regime_search'
    output.mkdir(exist_ok=True)
    jobs = []
    for regime_index, regime in enumerate(['original', 'warm', 'warm_noisy', 'warm_noisy_weak']):
        for replicate in range(4):
            name = f'{regime}_{replicate}'
            inputs, labels = regime_split(8314914 + regime_index * 859 + replicate * 83, 96, regime)
            np.savez_compressed(output / f'{name}_input.npz', **inputs)
            np.savez_compressed(output / f'{name}_labels.npz', **labels)
            jobs.append((name, regime))

    def test(job):
        name, regime = job
        result = evaluate(args.submission, output / f'{name}_input.npz', output / f'{name}_labels.npz')
        result.update(name=name, regime=regime)
        (output / f'{name}_score.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
        print(json.dumps({key: result[key] for key in ['name', 'core_score', 'worst_family_score', 'valid', 'passed']}), flush=True)
        return result

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(test, jobs))
    summary = []
    for regime in ['original', 'warm', 'warm_noisy', 'warm_noisy_weak']:
        selected = [result for result in results if result['regime'] == regime]
        if not all(result['valid'] for result in selected):
            summary.append({'regime': regime, 'valid': False})
            continue
        losses = np.concatenate([result['case_losses'] for result in selected])
        families = np.concatenate([result['case_families'] for result in selected])
        family_scores = {str(code): float(100 * np.exp(-losses[families == code].mean())) for code in range(4)}
        summary.append({'regime': regime, 'valid': True, 'cases': len(losses),
                        'core_score': float(100 * np.exp(-losses.mean())), 'family_scores': family_scores,
                        'worst_family_score': min(family_scores.values())})
    (output / 'summary.json').write_text(json.dumps({'regimes': summary, 'cases': 6144}, indent=2) + '\n')


if __name__ == '__main__':
    main()
