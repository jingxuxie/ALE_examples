import json
import itertools
import math
import os
from pathlib import Path
import random
import subprocess
import time


ROOT = Path(__file__).resolve().parent
PARTICIPANT = ROOT.parent / "participant"


def run(job_path, label, oracle=False):
    output = ROOT / (label + ".result.json")
    environment = dict(os.environ, EEC_STATS="1")
    if oracle:
        environment["EEC_ORACLE"] = "1"
    start = time.perf_counter()
    subprocess.run([
        "python", str(ROOT / "solve.py"), "--input", str(job_path),
        "--output", str(output),
    ], check=True, env=environment)
    result = json.loads(output.read_text())["histograms"]
    print(label, "wall_seconds", time.perf_counter() - start, flush=True)
    return result


def compare(first, second, label):
    error = max(sum(abs(left - right) for left, right in zip(lhs, rhs))
                / max(sum(map(abs, rhs)), 1e-100) for lhs, rhs in zip(first, second))
    print(label, "maximum_relative_L1", error, flush=True)
    assert error < 2e-10


def write_job(label, events, queries):
    data_path = ROOT / (label + ".txt")
    with data_path.open("w") as output:
        for event_id, event in enumerate(events):
            for pt, rapidity, phi in event:
                output.write(f"{event_id} {pt:.17g} {rapidity:.17g} {phi:.17g}\n")
    job = {"kind": "weighted", "events_file": data_path.name,
           "nevents": len(events), "queries": queries}
    job_path = ROOT / (label + ".json")
    job_path.write_text(json.dumps(job))
    return job_path


def query(order, kappa, algorithm="ca", resolution=8, bins=48, log_min=-4):
    return dict(order=order, kappa=kappa, algorithm=algorithm, resolution=resolution,
                bins=bins, log_min=log_min)


def main():
    sample = PARTICIPANT / "input" / "sample.json"
    compare(run(sample, "sample"), run(sample, "sample_oracle", True), "public_sample")
    random_source = random.Random(238749)
    queries = [query(order, kappa, algorithm, resolution)
               for algorithm, resolution in [("ca", 1.01), ("ca", 8), ("ca", 1e8),
                                              ("kt", 0.0001), ("kt", 0.03), ("kt", 100)]
               for kappa in [1.0, 1.25, 1.5, 1.75, 2.0]
               for order in range(2, 9)]
    events = [[(10 ** random_source.uniform(-1, 2), random_source.gauss(0, 0.15),
                3.1 + random_source.gauss(0, 0.15)) for unused in range(8)]
              for event in range(12)]
    events += [[(1, 0, 0)], [(2, 0, 0), (3, 0, 0)],
               [(1, 0, 0), (2, 0.2, 0), (3, -0.2, 0), (4, 0, 0.2), (5, 0, -0.2)]]
    randomized = write_job("randomized", events, queries)
    exact = run(randomized, "randomized")
    oracle = run(randomized, "randomized_oracle", True)
    compare(exact, oracle, "randomized_all_modes")
    totals = []
    for specification in queries:
        total = 0
        for event in events:
            scalar_pt = sum(particle[0] for particle in event)
            total += sum((particle[0] / scalar_pt) ** specification["kappa"]
                         for particle in event) ** specification["order"] / len(events)
        totals.append([total])
    compare([[sum(histogram)] for histogram in exact], totals, "mass_conservation")
    pair_queries = [query(order, kappa, algorithm, resolution, bins=19, log_min=-3)
                    for algorithm, resolution in [("ca", 8), ("kt", 0.03)]
                    for kappa in [1, 1.5, 2] for order in range(2, 9)]
    pair_events = [[(2, 0, math.pi - 0.03), (3, 0, -math.pi + 0.07)]]
    pair_path = write_job("periodic_pair", pair_events, pair_queries)
    observed = run(pair_path, "periodic_pair")
    expected = []
    for specification in pair_queries:
        weights = [0.4 ** specification["kappa"], 0.6 ** specification["kappa"]]
        contact = sum(weight ** specification["order"] for weight in weights)
        histogram = [0.0] * 19
        histogram[0] = contact
        histogram[12] = sum(weights) ** specification["order"] - contact
        expected.append(histogram)
    compare(observed, expected, "analytic_periodic_pair")
    uncompressed_queries = [query(order, kappa, resolution=1e20)
                            for kappa in [1, 1.5, 2] for order in [2, 3, 4]]
    uncompressed_path = write_job("uncompressed", events[:4], uncompressed_queries)
    observed = run(uncompressed_path, "uncompressed")
    expected = []
    for specification in uncompressed_queries:
        histogram = [0.0] * specification["bins"]
        for event in events[:4]:
            total = sum(particle[0] for particle in event)
            weights = [(particle[0] / total) ** specification["kappa"] for particle in event]
            for indices in itertools.product(range(len(event)), repeat=specification["order"]):
                distance = 0.0
                weight = 1.0
                for first_position, first in enumerate(indices):
                    weight *= weights[first]
                    for second in indices[:first_position]:
                        delta_phi = math.remainder(event[first][2] - event[second][2], 2 * math.pi)
                        distance = max(distance, math.hypot(event[first][1] - event[second][1], delta_phi))
                bin_index = 0 if distance <= 10 ** specification["log_min"] else min(
                    specification["bins"] - 1, int((math.log10(distance) - specification["log_min"])
                                                   * specification["bins"] / -specification["log_min"]))
                histogram[bin_index] += weight / 4
        expected.append(histogram)
    compare(observed, expected, "uncompressed_ordered_tuple_reference")
    invariance_queries = [query(order, kappa, algorithm, resolution)
                          for algorithm, resolution in [("ca", 8), ("kt", 0.03)]
                          for kappa in [1, 1.37, 2] for order in [2, 5, 8]]
    baseline_path = write_job("invariance_base", events[:4], invariance_queries)
    baseline = run(baseline_path, "invariance_base")
    transformed_events = [[(particle[0] * 7, particle[1] + 0.7, particle[2] + 13 * math.pi)
                           for particle in reversed(event)] for event in events[:4]]
    transformed_queries = [dict(specification, resolution=specification["resolution"]
                                / (49 if specification["algorithm"] == "kt" else 1))
                           for specification in invariance_queries]
    transformed_path = write_job("invariance_transformed", transformed_events, transformed_queries)
    compare(run(transformed_path, "invariance_transformed"), baseline, "kinematic_and_scale_invariances")
    lines = (ROOT / "invariance_base.txt").read_text().splitlines()
    random_source.shuffle(lines)
    (ROOT / "invariance_base.txt").write_text("\n".join(lines) + "\n")
    compare(run(baseline_path, "interleaved_events"), baseline, "interleaved_and_reordered_inputs")
    axis_queries = [query(order, kappa, algorithm, resolution, bins=bins, log_min=log_min)
                    for algorithm, resolution in [("ca", 8), ("kt", 0.03)]
                    for bins, log_min in [(1, -4), (17, -2), (81, -6), (4, -0.1)]
                    for order, kappa in [(3, 1.37), (8, 1.0), (5, 2.0)]]
    axes_path = write_job("varied_axes", events[:4], axis_queries)
    compare(run(axes_path, "varied_axes"), run(axes_path, "varied_axes_oracle", True), "mixed_axes_and_clamping")
    pair_only = [query(2, kappa, algorithm, resolution)
                 for algorithm, resolution in [("ca", 8), ("kt", 0.03)]
                 for kappa in [1, 1.25, 1.5, 1.75, 2]]
    pair_only_path = write_job("order_two_only", events[:4], pair_only)
    compare(run(pair_only_path, "order_two_only"), run(pair_only_path, "order_two_only_oracle", True),
            "specialized_two_point_path")
    print("All validation checks passed.", flush=True)


if __name__ == "__main__":
    main()
