import argparse
import json
import time
import zipfile
from pathlib import Path

from infer import Inference, SOURCE, jax, jnp
import numpy as np
from scipy.special import logsumexp


def prediction_function(inference):
    states = inference.states
    products = inference.products
    flips = inference.flips
    betas = jnp.array([4.0, 6.0, 8.0, 10.0])
    query_temperatures = jnp.asarray([int(query["beta"] / 2 - 2) for query in inference.queries])
    query_columns = jnp.asarray([query["readout"][0] // 8 for query in inference.queries])
    codes = []
    field_energies = []
    outcome_states = (2 * ((np.arange(64)[:, None] >> np.arange(6)) & 1) - 1)
    for query in inference.queries:
        readout = np.asarray(query["readout"])
        codes.append(np.asarray(((states[:, readout % 8] + 1) / 2) @ (1 << np.arange(6)), dtype=np.int64))
        fields = np.zeros(6)
        for site, field in zip(query["field_indices"], query["field_values"]):
            fields[list(readout).index(site)] = field
        field_energies.append(query["beta"] * (outcome_states @ fields))
    codes = jnp.asarray(codes)
    field_energies = jnp.asarray(field_energies)

    def predict(theta):
        signed = theta * jnp.asarray(inference.sign_all)
        vertical = signed[:84].reshape(12, 7)
        horizontal = signed[84:172].reshape(11, 8)
        fields = signed[172:].reshape(12, 8)

        def temperature_marginals(beta):
            energies = beta * (vertical @ products.T + fields @ states.T)
            unary = jnp.exp(energies - jnp.max(energies, axis=1, keepdims=True))

            def transfer(weights, couplings):
                def row_step(current, values):
                    coupling, permutation = values
                    strength = beta * coupling
                    same = jnp.exp(strength - jnp.abs(strength))
                    different = jnp.exp(-strength - jnp.abs(strength))
                    return same * current + different * current[permutation], None
                return jax.lax.scan(row_step, weights, (couplings, flips))[0]

            def forward_step(forward, values):
                unary_column, couplings = values
                weights = unary_column * transfer(forward, couplings)
                normalized = weights / jnp.sum(weights)
                return normalized, normalized

            first_forward = unary[0] / unary[0].sum()
            _, forwards = jax.lax.scan(forward_step, first_forward, (unary[1:], horizontal))
            forwards = jnp.concatenate([first_forward[None, :], forwards], axis=0)

            def backward_step(backward, values):
                unary_column, couplings = values
                weights = transfer(unary_column * backward, couplings)
                normalized = weights / jnp.max(weights)
                return normalized, normalized

            last_backward = jnp.ones(256)
            _, backwards = jax.lax.scan(backward_step, last_backward, (unary[1:], horizontal), reverse=True)
            backwards = jnp.concatenate([backwards, last_backward[None, :]], axis=0)
            marginals = forwards * backwards
            return marginals / marginals.sum(axis=1, keepdims=True)

        marginals = jax.vmap(temperature_marginals)(betas)
        query_marginals = marginals[query_temperatures, query_columns]
        joints = jax.vmap(lambda index, weights: jnp.bincount(index, weights=weights, length=64))(codes, query_marginals)
        logits = jnp.log(joints) + field_energies
        return jax.nn.softmax(logits, axis=1)

    return jax.jit(predict), jax.jit(jax.vmap(predict))


def convergence(chains):
    chain_count, count, dimension = chains.shape
    if dimension > 64:
        blocks = [convergence(chains[:, :, offset:offset + 64]) for offset in range(0, dimension, 64)]
        return np.concatenate([block[0] for block in blocks]), np.concatenate([block[1] for block in blocks])
    half = count // 2
    split = np.concatenate([chains[:, :half], chains[:, -half:]], axis=0)
    within = split.var(axis=1, ddof=1).mean(axis=0)
    between = half * split.mean(axis=1).var(axis=0, ddof=1)
    variance = (half - 1) / half * within + between / half
    rhat = np.sqrt(variance / within)
    centered = chains - chains.mean(axis=1, keepdims=True)
    fft = np.fft.rfft(centered, n=2 * count, axis=1)
    autocovariance = np.fft.irfft(fft * np.conjugate(fft), n=2 * count, axis=1)[:, :count].real / count
    average_autocovariance = autocovariance.mean(axis=0)
    rho = 1 - (within[None, :] - average_autocovariance) / variance[None, :]
    pairs = rho[:count - count % 2].reshape(-1, 2, dimension).sum(axis=1)
    monotone = np.minimum.accumulate(pairs, axis=0)
    positive = np.maximum(monotone, 0).sum(axis=0)
    ess = chain_count * count / np.maximum(2 * positive - 1, 1)
    return rhat, ess


def summarize_differences(reference, estimate, label, queries):
    kl = np.sum(reference * (np.log(reference) - np.log(estimate)), axis=1)
    tv = np.abs(reference - estimate).sum(axis=1) / 2
    groups = np.asarray([query["family"] for query in queries])
    print(label, "mean KL", kl.mean(), "family KL", {family: float(kl[groups == family].mean()) for family in set(groups)},
          "max TV", tv.max(), "query", int(tv.argmax()), flush=True)
    return {"mean_kl": float(kl.mean()), "max_tv": float(tv.max())}


def validate_archive(path, queries):
    assert not Path(path).is_symlink()
    with zipfile.ZipFile(path) as archive:
        assert sorted(archive.namelist()) == ["probabilities.npy", "query_ids.npy"]
        for member in archive.infolist():
            assert member.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
            assert not (member.flag_bits & 1)
            with archive.open(member) as array_file:
                assert np.lib.format.read_magic(array_file) in ((1, 0), (2, 0))
    archive = np.load(path, allow_pickle=False)
    probabilities = archive["probabilities"]
    ids = archive["query_ids"]
    assert probabilities.shape == (48, 64)
    assert probabilities.dtype.str == "<f8"
    assert probabilities.flags.c_contiguous
    assert np.isfinite(probabilities).all()
    assert np.all((probabilities > 0) & (probabilities <= 1))
    assert np.max(np.abs(probabilities.sum(axis=1) - 1)) <= 1e-10
    assert ids.dtype.str == "<U24"
    assert ids.flags.c_contiguous
    assert np.array_equal(ids, np.asarray([query["id"] for query in queries], dtype="<U24"))
    assert Path(path).stat().st_size <= 65536
    print("Archive validated", path, Path(path).stat().st_size, "bytes; minimum probability", probabilities.min(), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("chains", nargs="*")
    parser.add_argument("--thin", type=int, default=2)
    parser.add_argument("--discard", type=int, default=0)
    parser.add_argument("--output", default="posterior_predictions.npz")
    parser.add_argument("--save-draws", default="predictive_draws.npz")
    args = parser.parse_args()
    inference = Inference()
    single_predict, batch_predict = prediction_function(inference)
    fit = np.load("fit.npz")
    reference = inference.predict(fit["theta"])
    actual = np.asarray(single_predict(fit["theta"]))
    np.testing.assert_allclose(actual, reference, rtol=1e-9, atol=1e-12)
    print("Fast cold prediction matches supplied simulator", flush=True)
    baseline = np.load(SOURCE / "baseline/predictions.npz")["probabilities"]
    summarize_differences(baseline, reference, "baseline -> maximum likelihood", inference.queries)
    if not args.chains:
        return
    parameters = [np.load(path)["samples"][args.discard::args.thin] for path in args.chains]
    shortest = min(len(chain) for chain in parameters)
    parameters = np.stack([chain[-shortest:] for chain in parameters])
    rhat, ess = convergence(parameters)
    print("Parameter Rhat quantiles", np.quantile(rhat, [0, .5, .9, .95, 1]),
          "ESS quantiles", np.quantile(ess, [0, .05, .1, .5, 1]), flush=True)
    print("Worst parameters", np.argsort(rhat)[-15:], flush=True)
    started = time.time()
    all_predictions = []
    for chain in parameters:
        predictions = []
        for offset in range(0, len(chain), 16):
            batch = chain[offset:offset + 16]
            actual_size = len(batch)
            if actual_size != 16:
                batch = np.concatenate([batch, np.repeat(batch[-1:], 16 - actual_size, axis=0)], axis=0)
            predictions.append(np.asarray(batch_predict(batch))[:actual_size])
        all_predictions.append(np.concatenate(predictions, axis=0))
        print("Predicted", len(chain), "draws in", time.time() - started, "seconds", flush=True)
    all_predictions = np.stack(all_predictions)
    posterior = all_predictions.mean(axis=(0, 1))
    posterior /= posterior.sum(axis=1, keepdims=True)
    summarize_differences(baseline, posterior, "baseline -> posterior", inference.queries)
    predictive_rhat, predictive_ess = convergence(all_predictions.reshape(*all_predictions.shape[:2], -1))
    meaningful = posterior.ravel() > 0.01
    print("Predictive Rhat quantiles", np.quantile(predictive_rhat[meaningful], [0, .5, .9, .95, 1]),
          "ESS quantiles", np.quantile(predictive_ess[meaningful], [0, .05, .1, .5, 1]), flush=True)
    for chain_index, predictions in enumerate(all_predictions):
        summarize_differences(posterior, predictions.mean(axis=0), f"posterior -> chain {chain_index}", inference.queries)
    np.savez_compressed(args.save_draws, predictions=all_predictions, parameters=parameters, rhat=rhat, ess=ess,
                        predictive_rhat=predictive_rhat, predictive_ess=predictive_ess)
    np.savez(args.output, probabilities=np.ascontiguousarray(posterior, dtype="<f8"),
             query_ids=np.asarray([query["id"] for query in inference.queries], dtype="<U24"))
    validate_archive(args.output, inference.queries)


if __name__ == "__main__":
    main()
