"""Reproducible randomized accuracy and timing cross-checks."""

import json
from pathlib import Path
import time

import numpy as np

import solve
from test_solve import decode, encode, make_afm, make_legendre, reference_afm, reference_legendre, reference_time


def main():
    random = np.random.default_rng(104729)
    errors = {}
    timings = {}
    counts = {}
    for family in ("fourier", "afm", "legendre"):
        trials = 100 if family != "afm" else 24
        family_errors = {}
        maximum_time = 0
        for trial in range(trials):
            if family == "fourier":
                count = int(random.integers(1, 41))
                intervals = int(random.integers(2 * count + 1, 513))
                beta = float(random.uniform(1, 40))
                channels = []
                for index in range(12):
                    moments = [float(index % 3 == 0), *random.uniform(-5, 5, 2)]
                    if index % 3 == 1:
                        moments[1] = 0
                    if index % 3 == 2:
                        moments = [0, 0, 0]
                    values = random.normal(size=count) + 1j * random.normal(size=count)
                    channels.append({"sites": [0, index], "moments": moments, "iw": encode(values)})
                case = {"family": family, "beta": beta, "n_tau": intervals, "channels": channels}
                expected = {
                    "g_tau": [reference_time(beta, intervals, decode(channel["iw"]), channel["moments"]) for channel in channels],
                    "iw_roundtrip": [channel["iw"] for channel in channels],
                }
            elif family == "afm":
                case = make_afm(trial + 9000, flavors=2 * (trial % 6 + 1))
                expected = reference_afm(case)
            else:
                case = make_legendre(trial + 17000, degree=trial % 32 + 1, count=40)
                expected = reference_legendre(case)
            started = time.perf_counter()
            actual = solve.solve(case)
            maximum_time = max(maximum_time, time.perf_counter() - started)
            json.dumps(actual, allow_nan=False)
            for component in expected:
                observed = np.asarray(actual[component])
                reference = np.asarray(expected[component])
                assert observed.shape == reference.shape
                error = np.sqrt(np.mean((observed - reference)**2))
                error /= max(1, np.sqrt(np.mean(reference**2)))
                family_errors[component] = max(family_errors.get(component, 0), float(error))
                assert error < 1e-8, (family, trial, component, error)
        counts[family] = trials
        errors[family] = family_errors
        timings[family] = maximum_time
    report = {"case_counts": counts, "maximum_normalized_rms_error": errors, "maximum_solve_seconds": timings}
    text = json.dumps(report, indent=2) + "\n"
    (Path(__file__).resolve().parent / "validation_report.json").write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
