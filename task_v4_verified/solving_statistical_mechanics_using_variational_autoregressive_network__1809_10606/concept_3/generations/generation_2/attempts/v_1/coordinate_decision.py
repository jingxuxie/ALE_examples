import argparse
import itertools
import time

import numpy as np


def optimize(draws, initial, maximum_passes, rng):
    count = len(draws)
    mean = draws.mean(axis=0)
    uncertainty = np.abs(draws - mean).sum(axis=-1).mean(axis=0) / 2
    queries = np.argsort(uncertainty)[-12:]
    coordinates = []
    for query in queries:
        outcomes = mean[query].argsort()[-4:]
        outcomes = [outcome for outcome in outcomes if mean[query, outcome] > .005]
        coordinates.extend((query, first, second) for first, second in itertools.combinations(outcomes, 2))
    fields = np.asarray([query % 12 >= 6 for query in range(48)])
    prediction = initial.copy()
    entropies = np.stack([np.sum(draws[:, query] * np.log(draws[:, query]), axis=-1) for query in range(48)], axis=1)
    kl = np.empty((count, 48))
    tv = np.empty((count, 48))

    def update_query(query):
        kl[:, query] = entropies[:, query] - draws[:, query] @ np.log(prediction[query])
        tv[:, query] = np.abs(draws[:, query] - prediction[query]).sum(axis=-1) / 2

    def passed():
        return ((tv.max(axis=-1) <= .120) & (kl.sum(axis=-1) <= 48 * .020)
                & (kl[:, fields].sum(axis=-1) <= 24 * .035)
                & (kl[:, ~fields].sum(axis=-1) <= 24 * .035))

    for query in range(48):
        update_query(query)
    current_count = int(passed().sum())
    results = []
    coverage = []
    for pass_index in range(maximum_passes):
        previous_count = current_count
        order = rng.permutation(len(coordinates))
        for coordinate_index in order:
            query, first, second = coordinates[coordinate_index]
            family = fields == fields[query]
            other_queries = np.arange(48) != query
            eligible = ((tv[:, other_queries].max(axis=-1) <= .120)
                        & (kl[:, ~family].sum(axis=-1) <= 24 * .035))
            positions = np.flatnonzero(eligible)
            if len(positions) < current_count:
                continue
            first_probability = prediction[query, first]
            second_probability = prediction[query, second]
            truth_first = draws[positions, query, first]
            truth_second = draws[positions, query, second]
            first_difference = truth_first - first_probability
            second_difference = truth_second - second_probability
            remaining_tv = tv[positions, query] - .5 * (np.abs(first_difference) + np.abs(second_difference))
            radius = 2 * (.120 - remaining_tv)
            lower = (first_difference - second_difference - radius) / 2
            upper = (first_difference - second_difference + radius) / 2
            lower = np.maximum(lower, .005 * mean[query, first] - first_probability)
            upper = np.minimum(upper, second_probability - .005 * mean[query, second])
            feasible = (radius >= np.abs(first_difference + second_difference)) & (lower <= upper)
            if np.count_nonzero(feasible) < current_count:
                continue
            positions = positions[feasible]
            lower, upper = lower[feasible], upper[feasible]
            truth_first, truth_second = truth_first[feasible], truth_second[feasible]
            budget = np.minimum(48 * .020 - (kl[positions].sum(axis=-1) - kl[positions, query]),
                                24 * .035 - (kl[positions][:, family].sum(axis=-1) - kl[positions, query]))
            constant = (kl[positions, query] + truth_first * np.log(first_probability)
                        + truth_second * np.log(second_probability))

            def divergence(change):
                return (constant - truth_first * np.log(first_probability + change)
                        - truth_second * np.log(second_probability - change))

            best_change = ((first_probability + second_probability) * truth_first /
                           (truth_first + truth_second) - first_probability)
            best_change = np.clip(best_change, lower, upper)
            feasible = divergence(best_change) <= budget
            if np.count_nonzero(feasible) < current_count:
                continue
            needs_lower = divergence(lower) > budget
            needs_upper = divergence(upper) > budget
            if np.any(needs_lower):
                outside, inside = lower.copy(), best_change.copy()
                for _ in range(40):
                    middle = (outside + inside) / 2
                    failed = divergence(middle) > budget
                    outside = np.where(failed, middle, outside)
                    inside = np.where(failed, inside, middle)
                lower = np.where(needs_lower, inside, lower)
            if np.any(needs_upper):
                inside, outside = best_change.copy(), upper.copy()
                for _ in range(40):
                    middle = (outside + inside) / 2
                    failed = divergence(middle) > budget
                    outside = np.where(failed, middle, outside)
                    inside = np.where(failed, inside, middle)
                upper = np.where(needs_upper, inside, upper)
            lower, upper = lower[feasible], upper[feasible]
            endpoints = np.concatenate([lower, upper])
            changes = np.r_[np.ones(len(lower), dtype=int), -np.ones(len(upper), dtype=int)]
            event_order = np.argsort(endpoints, kind="stable")
            endpoints, changes = endpoints[event_order], changes[event_order]
            overlaps = np.cumsum(changes)[:-1]
            if not len(overlaps) or overlaps.max() < current_count + 3:
                continue
            intervals = np.flatnonzero(overlaps == overlaps.max())
            widths = endpoints[intervals + 1] - endpoints[intervals]
            chosen_interval = intervals[np.argmax(widths)]
            change = (endpoints[chosen_interval] + endpoints[chosen_interval + 1]) / 2
            prediction[query, first] += change
            prediction[query, second] -= change
            update_query(query)
            next_count = int(passed().sum())
            if next_count >= current_count + 3:
                current_count = next_count
            else:
                prediction[query, first] -= change
                prediction[query, second] += change
                update_query(query)
        print("coordinate pass", pass_index, "coverage", current_count / count,
              "expected KL", kl.mean(), "gain", current_count - previous_count, flush=True)
        results.append(prediction.copy())
        coverage.append(current_count / count)
        if current_count == previous_count:
            break
    return results, coverage


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive")
    parser.add_argument("candidates")
    parser.add_argument("--passes", type=int, default=5)
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--output", default="coordinate_candidates.npz")
    args = parser.parse_args()
    draws = np.load(args.archive)["predictions"].reshape(-1, 48, 64)
    initial = np.load(args.candidates)["candidates"][:args.count]
    results, coverages = [], []
    started = time.time()
    for index, candidate in enumerate(initial):
        print("Starting coordinate candidate", index, flush=True)
        predictions, coverage = optimize(draws, candidate, args.passes, np.random.default_rng(999 + index))
        results.extend(predictions)
        coverages.extend(coverage)
        np.savez(args.output, candidates=results, training_scores=coverages)
        print("Elapsed", time.time() - started, flush=True)


if __name__ == "__main__":
    main()
