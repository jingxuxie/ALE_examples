import itertools
from decimal import Decimal, getcontext
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np


ROOT = Path(__file__).resolve().parent
PARTICIPANT = ROOT.parent / "participant"


def wrap(angle):
    angle = math.fmod(angle, 2 * math.pi)
    if angle <= -math.pi:
        angle += 2 * math.pi
    if angle > math.pi:
        angle -= 2 * math.pi
    return angle


def delta(prefix, weight, exponent):
    if exponent == 1:
        return weight
    if prefix == 0:
        return weight ** exponent
    if weight == 0:
        return 0.0
    if isinstance(weight, Decimal):
        return (prefix + weight) ** exponent - prefix ** exponent
    return (prefix + weight) ** exponent * -math.expm1(-exponent * math.log1p(weight / prefix))


def reference(events, query, high_precision=False):
    bins, ratio_bins, phi_bins = (query[key] for key in ("bins", "ratio_bins", "phi_bins"))
    order = query["order"]
    nu1, nu2, nu3 = (query.get(key, 1.0) for key in ("nu1", "nu2", "nu3"))
    if high_precision:
        nu1, nu2, nu3 = (Decimal.from_float(float(value)) for value in (nu1, nu2, nu3))
    cell_count = ratio_bins * phi_bins
    size = bins * cell_count ** (order - 2)
    result = [Decimal(0)] * size if high_precision else np.zeros(size)

    def radial(radius):
        if radius < 10 ** query["log_min"]:
            return 0
        if radius >= 1:
            return bins - 1
        return max(1, min(bins - 2, 1 + math.floor(
            (math.log10(radius) - query["log_min"]) * (bins - 2) / -query["log_min"])))

    for event in events:
        count = len(event)
        if high_precision:
            momenta = [Decimal.from_float(particle[0]) for particle in event]
            total = sum(momenta)
            weights = [momentum / total for momentum in momenta]
        else:
            total = math.fsum(particle[0] for particle in event)
            weights = [particle[0] / total for particle in event]
        for special in range(count):
            special_weight = weights[special]
            vectors = [(particle[1] - event[special][1], wrap(particle[2] - event[special][2]))
                       for particle in event]
            radii = [math.hypot(*vector) for vector in vectors]
            ranks = sorted((index for index in range(count) if index != special),
                           key=lambda index: (radii[index], index))
            first = {}
            second = {}
            third = {}
            cells = {}
            prefix = special_weight
            for outer_rank, outer in enumerate(ranks):
                first[outer] = delta(prefix, weights[outer], nu1)
                prefix += weights[outer]
                phi_prefix = [Decimal(0) if high_precision else 0.0] * phi_bins
                phi_prefix[phi_bins // 2] = special_weight
                for inner in ranks[:outer_rank]:
                    outer_y, outer_phi = vectors[outer]
                    inner_y, inner_phi = vectors[inner]
                    angle = 0.0 if radii[inner] == 0 or radii[outer] == 0 else wrap(math.atan2(
                        outer_y * inner_phi - outer_phi * inner_y,
                        outer_y * inner_y + outer_phi * inner_phi))
                    phi_cell = min(phi_bins - 1, int((angle + math.pi) / (2 * math.pi) * phi_bins))
                    ratio = radii[inner] / radii[outer] if radii[outer] else 0.0
                    ratio_cell = min(ratio_bins - 1, int(ratio * ratio_bins))
                    cells[outer, inner] = ratio_cell * phi_bins + phi_cell
                    second[outer, inner] = delta(phi_prefix[phi_cell], weights[inner], nu2)
                    third[outer, inner] = delta(phi_prefix[phi_cell], weights[inner], nu3)
                    phi_prefix[phi_cell] += weights[inner]
            if order == 3:
                result[phi_bins // 2] += special_weight ** (1 + nu1 + nu2)
                for outer in ranks:
                    base = radial(radii[outer]) * cell_count
                    result[base + phi_bins // 2] += 2 * special_weight ** (1 + nu2) * weights[outer] ** nu1
                    result[base + (ratio_bins - 1) * phi_bins + phi_bins // 2] += special_weight * weights[outer] ** (nu1 + nu2)
                for inner, outer in itertools.combinations(ranks, 2):
                    index = radial(radii[outer]) * cell_count + cells[outer, inner]
                    result[index] += 2 * special_weight * first[outer] * second[outer, inner]
            else:
                for inner, middle, outer in itertools.combinations(ranks, 3):
                    index = ((radial(radii[outer]) * cell_count + cells[outer, middle]) * cell_count
                             + cells[middle, inner])
                    result[index] += 6 * special_weight * first[outer] * second[outer, middle] * third[middle, inner]
    return np.asarray(result, dtype=float) / len(events)


def read_events(filename):
    events = []
    current = None
    for line in Path(filename).read_text().splitlines():
        if not line.strip():
            continue
        event_id, *values = line.split()
        if event_id != current:
            events.append([])
            current = event_id
        events[-1].append(tuple(map(float, values)))
    return events


def run_case(name, events, queries, high_precision=False):
    with tempfile.TemporaryDirectory(prefix="validation-", dir=ROOT) as temporary:
        directory = Path(temporary)
        with (directory / "events.txt").open("w") as stream:
            for event_id, event in enumerate(events):
                for particle in event:
                    stream.write(f"{event_id} " + " ".join(map(repr, particle)) + "\n")
                stream.write("\n")
        job = {"kind": "resolved", "events_file": "events.txt", "nevents": len(events), "queries": queries}
        (directory / "job.json").write_text(json.dumps(job))
        subprocess.run([sys.executable, str(ROOT / "solve.py"), "--input", str(directory / "job.json"),
                        "--output", str(directory / "result.json")], check=True)
        result = json.loads((directory / "result.json").read_text())["histograms"]
        for query_index, (query, actual) in enumerate(zip(queries, result)):
            expected = reference(events, query, high_precision)
            error = np.abs(np.asarray(actual) - expected)
            print(name, query_index, "L1", error.sum(), "max", error.max(), "mass", sum(actual), flush=True)
            if error.sum() > 2e-10 * max(1.0, np.abs(expected).sum()):
                indices = np.argsort(error)[-6:]
                print([(int(index), actual[index], expected[index]) for index in indices])
                raise AssertionError(name)
        return result


def check_interface():
    events = [[(2., 0., 0.), (3., 0.2, 0.1)],
              [(1., 0., 0.), (2., 0.1, 0.), (3., 0., 0.2), (4., -0.2, -0.1)]]
    queries = [dict(order=order, bins=7, log_min=-3., ratio_bins=3, phi_bins=5) for order in (3, 4)]
    with tempfile.TemporaryDirectory(prefix="interface-", dir=ROOT) as temporary:
        directory = Path(temporary)
        data_file = directory / "events with spaces.txt"
        rows = [f"{event_id} " + " ".join(map(repr, particle))
                for event_id, event in enumerate(events) for particle in event]
        data_file.write_text("\n\n".join(rows))
        for nevents in (1, 2, 3):
            job = dict(kind="resolved", events_file=data_file.name if nevents == 1 else str(data_file),
                       nevents=nevents, queries=queries)
            (directory / "job.json").write_text(json.dumps(job))
            output = directory / f"result-{nevents}.json"
            completed = subprocess.run([sys.executable, str(ROOT / "solve.py"), "--input", "job.json",
                                        "--output", str(output)], cwd=directory, capture_output=True, text=True)
            if nevents == 3:
                assert completed.returncode != 0 and "Fewer jets than requested" in completed.stderr
                assert not output.exists()
            else:
                assert completed.returncode == 0, completed.stderr
                actual = json.loads(output.read_text())["histograms"]
                for query, histogram in zip(queries, actual):
                    expected = reference(events[:nevents], query)
                    assert np.abs(np.asarray(histogram) - expected).sum() < 1e-12
    print("Input grouping, exponent defaults, EOF, and short-input errors passed.")


def main():
    sample_job = json.loads((PARTICIPANT / "input/sample.json").read_text())
    run_case("sample", read_events(PARTICIPANT / "input/sample.txt"), sample_job["queries"])
    rng = np.random.default_rng(2807)
    events = []
    for count in range(1, 13):
        event = np.column_stack((np.exp(rng.uniform(-8, 4, count)), rng.normal(0, 0.2, count),
                                 rng.uniform(-5 * math.pi, 5 * math.pi, count)))
        events.append([tuple(map(float, particle)) for particle in event])
    events.extend([
        [(1., 0., 0.)],
        [(1., 0., 0.), (1., 0., 0.)],
        [(1., 0., 0.), (2., 0., 0.), (3., 0., 0.), (4., 0., 0.)],
        [(1., 0., 0.), (1., 1., 0.), (1., -1., 0.), (1., 0., 1.), (1., 0., -1.)],
        [(1., 0., 0.), (2., 0.001, 0.), (3., 0.01, 0.), (4., 0.1, 0.), (5., 1., 0.)],
        [(1., 0., 0.), (1., 1., 0.), (1., 1., 1.), (1., 0., 1.)],
        [(1., 0., math.pi), (2., 0.1, -math.pi), (3., 0.3, 0.), (4., -0.2, 2 * math.pi)],
        [(1e-20, 0., 0.), (1e-12, 0.1, 0.), (1., 0.2, 0.), (1e-10, 0.3, 0.), (1e-15, 0.4, 0.)],
        [(0., 0., 0.), (1., 0.1, 0.1), (2., 0.2, 0.2), (0., 0.3, 0.3), (3., 0.4, 0.4)],
    ])
    queries = []
    for ratio_bins, phi_bins in [(1, 1), (3, 3), (4, 5), (6, 8), (5, 12)]:
        for order, exponents in [(3, (1, 1, 1)), (4, (1, 1, 1)), (3, (0.65, 1.7, 1)),
                                 (4, (1.2, 0.45, 1.6)), (4, (2, 2, 2)),
                                 (3, (0.000001, 0.000002, 1)), (4, (0.01, 0.02, 0.03))]:
            queries.append(dict(order=order, bins=8, log_min=-3., ratio_bins=ratio_bins,
                                phi_bins=phi_bins, **dict(zip(("nu1", "nu2", "nu3"), exponents))))
    run_case("analytic-random", events, queries)
    two = [[(1., 0., 0.), (1., 0.1, 0.2)]]
    query = dict(order=3, bins=8, log_min=-3., ratio_bins=4, phi_bins=8, nu1=2., nu2=1.)
    result = run_case("two-particle-source-contacts", two, [query])
    assert abs(sum(result[0]) - 0.5) < 1e-14
    boundary_events = []
    boundary_queries = []
    for phi_bins in (3, 5, 6, 7, 8, 10, 12, 16):
        for boundary in range(1, phi_bins):
            angle = -math.pi + 2 * math.pi * boundary / phi_bins
            boundary_events.append([(5., 0., 0.), (4., 0.7, 0.),
                                    (3., 0.5 * math.cos(angle), 0.5 * math.sin(angle)),
                                    (2., 0.2 * math.cos(0.21), 0.2 * math.sin(0.21))])
        for order in (3, 4):
            boundary_queries.append(dict(order=order, bins=11, log_min=-4., ratio_bins=7,
                                         phi_bins=phi_bins, nu1=0.6, nu2=1.3, nu3=0.8))
    run_case("azimuth-boundaries", boundary_events, boundary_queries)
    getcontext().prec = 800
    extreme_events = [[(1., 0., 0.), (1e-100, 0.1, 0.), (2e-100, 0.2, 0.), (3e-100, 0.3, 0.)],
                      [(1., 0., 0.), (2., 0.1, 0.), (3., 0.2, 0.), (4., 0.3, 0.)]]
    extreme_queries = []
    for order, exponents in [(3, (1e100, 1.3, 1.)), (3, (1e100, 1e100, 1.)),
                             (4, (1e100, 1e100, 1e100)), (4, (2e100, 3e100, 5e100)),
                             (4, (1e100, 0.65, 0.8))]:
        extreme_queries.append(dict(order=order, bins=8, log_min=-3., ratio_bins=6, phi_bins=8,
                                    **dict(zip(("nu1", "nu2", "nu3"), exponents))))
    run_case("extreme-exponents", extreme_events, extreme_queries, high_precision=True)
    projected_queries = [dict(query, ratio_bins=1, phi_bins=1) for query in extreme_queries]
    run_case("extreme-projected", extreme_events, projected_queries, high_precision=True)
    underflow_events = [[(1e300, 0., 0.), (1e300, 0.3, 0.),
                         (1e-300, 0.1, 0.1), (2e-300, 0.2, -0.2)]]
    underflow_queries = [dict(order=order, bins=8, log_min=-3., ratio_bins=6, phi_bins=8,
                              nu1=0.8, nu2=0.001, nu3=0.001) for order in (3, 4)]
    run_case("fractional-underflow", underflow_events, underflow_queries, high_precision=True)
    check_interface()
    print("All independent enumeration checks passed.")


if __name__ == "__main__":
    main()
