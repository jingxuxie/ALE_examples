import argparse
import json
import time

import numpy as np
from scipy.optimize import minimize

from infer import ASSETS, Likelihood, OUTPUT, load_data, model_from_edges
from native import NativeLikelihood


def fit(configurations, betas, spec, initial):
    likelihood = NativeLikelihood(Likelihood(configurations, betas, spec))
    started = time.monotonic()
    result = minimize(likelihood.evaluate, initial, jac=True, bounds=[(0.3, 0.95)] * 172 + [(-0.12, 0.12)] * 96, method='L-BFGS-B', options={'maxiter': 1500, 'maxcor': 30, 'ftol': 1e-12, 'gtol': 3e-7})
    print('fit result', result.message, result.fun, result.nit, 'seconds', time.monotonic() - started, flush=True)
    return result.x, likelihood


def error_metrics(truth, estimate, queries):
    divergence = np.sum(truth * np.log(truth / estimate), axis=1)
    variation = 0.5 * np.sum(np.abs(truth - estimate), axis=1)
    families = sorted(set(query['family'] for query in queries))
    family_divergence = {family: float(np.mean(divergence[[query['family'] == family for query in queries]])) for family in families}
    return {'mean_kl': float(divergence.mean()), 'family_kl': family_divergence, 'max_tv': float(variation.max()), 'query_kl': divergence.tolist(), 'query_tv': variation.tolist()}


def split_validation(configurations, betas, spec):
    training = configurations[:, :6144]
    testing = configurations[:, 6144:]
    initial = np.concatenate((np.full(172, 0.625), np.zeros(96)))
    values, likelihood = fit(training, betas, spec, initial)
    test_likelihood = NativeLikelihood(Likelihood(testing, betas, spec))
    queries = json.loads((ASSETS / 'input/queries.json').read_text())[:8]
    reference = []
    model_losses = []
    empirical_losses = []
    lookup = {site: index for index, site in enumerate(spec['visible_indices'])}
    for condition, beta in enumerate(betas):
        local_queries = [{**query, 'beta': float(beta)} for query in queries]
        predicted = likelihood.predict(values, local_queries)
        for query, probability in zip(local_queries, predicted):
            indices = [lookup[site] for site in query['readout']]
            train_codes = ((training[condition][:, indices] + 1) // 2) @ (1 << np.arange(6))
            test_codes = ((testing[condition][:, indices] + 1) // 2) @ (1 << np.arange(6))
            counts = np.bincount(train_codes, minlength=64).astype(float) + 0.5
            empirical = counts / counts.sum()
            model_loss = -np.log(probability[test_codes]).mean()
            empirical_loss = -np.log(empirical[test_codes]).mean()
            model_losses.append(float(model_loss))
            empirical_losses.append(float(empirical_loss))
            reference.append({'beta': float(beta), 'readout': query['readout'], 'model_cross_entropy': float(model_loss), 'empirical_cross_entropy': float(empirical_loss)})
    report = {'validation': 'held_out_2048_per_temperature', 'train_nll': likelihood.evaluate(values, gradient=False), 'test_nll': test_likelihood.evaluate(values, gradient=False), 'mean_joint_cross_entropy': float(np.mean(model_losses)), 'empirical_mean_joint_cross_entropy': float(np.mean(empirical_losses)), 'readouts': reference}
    print(json.dumps(report, indent=2), flush=True)
    (OUTPUT / 'validation_split.json').write_text(json.dumps(report, indent=2))
    np.savez(OUTPUT / 'fit_split.npz', theta=values)


def synthetic_validation(configurations, betas, spec, replicate):
    initial_fit = np.load(OUTPUT / 'fit.npz')['theta']
    geometry = np.load(OUTPUT / 'posterior_geometry.npz')
    reference_values = geometry['theta_mode']
    chain_path = OUTPUT / f'chain_{replicate % 4}.npz'
    if chain_path.exists():
        draws = np.load(chain_path)['theta']
        reference_values = draws.mean(axis=0)
    rng = np.random.default_rng(581201 + 9701 * replicate)
    reference_model = model_from_edges(spec, reference_values[:172] * np.asarray(spec['edge_signs']), reference_values[172:])
    synthetic = np.asarray([reference_model.sample(beta, 8192, rng)[:, spec['visible_indices']] for beta in betas])
    values, likelihood = fit(synthetic, betas, spec, initial_fit)
    queries = json.loads((ASSETS / 'input/queries.json').read_text())
    truth = likelihood.predict(reference_values, queries)
    estimate = likelihood.predict(values, queries)
    report = {'validation': 'synthetic_parameter_recovery', 'replicate': replicate, **error_metrics(truth, estimate, queries)}
    print(json.dumps(report, indent=2), flush=True)
    (OUTPUT / f'validation_synthetic_{replicate}.json').write_text(json.dumps(report, indent=2))
    np.savez(OUTPUT / f'synthetic_{replicate}.npz', reference=reference_values, fitted=values, truth=truth, estimate=estimate)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--split', action='store_true')
    parser.add_argument('--synthetic', type=int)
    args = parser.parse_args()
    configurations, betas, spec = load_data()
    if args.split:
        split_validation(configurations, betas, spec)
    if args.synthetic is not None:
        synthetic_validation(configurations, betas, spec, args.synthetic)
