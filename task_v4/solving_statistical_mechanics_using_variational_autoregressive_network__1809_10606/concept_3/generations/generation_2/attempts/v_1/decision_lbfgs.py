import argparse
import time

from infer import jax, jnp
from decision import DecisionProblem
import numpy as np
from scipy.optimize import minimize


def objective(problem, active_count=12):
    uncertainty = np.abs(problem.draws - problem.mean).sum(axis=-1).mean(axis=0) / 2
    query_indices = np.sort(np.argsort(uncertainty)[-active_count:])
    print("Active response queries", query_indices, flush=True)
    sizes = [len(problem.indices[query]) + 1 for query in query_indices]
    width = max(sizes)
    values = np.zeros((len(problem.draws), len(query_indices), width))
    active = np.zeros((len(query_indices), width), dtype=bool)
    for position, (query, size) in enumerate(zip(query_indices, sizes)):
        start = problem.starts[query]
        values[:, position, :size] = problem.features[:, start:start + size]
        active[position, :size] = True
    features = jnp.asarray(values)
    mask = jnp.asarray(active)
    prior = jnp.asarray(values.mean(axis=0))
    entropies = jnp.asarray(problem.entropies[:, query_indices])
    field = jnp.asarray(np.flatnonzero(problem.groups[query_indices]))
    zero = jnp.asarray(np.flatnonzero(~problem.groups[query_indices]))
    _, static_kl, static_tv = problem.scores(problem.mean)
    static_kl[:, query_indices] = 0
    static_tv[:, query_indices] = 0
    constant_kl_all = jnp.asarray(static_kl.sum(axis=-1))
    constant_kl_field = jnp.asarray(static_kl[:, problem.groups].sum(axis=-1))
    constant_kl_zero = jnp.asarray(static_kl[:, ~problem.groups].sum(axis=-1))
    constant_tv = jnp.asarray(static_tv.max(axis=-1))

    def probabilities(logits):
        logits = logits.reshape(len(query_indices), width)
        normalized = jax.nn.softmax(jnp.where(mask, logits, -1e300), axis=-1)
        return .005 * prior + .995 * normalized

    def loss(logits, temperature):
        estimate = probabilities(logits)
        kl = entropies - (features * jnp.log(jnp.maximum(estimate, 1e-300))).sum(axis=-1)
        tv = .5 * jnp.sqrt((features - estimate) ** 2 + 1e-14).sum(axis=-1)
        mean_kl = (constant_kl_all + kl.sum(axis=-1)) / 48
        field_kl = (constant_kl_field + kl[:, field].sum(axis=-1)) / 24
        zero_kl = (constant_kl_zero + kl[:, zero].sum(axis=-1)) / 24
        ratio = jnp.maximum(jnp.maximum(constant_tv, tv.max(axis=-1)) / .120,
                            jnp.maximum(mean_kl / .020, jnp.maximum(field_kl, zero_kl) / .035))
        return -jax.nn.sigmoid((1 - ratio) / temperature).mean() + .01 * mean_kl.mean()

    def initialize(prediction):
        compressed = problem.compress(prediction)
        logits = np.full((len(query_indices), width), -700.0)
        for position, (query, size) in enumerate(zip(query_indices, sizes)):
            start = problem.starts[query]
            logits[position, :size] = np.log(np.maximum(compressed[start:start + size], 1e-300))
        return logits.ravel()

    compiled_probabilities = jax.jit(probabilities)

    def expand(logits):
        padded = np.asarray(compiled_probabilities(logits))
        compressed = problem.compress(problem.mean).copy()
        for position, (query, size) in enumerate(zip(query_indices, sizes)):
            start = problem.starts[query]
            compressed[start:start + size] = padded[position, :size]
        return problem.expand(compressed)

    return jax.jit(jax.value_and_grad(loss)), initialize, expand


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive")
    parser.add_argument("candidates")
    parser.add_argument("--count", type=int, default=2)
    parser.add_argument("--iterations", type=int, default=60)
    parser.add_argument("--output", default="lbfgs_candidates.npz")
    parser.add_argument("--active", type=int, default=12)
    args = parser.parse_args()
    chains = np.load(args.archive)["predictions"]
    problem = DecisionProblem(chains)
    starting = np.load(args.candidates)["candidates"]
    starting = np.concatenate([problem.mean[None], starting[:args.count]], axis=0)
    value_grad, initialize, expand = objective(problem, args.active)
    candidates = []
    coverages = []
    started = time.time()
    for candidate_index, prediction in enumerate(starting):
        logits = initialize(prediction)
        for temperature in [.15, .08, .04]:
            def scipy_loss(current):
                loss, gradient = value_grad(current, temperature)
                return float(loss), np.asarray(gradient)

            benchmark = time.time()
            result = minimize(scipy_loss, logits, jac=True, method="L-BFGS-B",
                              options={"maxiter": args.iterations, "maxls": 30, "maxcor": 20,
                                       "ftol": 1e-11, "gtol": 1e-7})
            logits = result.x
            prediction = expand(logits)
            coverage = problem.report(prediction, f"candidate {candidate_index} temperature {temperature}")
            print("solver", result.message, "iterations", result.nit, "evaluations", result.nfev,
                  "seconds", time.time() - benchmark, "total", time.time() - started, flush=True)
            candidates.append(prediction)
            coverages.append(coverage)
            np.savez(args.output, candidates=candidates, training_scores=coverages)


if __name__ == "__main__":
    main()
