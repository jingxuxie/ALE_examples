import json
import zipfile

import numpy as np
from scipy.special import ndtri
from scipy.stats import rankdata

from infer import ASSETS, OUTPUT, Likelihood, load_data
from native import NativeLikelihood


def split_rhat(chains):
    count = chains.shape[1] // 2
    split = np.concatenate((chains[:, :count], chains[:, -count:]), axis=0)
    within = split.var(axis=1, ddof=1).mean(axis=0)
    between = count * split.mean(axis=1).var(axis=0, ddof=1)
    return np.sqrt(((count - 1) / count * within + between / count) / np.maximum(within, 1e-30))


def rank_rhat(chains):
    flat = chains.reshape(-1, chains.shape[-1])
    ranks = rankdata(flat, axis=0)
    normalized = ndtri((ranks - 0.375) / (len(flat) + 0.25)).reshape(chains.shape)
    folded_ranks = rankdata(np.abs(flat - np.median(flat, axis=0)), axis=0)
    folded = ndtri((folded_ranks - 0.375) / (len(flat) + 0.25)).reshape(chains.shape)
    return np.maximum(split_rhat(normalized), split_rhat(folded))


def effective_sample_size(chains):
    chain_count, sample_count, parameter_count = chains.shape
    centered = chains - chains.mean(axis=1, keepdims=True)
    transformed = np.fft.rfft(centered, n=2 * sample_count, axis=1)
    autocovariance = np.fft.irfft(np.abs(transformed) ** 2, n=2 * sample_count, axis=1)[:, :sample_count] / sample_count
    within = chains.var(axis=1, ddof=1).mean(axis=0)
    between = sample_count * chains.mean(axis=1).var(axis=0, ddof=1)
    variance = within * (sample_count - 1) / sample_count + between / sample_count
    correlation = 1 - (within[None, :] - autocovariance.mean(axis=0)) / np.maximum(variance[None, :], 1e-30)
    correlation[0] = 1
    estimates = np.empty(parameter_count)
    for parameter in range(parameter_count):
        pairs = correlation[:2 * (sample_count // 2), parameter].reshape(-1, 2).sum(axis=1)
        negative = np.flatnonzero(pairs <= 0)
        if len(negative):
            pairs = pairs[:negative[0]]
        pairs = np.minimum.accumulate(pairs)
        integrated = max(1.0, -1 + 2 * pairs.sum())
        estimates[parameter] = chain_count * sample_count / integrated
    return estimates


def main():
    configurations, betas, spec = load_data()
    likelihood = NativeLikelihood(Likelihood(configurations, betas, spec))
    queries = json.loads((ASSETS / 'input/queries.json').read_text())
    archives = [np.load(OUTPUT / f'chain_{chain}.npz') for chain in range(4)]
    common_length = min(len(archive['theta']) for archive in archives)
    chains = np.asarray([archive['theta'][:common_length] for archive in archives])
    parameter_rhat = rank_rhat(chains)
    parameter_ess = effective_sample_size(chains)
    stored_predictions = np.asarray([archive['predictive'][:common_length // 10] for archive in archives])
    predictive_rhat = rank_rhat(stored_predictions.reshape(4, -1, 24 * 64))
    predictive_ess = effective_sample_size(stored_predictions.reshape(4, -1, 24 * 64))
    predictions = np.asarray([[likelihood.predict(values, queries) for values in chain] for chain in chains])
    mean_prediction = predictions.mean(axis=(0, 1))
    mean_prediction /= mean_prediction.sum(axis=1, keepdims=True)
    divergences = np.sum(predictions * np.log(predictions / mean_prediction), axis=-1)
    variations = 0.5 * np.sum(np.abs(predictions - mean_prediction), axis=-1)
    mle_prediction = likelihood.predict(np.load(OUTPUT / 'fit.npz')['theta'], queries)
    mle_divergence = np.sum(mean_prediction * np.log(mean_prediction / mle_prediction), axis=1)
    chain_predictions = predictions.mean(axis=1)
    chain_tv = 0.5 * np.sum(np.abs(chain_predictions - mean_prediction), axis=-1)
    families = sorted(set(query['family'] for query in queries))
    report = {
        'samples_per_chain': common_length,
        'acceptance': [float(archive['acceptance'][:common_length].mean()) for archive in archives],
        'parameter_rhat_quantiles': np.quantile(parameter_rhat, [0, 0.5, 0.9, 0.99, 1]).tolist(),
        'parameter_ess_quantiles': np.quantile(parameter_ess, [0, 0.1, 0.5, 1]).tolist(),
        'worst_parameter_rhat': [(int(index), float(parameter_rhat[index])) for index in np.argsort(parameter_rhat)[-10:]],
        'predictive_rhat_quantiles': np.quantile(predictive_rhat, [0, 0.5, 0.9, 0.99, 1]).tolist(),
        'predictive_ess_quantiles': np.quantile(predictive_ess, [0, 0.1, 0.5, 1]).tolist(),
        'posterior_expected_kl': float(divergences.mean()),
        'posterior_family_expected_kl': {family: float(divergences[:, :, [query['family'] == family for query in queries]].mean()) for family in families},
        'posterior_mean_kl_quantiles': np.quantile(divergences.mean(axis=-1), [0.5, 0.9, 0.99]).tolist(),
        'posterior_max_tv_quantiles': np.quantile(variations.max(axis=-1), [0.5, 0.9, 0.99]).tolist(),
        'max_chain_mean_tv': float(chain_tv.max()),
        'mle_difference_mean_kl': float(mle_divergence.mean()),
        'minimum_probability': float(mean_prediction.min()),
        'maximum_probability': float(mean_prediction.max()),
    }
    print(json.dumps(report, indent=2), flush=True)
    (OUTPUT / 'posterior_diagnostics.json').write_text(json.dumps(report, indent=2))
    np.savez(OUTPUT / 'posterior_summary.npz', theta_mean=chains.mean(axis=(0, 1)), probabilities=mean_prediction, chain_probabilities=chain_predictions, parameter_rhat=parameter_rhat, parameter_ess=parameter_ess)
    np.savez(OUTPUT / 'predictions.npz', probabilities=np.ascontiguousarray(mean_prediction, dtype='<f8'), query_ids=np.ascontiguousarray([query['id'] for query in queries], dtype='<U24'))
    path = OUTPUT / 'predictions.npz'
    assert path.stat().st_size <= 65536
    with zipfile.ZipFile(path) as archive:
        assert archive.namelist() == ['probabilities.npy', 'query_ids.npy']
        assert archive.testzip() is None
    with np.load(path, allow_pickle=False) as archive:
        probabilities = archive['probabilities']
        query_ids = archive['query_ids']
        assert probabilities.shape == (24, 64)
        assert probabilities.dtype.str == '<f8'
        assert probabilities.flags.c_contiguous
        assert np.isfinite(probabilities).all()
        assert np.all((probabilities > 0) & (probabilities <= 1))
        assert np.max(np.abs(probabilities.sum(axis=1) - 1)) <= 1e-10
        assert query_ids.dtype.str == '<U24'
        assert query_ids.flags.c_contiguous
        assert query_ids.tolist() == [query['id'] for query in queries]
    print('Submission archive verified:', path.stat().st_size, 'bytes', flush=True)


if __name__ == '__main__':
    main()
