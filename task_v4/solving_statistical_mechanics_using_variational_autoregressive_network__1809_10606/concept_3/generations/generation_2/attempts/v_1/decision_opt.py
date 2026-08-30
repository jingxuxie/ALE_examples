import argparse
import time

from infer import jax, jnp
from decision import DecisionProblem
import numpy as np


def optimizer(problem, regularization=0.01):
    features = jnp.asarray(problem.features)
    entropies = jnp.asarray(problem.entropies)
    groups = np.repeat(np.arange(48), [len(index) + 1 for index in problem.indices])
    group_index = jnp.asarray(groups)
    indices = jnp.asarray(problem.starts)
    global_features = jnp.asarray(problem.compress(problem.mean))
    field_queries = jnp.asarray(np.flatnonzero(problem.groups))
    zero_queries = jnp.asarray(np.flatnonzero(~problem.groups))

    def probabilities(logits):
        maximum = jax.ops.segment_max(logits, group_index, num_segments=48)
        weights = jnp.exp(logits - maximum[group_index])
        normalized = weights / jax.ops.segment_sum(weights, group_index, num_segments=48)[group_index]
        return .005 * global_features + .995 * normalized

    def loss(logits, temperature):
        estimate = probabilities(logits)
        log_estimate = jnp.log(jnp.maximum(estimate, 1e-300))
        contributions = features * log_estimate
        kl = entropies - jax.vmap(lambda row: jax.ops.segment_sum(row, group_index, num_segments=48))(contributions)
        differences = jnp.sqrt((features - estimate) ** 2 + 1e-14)
        tv = .5 * jax.vmap(lambda row: jax.ops.segment_sum(row, group_index, num_segments=48))(differences)
        ratio = jnp.maximum(jnp.max(tv, axis=1) / .120,
                            jnp.maximum(jnp.mean(kl, axis=1) / .020,
                                        jnp.maximum(jnp.mean(kl[:, field_queries], axis=1) / .035,
                                                    jnp.mean(kl[:, zero_queries], axis=1) / .035)))
        coverage = jax.nn.sigmoid((1 - ratio) / temperature).mean()
        return -coverage + regularization * kl.mean(), (coverage, kl.mean())

    value_grad = jax.value_and_grad(loss, has_aux=True)

    @jax.jit
    def update(logits, first_moment, second_moment, iteration, temperature, learning_rate):
        (value, auxiliary), gradient = value_grad(logits, temperature)
        first_moment = .9 * first_moment + .1 * gradient
        second_moment = .999 * second_moment + .001 * gradient ** 2
        adjusted_first = first_moment / (1 - .9 ** iteration)
        adjusted_second = second_moment / (1 - .999 ** iteration)
        logits = logits - learning_rate * adjusted_first / (jnp.sqrt(adjusted_second) + 1e-8)
        return logits, first_moment, second_moment, value, auxiliary

    return update, jax.jit(probabilities)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive")
    parser.add_argument("candidates")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--steps", type=int, default=600)
    parser.add_argument("--train-all", action="store_true")
    parser.add_argument("--output", default="optimized_candidates.npz")
    args = parser.parse_args()
    chains = np.load(args.archive)["predictions"]
    training = DecisionProblem(chains if args.train_all else chains[::2])
    validation = DecisionProblem(chains[1::2])
    initial = np.load(args.candidates)["candidates"]
    initial = np.concatenate([training.mean[None], initial[:args.count]], axis=0)
    update, get_probabilities = optimizer(training)
    all_candidates = []
    training_scores = []
    validation_scores = []
    started = time.time()
    for candidate_index, initial_prediction in enumerate(initial):
        logits = jnp.asarray(np.log(np.maximum(training.compress(initial_prediction), 1e-300)))
        first_moment = jnp.zeros_like(logits)
        second_moment = jnp.zeros_like(logits)
        for iteration in range(1, args.steps + 1):
            fraction = iteration / args.steps
            temperature = .15 if fraction < .4 else .07 if fraction < .75 else .03
            learning_rate = .025 if fraction < .4 else .012 if fraction < .75 else .005
            logits, first_moment, second_moment, value, auxiliary = update(
                logits, first_moment, second_moment, iteration, temperature, learning_rate)
            if iteration % 100 == 0:
                prediction = training.expand(np.asarray(get_probabilities(logits)))
                training_score = training.report(prediction, f"candidate {candidate_index} step {iteration} training")
                validation_score = validation.report(prediction, f"candidate {candidate_index} step {iteration} validation")
                all_candidates.append(prediction)
                training_scores.append(training_score)
                validation_scores.append(validation_score)
                print("elapsed", time.time() - started, "smooth loss", float(value), flush=True)
        np.savez(args.output, candidates=all_candidates, training_scores=training_scores, validation_scores=validation_scores)


if __name__ == "__main__":
    main()
