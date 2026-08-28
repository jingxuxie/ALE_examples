import json
import math
import os
import subprocess
import time

from validate import ROOT, query, write_job, run


def multiply(first, second):
    return [sum(first[index] * second[order - index] for index in range(order + 1))
            for order in range(9)]


def vertex_series(weight):
    return [0.0] + [weight ** order / math.factorial(order) for order in range(1, 9)]


def path_series(weights):
    previous = [1.0] + [0.0] * 8
    previous_previous = previous[:]
    for weight in weights:
        selected = multiply(vertex_series(weight), previous_previous)
        current = [left + right for left, right in zip(previous, selected)]
        previous_previous, previous = previous, current
    return previous


def main():
    count = 139
    radial = 0.5 * 10 ** (-1 / 12) * 1.0001
    event = [(1.0, radial * math.cos(2 * math.pi * index / count),
              radial * math.sin(2 * math.pi * index / count)) for index in range(count)]
    queries = [query(order, kappa, resolution=1e20)
               for kappa in [1, 1.5, 2] for order in range(2, 9)]
    path = write_job("ring", [event], queries)
    lines = [str(ROOT / "ring.txt"), f"1 {len(queries)}"]
    lines += [" ".join(str(specification[key]) for key in
                       ["order", "kappa", "algorithm", "resolution", "log_min", "bins"])
              for specification in queries]
    start = time.perf_counter()
    try:
        result = subprocess.run([str(ROOT / "engine")], input="\n".join(lines) + "\n",
                                text=True, stdout=subprocess.PIPE, env=dict(os.environ, EEC_STATS="1"),
                                timeout=10, check=True)
    except subprocess.TimeoutExpired:
        print("near-antipodal ring TIMEOUT", flush=True)
        return
    histograms = json.loads(result.stdout)["histograms"]
    stirling = [[0] * 9 for unused in range(9)]
    stirling[0][0] = 1
    for order in range(1, 9):
        for support in range(1, order + 1):
            stirling[order][support] = stirling[order - 1][support - 1] + support * stirling[order - 1][support]
    maximum_error = 0
    for specification, histogram in zip(queries, histograms):
        order = specification["order"]
        cumulative = sum(count * math.comb(count - support, support) // (count - support)
                         * math.factorial(support) * stirling[order][support]
                         for support in range(1, order + 1)) * count ** (-specification["kappa"] * order)
        total = count ** ((1 - specification["kappa"]) * order)
        error = abs(sum(histogram[:-1]) - cumulative) / total
        maximum_error = max(maximum_error, error)
    print("near-antipodal ring seconds", time.perf_counter() - start,
          "maximum_scaled_CDF_error", maximum_error, flush=True)
    assert maximum_error < 1e-10
    weighted_event = [(1 + 0.7 * math.sin(0.31 * index), rapidity, phi)
                      for index, (pt, rapidity, phi) in enumerate(event)]
    weighted_path = write_job("weighted_ring", [weighted_event], queries)
    histograms = run(weighted_path, "weighted_ring")
    total_pt = sum(particle[0] for particle in weighted_event)
    maximum_error = 0
    for specification, histogram in zip(queries, histograms):
        weights = [(weighted_event[(index * 69) % count][0] / total_pt) ** specification["kappa"]
                   for index in range(count)]
        excluded = path_series(weights[1:])
        included = multiply(vertex_series(weights[0]), path_series(weights[2:-1]))
        order = specification["order"]
        cumulative = (excluded[order] + included[order]) * math.factorial(order)
        error = abs(sum(histogram[:-1]) - cumulative) / sum(weights) ** order
        maximum_error = max(maximum_error, error)
    print("weighted near-antipodal cycle maximum_scaled_CDF_error", maximum_error, flush=True)
    assert maximum_error < 1e-10


if __name__ == "__main__":
    main()
