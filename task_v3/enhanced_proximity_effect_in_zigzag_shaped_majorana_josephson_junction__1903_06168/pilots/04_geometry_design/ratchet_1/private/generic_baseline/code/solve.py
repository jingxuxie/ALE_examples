import argparse
from concurrent.futures import ProcessPoolExecutor
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

import numpy as np


participant = Path(os.environ["BENCHMARK_PARTICIPANT"])
sys.path.insert(0, str(participant / "workspace"))
sys.path.insert(0, str(participant / "workspace/baseline"))
specification = importlib.util.spec_from_file_location("published_baseline", participant / "workspace/baseline/solve.py")
baseline = importlib.util.module_from_spec(specification)
sys.modules[specification.name] = baseline
specification.loader.exec_module(baseline)


def complete(record, points, count):
    if baseline.merit(record, points) <= 0:
        return False
    return all(all(float(momentum) in record["samples"][point]["values"] for momentum in np.linspace(0, np.pi, count)) for point in points)


def ranked(search, points, count):
    return [record for record in search.ranked(points) if complete(record, points, count)]


def parameters(request):
    yield None
    period = request["grid"]["period_nm"]
    for frequency in (2, 1, 3):
        wavelength = period / frequency
        for fraction in (0.2, 0.25, 0.15, 0.3, 0.1):
            for width in (100, 140, 180):
                yield dict(amplitude=round(fraction * wavelength, 3), width=width, frequency=frequency)


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    request = json.loads(Path(arguments.input).read_text())
    region = request["operating_region"]
    chemical_lower, chemical_upper = region["mu_normal_mev"]
    field_lower, field_upper = region["zeeman_mev"]
    points = [(float((point["mu_normal_mev"]-chemical_lower)/(chemical_upper-chemical_lower)),
               float((point["zeeman_mev"]-field_lower)/(field_upper-field_lower))) for point in request["operating_points"]]
    duration = min(1120.0, request["budget"]["wall_seconds"]-60.0)
    baseline.write_result(request, None, arguments.output)
    with ProcessPoolExecutor(max_workers=2) as pool:
        search = baseline.Search(request, pool, started, duration)
        candidates = [record for parameter in parameters(request) if (record := search.add(parameter)) is not None]
        search.run(candidates, points, count=5, until=started+0.45*duration)
        search.report("Dimensionless grid", points)
        leaders = ranked(search, points, 5)[:8]
        search.run(leaders, points, count=9, until=started+0.65*duration)
        leaders = ranked(search, points, 9)
        if leaders:
            baseline.write_result(request, leaders[0]["parameters"], arguments.output)
        refinements = []
        for leader in leaders[:2]:
            if leader["parameters"] is None:
                continue
            original = leader["parameters"]
            wavelength = request["grid"]["period_nm"]/original["frequency"]
            for name, shift in (("amplitude", -0.025*wavelength), ("amplitude", 0.025*wavelength), ("width", -20), ("width", 20)):
                candidate = dict(original)
                candidate[name] = round(candidate[name]+shift, 3)
                record = search.add(candidate)
                if record is not None:
                    refinements.append(record)
        search.run(refinements, points, count=9, until=started+0.84*duration)
        finalists = ranked(search, points, 9)[:3]
        if finalists:
            baseline.write_result(request, finalists[0]["parameters"], arguments.output)
        search.run(finalists, points, count=17, until=search.deadline-15)
        final = ranked(search, points, 17) or ranked(search, points, 9) or ranked(search, points, 5)
        if final:
            baseline.write_result(request, final[0]["parameters"], arguments.output)
            print(json.dumps({"elapsed_seconds": time.monotonic()-started, "parameters": final[0]["parameters"], "sampled_merit": baseline.merit(final[0], points), "geometries": len(search.records)}), flush=True)


if __name__ == "__main__":
    main()
