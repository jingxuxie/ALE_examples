import argparse
import json
import math
from pathlib import Path
import random
import time

import numpy as np

import solve


DIRECTORY = Path(__file__).resolve().parent
PUBLIC = DIRECTORY.parent / "participant" / "input"


def query(nu, nsub=16, bins=48, log_min=-4.0):
    return dict(nu=nu, nsub=nsub, bins=bins, log_min=log_min)


def run(events, queries, name, algorithm="cliques", shuffle=False):
    rows = [f"{event_id} {pt:.17g} {rapidity:.17g} {phi:.17g}\n"
            for event_id, event in enumerate(events) for pt, rapidity, phi in event]
    if shuffle:
        random.Random(1642).shuffle(rows)
    path = DIRECTORY / (name + ".txt")
    path.write_text("".join(rows))
    job = dict(kind="fractional", events_file=path.name, nevents=len(events), queries=queries)
    job_path = DIRECTORY / (name + ".json")
    job_path.write_text(json.dumps(job))
    start = time.perf_counter()
    answer = solve.compute(job, job_path, algorithm)["histograms"]
    return [np.array(histogram) for histogram in answer], time.perf_counter() - start


def maximum_error(first, second):
    return max((float(np.max(np.abs(left - right))) for left, right in zip(first, second)), default=0)


def direct(events, queries):
    histograms = []
    for settings in queries:
        histogram = np.zeros(settings["bins"], dtype=np.longdouble)
        for event in events:
            count = len(event)
            fractions = np.array([point[0] for point in event], dtype=np.longdouble)
            fractions /= fractions.sum()
            sums = np.zeros(1 << count, dtype=np.longdouble)
            diameters = np.zeros(1 << count)
            for mask in range(1, 1 << count):
                bit = mask & -mask
                vertex = bit.bit_length() - 1
                rest = mask ^ bit
                sums[mask] = sums[rest] + fractions[vertex]
                diameter = diameters[rest]
                remaining = rest
                while remaining:
                    other_bit = remaining & -remaining
                    other = other_bit.bit_length() - 1
                    dy = event[vertex][1] - event[other][1]
                    dphi = math.remainder(event[vertex][2] - event[other][2], 2 * math.pi)
                    diameter = max(diameter, math.hypot(dy, dphi))
                    remaining ^= other_bit
                diameters[mask] = diameter
            weights = sums ** np.longdouble(settings["nu"])
            for vertex in range(count):
                bit = 1 << vertex
                reshaped = weights.reshape(-1, 2 * bit)
                reshaped[:, bit:] -= reshaped[:, :bit]
            for mask in range(1, 1 << count):
                distance = diameters[mask]
                bin_index = 0
                if distance > 10 ** settings["log_min"]:
                    bin_index = min(settings["bins"] - 1, int(
                        (math.log10(distance) - settings["log_min"])
                        * settings["bins"] / -settings["log_min"]))
                histogram[bin_index] += weights[mask]
        histograms.append(np.asarray(histogram / len(events), dtype=float))
    return histograms


def random_event(generator, count):
    points = []
    for index in range(count):
        width = 0.008 if index % 4 else 0.21
        center = -0.065 if index % 3 else 0.13
        rapidity = center + max(-0.48, min(0.48, generator.gauss(0, width)))
        phi = 3.12 + center / 2 + max(-0.48, min(0.48, generator.gauss(0, width)))
        pt = math.exp(generator.uniform(-4, 5))
        points.append((pt, rapidity, phi))
    return points


def validate(benchmark_events):
    generator = random.Random(517904)
    report = {}
    job_path = PUBLIC / "sample.json"
    job = json.loads(job_path.read_text())
    sample = [np.array(histogram) for histogram in solve.compute(job, job_path)["histograms"]]
    sample_brute = [np.array(histogram) for histogram in solve.compute(job, job_path, "mobius")["histograms"]]
    report["public_sample_max_error"] = maximum_error(sample, sample_brute)
    assert report["public_sample_max_error"] < 2e-10
    report["public_sample_masses"] = [float(histogram.sum()) for histogram in sample]
    report["public_sample_negative_bins"] = [int(np.sum(histogram < -1e-10)) for histogram in sample]

    small_events = [
        [(7.0, -0.4, 3.13)],
        [(3.0, 0, 0), (7.0, 0.17, 0.09)],
        [(240, 0, 0), (180, 0.18, 0.08), (80, -0.07, -0.16)],
        [(1, 0, 3.14), (2, 0.1, -3.12), (4, -0.2, 9.37)],
        [(1, 0, 0), (7, 0, 0), (0.1, 0, 0)],
        [(3, -0.65, 0), (4, 0.65, 0)],
        [(3, 0, 0), (2, 3e-7, 0), (5, 0.19, 0.03)],
    ] + [random_event(generator, count) for count in range(3, 9)]
    small_queries = [query(nu) for nu in (0.001, 0.15, 0.6, 1, 1.00001, 1.7, 2, 3, 4.5, 8, 16.5)]
    small, _ = run(small_events, small_queries, "validation_small")
    expected = direct(small_events, small_queries)
    report["independent_full_subset_max_error"] = maximum_error(small, expected)
    assert report["independent_full_subset_max_error"] < 3e-11

    polygon = [(1.0, 0.431 * math.cos(2 * math.pi * index / 8),
                0.431 * math.sin(2 * math.pi * index / 8)) for index in range(8)]
    polygon_actual, _ = run([polygon], [query(0.6)], "validation_polygon")
    polygon_expected = direct([polygon], [query(0.6)])
    report["signed_polygon_max_error"] = maximum_error(polygon_actual, polygon_expected)
    report["signed_polygon_positive_noncontact_mass"] = float(polygon_actual[0][1:].clip(min=0).sum())
    assert report["signed_polygon_max_error"] < 2e-11
    assert report["signed_polygon_positive_noncontact_mass"] > 1e-4
    assert np.any(polygon_actual[0][1:] < -1e-4)

    dense_events = [random_event(generator, count) for count in (17, 31, 70, 139)]
    dense_events.append([(1.0, 0.418 * math.cos(2 * math.pi * index / 16),
                          0.418 * math.sin(2 * math.pi * index / 16)) for index in range(16)])
    dense_events.append([(math.exp(generator.uniform(-4, 4)),
                          0.52 * math.cos(2 * math.pi * index / 139),
                          0.52 * math.sin(2 * math.pi * index / 139)) for index in range(139)])
    dense_queries = [query(nu) for nu in (0.02, 0.15, 0.6, 1.7, 2, 3, 4.5, 10.5)]
    dense_queries += [query(17.3, 15, 257, -1.8), query(0.27, 7, 131, -3.3), query(2.01, 16, 5, -0.6)]
    dense_queries += [query(0.3, nsub=cap) for cap in (2, 3, 5, 8, 12, 13, 14)]
    dense, dense_time = run(dense_events, dense_queries, "validation_dense")
    dense_brute, brute_time = run(dense_events, dense_queries, "validation_dense", "mobius")
    report["high_multiplicity_max_error"] = maximum_error(dense, dense_brute)
    report["dense_validation_seconds"] = dense_time
    report["exhaustive_validation_seconds"] = brute_time
    assert report["high_multiplicity_max_error"] < 3e-10
    assert maximum_error([dense[-7], dense[-3]], [dense[-6], dense[-2]]) == 0
    report["maximum_normalization_error"] = max(abs(float(histogram.sum()) - 1) for histogram in dense)
    assert report["maximum_normalization_error"] < 2e-10

    unshuffled, _ = run(dense_events[:4], dense_queries, "validation_unshuffled")
    shuffled, _ = run(dense_events[:4], dense_queries, "validation_shuffled", shuffle=True)
    report["permutation_max_error"] = maximum_error(unshuffled, shuffled)
    assert report["permutation_max_error"] < 3e-10
    transformed_events = [[(pt * 1e7, rapidity + 0.73, phi + 8 * math.pi)
                           for pt, rapidity, phi in event] for event in dense_events[:4]]
    invariant_queries = dense_queries[:8]
    original, _ = run(dense_events[:4], invariant_queries, "validation_original")
    transformed, _ = run(transformed_events, invariant_queries, "validation_transformed")
    report["kinematic_invariance_max_error"] = maximum_error(original, transformed)
    assert report["kinematic_invariance_max_error"] < 3e-10

    rebin_queries = [query(0.4, bins=24), query(0.4, bins=48), query(1, bins=17), query(0.4, bins=1)]
    rebinned, _ = run(dense_events, rebin_queries, "validation_rebin")
    report["rebin_max_error"] = maximum_error([rebinned[0]], [rebinned[1].reshape(24, 2).sum(axis=1)])
    assert report["rebin_max_error"] < 2e-11
    assert rebinned[2][0] == 1 and np.count_nonzero(rebinned[2]) == 1
    assert abs(rebinned[3][0] - 1) < 1e-10

    if benchmark_events:
        benchmark = [random_event(generator, (30, 50, 70, 139)[index % 4])
                     for index in range(benchmark_events)]
        benchmark_queries = [query(0.15, 12), query(0.6, 16), query(1.7, 14), query(4.5, 12)]
        answer, elapsed = run(benchmark, benchmark_queries, "benchmark")
        report["benchmark_events"] = benchmark_events
        report["benchmark_constituents"] = sum(map(len, benchmark))
        report["benchmark_seconds"] = elapsed
        report["benchmark_normalization_error"] = max(abs(float(histogram.sum()) - 1) for histogram in answer)
    (DIRECTORY / "validation_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-events", type=int, default=1000)
    arguments = parser.parse_args()
    validate(arguments.benchmark_events)
