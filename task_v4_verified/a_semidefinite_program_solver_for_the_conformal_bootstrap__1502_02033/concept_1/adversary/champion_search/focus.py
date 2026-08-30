import json
import math
from pathlib import Path
import signal
import time

import numpy as np

from generator import make_scenario, validate
from sweep import HERE, ROOT, interrupted, load_module, save, screen, solve, verify


def focused_cases():
    random = np.random.default_rng(20260829)
    for index in range(32):
        degree = [48, 46, 42, 36][index % 4]
        family = ["six_scenario_boundary", "crossing_pole_models", "antagonistic_scales", "dense_log_ladder"][index % 4]
        scenarios = []
        for position, shift in enumerate(np.linspace(-1, 1, 6)):
            if family == "six_scenario_boundary":
                pole = 10 ** (-6 + (index // 4) * 0.4)
                poles = [pole * math.exp(0.5 * shift)] * 24
                rate = 0.023 * math.exp(0.12 * shift)
            elif family == "crossing_pole_models":
                multiplicity = int(round(position * 24 / 5))
                pole = 10 ** random.uniform(-5.9, -3.0)
                poles = [pole] * multiplicity
                rate = 0.022 * (200 ** ((1 - shift) / 2))
            elif family == "antagonistic_scales":
                poles = [10 ** (-5.9 + 9 * position / 5)] * 24
                rate = 0.021 * (220 ** ((1 - shift) / 2))
            else:
                centers = np.geomspace(1.1e-6, 9500, 6)
                allocation = random.multinomial(24, random.dirichlet(np.ones(6) * 2))
                poles = [center * math.exp(0.15 * shift) for center, count in zip(centers, allocation) for repeat in range(count)]
                rate = 10 ** random.uniform(-1.65, 0.65)
            scenarios.append(make_scenario(rate, poles))
        case = {"degree": degree, "scenarios": scenarios}
        validate(case)
        yield {"id": "%s_%02d" % (family, index), "family": family, "input": case}


def main():
    signal.signal(signal.SIGPROF, interrupted)
    signal.signal(signal.SIGALRM, interrupted)
    baseline = load_module("focus_baseline", ROOT / "participant" / "baseline" / "solution.py")
    champion = load_module("focus_champion", ROOT / "attempts" / "v_1" / "solution.py")
    started = time.monotonic()
    records = []
    entries = list(focused_cases())
    save(HERE / "focused_cases.json", entries)
    with (HERE / "focused_screening.jsonl").open("w") as handle:
        for entry in entries:
            if time.monotonic() - started > 180:
                break
            case = entry["input"]
            record = {**entry, "baseline": solve(baseline, case), "champion": solve(champion, case)}
            try:
                sampled = screen(case, record["baseline"], record["champion"])
                record["sampled_log_lower"] = sampled
                candidate_regression = sampled.get("champion", -math.inf) > sampled.get("baseline", math.inf) - math.log(1.01)
                if candidate_regression or not record["champion"]["valid_output"]:
                    record["baseline_verification"] = verify(case, record["baseline"])
                    record["champion_verification"] = verify(case, record["champion"])
                    if all(record[name + "_verification"]["verified"] for name in ("baseline", "champion")):
                        numerator = record["champion_verification"]["enclosure"]["log_lower"]
                        denominator = record["baseline_verification"]["enclosure"]["log_upper"]
                        record["champion_over_baseline_lower"] = math.exp(min(700, numerator - denominator))
                        record["certified_regression"] = numerator > denominator + math.log(1.005)
                    save(HERE / "cases" / (entry["id"] + ".json"), case)
                    save(HERE / "outcomes" / (entry["id"] + ".json"), record)
            except Exception as error:
                record["screening_error"] = type(error).__name__ + ": " + str(error)
            records.append(record)
            handle.write(json.dumps(record, allow_nan=False) + "\n")
            handle.flush()
            print(entry["id"], "CPU=%.3f" % record["champion"]["solve_cpu_seconds"],
                  "ratio=", record.get("champion_over_baseline_lower", "screen-only"),
                  "valid=", record["champion"]["valid_output"], flush=True)
    save(HERE / "focused_summary.json", {"seed": 20260829, "completed": len(records),
         "wall_seconds": time.monotonic() - started,
         "regressions": [record["id"] for record in records if record.get("certified_regression")],
         "invalid": [record["id"] for record in records if not record["champion"]["valid_output"]]})


if __name__ == "__main__":
    main()
