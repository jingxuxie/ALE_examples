"""Independent small-ring enumeration and public screening benchmarks."""

import argparse
import glob
import itertools
import json
import random
import time

import numpy as np

import solver


def brute_instance(case, channel, anchor):
    length = case["length"]
    model = case["model"]
    target = case["target"]
    result = set()
    for links in itertools.product((0, 1), repeat=length):
        if model == "u1":
            if any(links[site - 1] + links[site] == 2 for site in range(length)):
                continue
            matter = tuple(1 - links[site - 1] - links[site] for site in range(length))
        else:
            matter = tuple((1 - target[site] * (2 * links[site - 1] - 1) * (2 * links[site] - 1)) // 2 for site in range(length))
        initial = matter + links
        outputs = {}
        for term in channel["terms"]:
            states = {initial: complex(*term["amplitude"])}
            for kind, offset, name in term["ops"]:
                site = (anchor + offset) % length
                position = site + (length if kind == "l" else 0)
                matrix = solver.ELECTRIC[name] if model == "z2" and kind == "l" else solver.MATTER[name]
                updated = {}
                for state, amplitude in states.items():
                    for output in (0, 1):
                        coefficient = matrix[output][state[position]]
                        if coefficient:
                            changed = state[:position] + (output,) + state[position + 1:]
                            updated[changed] = updated.get(changed, 0) + amplitude * coefficient
                states = updated
            for state, amplitude in states.items():
                outputs[state] = outputs.get(state, 0) + amplitude
        for state, amplitude in outputs.items():
            if abs(amplitude) <= 1e-12:
                continue
            sectors, penalties = [], []
            for site in range(length):
                occupation = state[site]
                left = state[length + (site - 1) % length]
                right = state[length + site]
                if model == "u1":
                    sector = (-1) ** site * (occupation + left + right - 1)
                    penalty = sector
                else:
                    product = (2 * left - 1) * (2 * right - 1)
                    sector = (1 - 2 * occupation) * product - target[site]
                    penalty = product + 2 * target[site] * occupation - target[site]
                if sector:
                    sectors.append((site, sector))
                if penalty:
                    penalties.append((site, penalty))
            if sectors:
                result.add((tuple(sectors), tuple(penalties)))
    return result


def check_compiler(input_directory):
    generator = random.Random(7421)
    cases = []
    for filename in sorted(glob.glob(input_directory + "/*.json")):
        case = json.load(open(filename))
        case["length"] = 6
        case["target"] = case["target"][:6]
        for channel in case["channels"]:
            channel["anchors"] = [0, 1, 4, 5]
        cases.append(case)
    for index in range(80):
        model = "z2" if index % 2 else "u1"
        length = 4 if index % 3 else 6
        terms = []
        for term_index in range(generator.randrange(1, 7)):
            support = generator.sample([(kind, site) for kind in ("m", "l") for site in range(length)], generator.randrange(1, 5))
            ops = [[kind, site - length, generator.choice(list(solver.ELECTRIC if model == "z2" and kind == "l" else solver.MATTER))] for kind, site in support]
            terms.append({"amplitude": [generator.choice([-1, -0.5, 0.5, 1]), generator.choice([0, 0.5, -0.5])], "ops": ops})
        if index % 4 == 0:
            terms += [{"amplitude": [-value for value in term["amplitude"]], "ops": term["ops"]} for term in list(terms)]
        cases.append({"model": model, "length": length,
                      "target": [generator.choice([-1, 1]) if model == "z2" else 0 for site in range(length)],
                      "channels": [{"id": "random", "anchors": list(range(length)), "terms": terms}]})
    instances = 0
    for case in cases:
        certificate, rows = solver.compile_certificate(case)
        channels = {channel["id"]: channel for channel in case["channels"]}
        for entry in certificate:
            expected = brute_instance(case, channels[entry["channel"]], entry["anchor"])
            actual = {(tuple(map(tuple, transfer["sector"])), tuple(map(tuple, transfer["penalty"]))) for transfer in entry["transfers"]}
            assert actual == expected, (case, entry, expected - actual, actual - expected)
            instances += 1
    print("Compiler exact against independent global enumeration:", instances, "instances", flush=True)


def benchmark(input_directory, seconds, selected):
    for filename in sorted(glob.glob(input_directory + "/*.json")):
        if selected and selected not in filename:
            continue
        case = json.load(open(filename))
        start = time.monotonic()
        certificate, rows = solver.compile_certificate(case)
        analog, digital, phase = solver._optimize(rows, case["hardware"], seconds)
        analog_values = solver.margins(rows, analog, case["hardware"])
        digital_values = solver.margins(rows, digital, case["hardware"], phase)
        for ticks in (analog, digital):
            assert len(ticks) == case["length"]
            assert all(type(value) is int and abs(value) <= cap for value, cap in zip(ticks, case["hardware"]["caps"]))
        assert phase in case["hardware"]["phase_ticks"]
        print(json.dumps({"id": case["id"], "seconds": time.monotonic() - start,
                          "rows": len(rows), "analog": {"quality": solver._quality(analog_values), "min": float(min(analog_values)), "mean": float(np.mean(analog_values)), "ticks": analog},
                          "digital": {"quality": solver._quality(digital_values), "min": float(min(digital_values)), "mean": float(np.mean(digital_values)), "ticks": digital, "phase": phase}}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--seconds", type=float, default=3)
    parser.add_argument("--selected", default="")
    parser.add_argument("--compiler", action="store_true")
    arguments = parser.parse_args()
    if arguments.compiler:
        check_compiler(arguments.input)
    benchmark(arguments.input, arguments.seconds, arguments.selected)
