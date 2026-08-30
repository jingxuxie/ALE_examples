import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import sys
import time
import traceback
import warnings


sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from oracle import InvalidResult, LebesgueOracle, validate_nodes
from generator import FAMILIES, generate


class SearchBudgetExceeded(Exception):
    pass


def interrupted(signum, frame):
    raise SearchBudgetExceeded("private screening per-call CPU/wall budget")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def solve(module, case):
    cpu_started, wall_started = time.process_time(), time.monotonic()
    signal.setitimer(signal.ITIMER_PROF, 10.0)
    signal.setitimer(signal.ITIMER_REAL, 70.0)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            output = module.solve(case)
        validate_nodes(case, output)
        return {"valid_output": True, "output": output, "solve_cpu_seconds": time.process_time() - cpu_started,
                "solve_wall_seconds": time.monotonic() - wall_started}
    except Exception as error:
        return {"valid_output": False, "error": type(error).__name__ + ": " + str(error),
                "solve_cpu_seconds": time.process_time() - cpu_started,
                "solve_wall_seconds": time.monotonic() - wall_started}
    finally:
        signal.setitimer(signal.ITIMER_PROF, 0)
        signal.setitimer(signal.ITIMER_REAL, 0)


def sample_points(oracle):
    boundaries = np.unique(np.r_[0.0, oracle.nodes, oracle.nodes[-1] + 2 * oracle.degree + 4])
    grids = [boundaries]
    for left, right in zip(boundaries[:-1], boundaries[1:]):
        fraction = (1 - np.cos(np.linspace(0, math.pi, 33))) / 2
        grids.append(left + (right - left) * fraction)
        slope = max(rate + (1 / (left + poles)).sum() for rate, poles in zip(oracle.rates, oracle.poles))
        offset = 1 / slope
        grids.append(left + offset * np.expm1(np.linspace(0, math.log1p((right - left) / offset), 41)))
    return np.unique(np.concatenate(grids))


def screen(case, baseline, champion):
    oracles = {name: LebesgueOracle(case, result["output"]) for name, result in
               (("baseline", baseline), ("champion", champion)) if result["valid_output"]}
    if not oracles:
        return {}
    points = np.unique(np.concatenate([sample_points(oracle) for oracle in oracles.values()]))
    return {name: float(oracle.values(points).max()) for name, oracle in oracles.items()}


def verify(case, result):
    if not result["valid_output"]:
        return {"verified": False, "error": result["error"]}
    try:
        return {"verified": True, "enclosure": LebesgueOracle(case, result["output"]).supremum()}
    except Exception as error:
        return {"verified": False, "error": type(error).__name__ + ": " + str(error)}


def summarize(records, metadata, elapsed):
    regressions = [record for record in records if record.get("certified_regression", False)]
    invalid = [record["id"] for record in records if not record["champion"]["valid_output"]]
    overruns = [record["id"] for record in records if record["champion"]["solve_cpu_seconds"] > 7.5]
    return {**metadata, "completed_cases": len(records), "elapsed_wall_seconds": elapsed,
            "coverage": {family: sum(record["family"] == family for record in records) for family in FAMILIES},
            "certified_regressions": [{"id": record["id"], "family": record["family"],
                                       "champion_over_baseline_lower": record["champion_over_baseline_lower"]}
                                      for record in sorted(regressions, key=lambda row: -row["champion_over_baseline_lower"])],
            "invalid_champion_outputs": invalid, "champion_cpu_above_7_5_seconds": overruns,
            "runtime_scope": "imported solve functions, not isolated complete executable grading",
            "screening_scope": "sampled lower estimates are triage only; regressions require oracle enclosures",
            "target_changed": False, "hardness_classification": None}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wall-seconds", type=float, default=480)
    parser.add_argument("--cpu-seconds", type=float, default=240)
    parser.add_argument("--rounds", type=int, default=16)
    arguments = parser.parse_args()
    baseline_path = ROOT / "participant" / "baseline" / "solution.py"
    champion_path = ROOT / "attempts" / "v_1" / "solution.py"
    baseline_module = load_module("stress_baseline", baseline_path)
    champion_module = load_module("stress_champion", champion_path)
    metadata = {"seed": 20260828, "mode": "privileged_generation_only",
                "hashes": {label: hashlib.sha256(path.read_bytes()).hexdigest() for label, path in
                           (("baseline", baseline_path), ("champion", champion_path),
                            ("oracle", ROOT / "evaluator" / "oracle.py"), ("generator", HERE / "generator.py"))}}
    signal.signal(signal.SIGPROF, interrupted)
    signal.signal(signal.SIGALRM, interrupted)
    cases = generate(arguments.rounds)
    save(HERE / "generated_cases.json", cases)
    records = []
    wall_started, cpu_started = time.monotonic(), time.process_time()
    with (HERE / "screening.jsonl").open("w") as log:
        for entry in cases:
            if time.monotonic() - wall_started > arguments.wall_seconds or time.process_time() - cpu_started > arguments.cpu_seconds:
                break
            case = entry["input"]
            baseline = solve(baseline_module, case)
            champion = solve(champion_module, case)
            record = {"id": entry["id"], "family": entry["family"], "input": case,
                      "baseline": baseline, "champion": champion}
            try:
                samples = screen(case, baseline, champion)
                record["sampled_log_lower"] = samples
                regression = samples.get("champion", -math.inf) > samples.get("baseline", math.inf) + math.log(1.015)
                near_tie = samples.get("champion", -math.inf) > samples.get("baseline", math.inf) - math.log(1.03)
                should_verify = regression or (entry["round"] == 0) or (near_tie and entry["round"] < 4) or not champion["valid_output"]
                if should_verify:
                    record["baseline_verification"] = verify(case, baseline)
                    record["champion_verification"] = verify(case, champion)
                    if record["baseline_verification"]["verified"] and record["champion_verification"]["verified"]:
                        base_bound = record["baseline_verification"]["enclosure"]
                        champ_bound = record["champion_verification"]["enclosure"]
                        log_ratio = champ_bound["log_lower"] - base_bound["log_upper"]
                        record["champion_over_baseline_lower"] = math.exp(min(700, log_ratio))
                        record["certified_regression"] = log_ratio > math.log(1.005)
                    save(HERE / "cases" / (entry["id"] + ".json"), case)
                    save(HERE / "outcomes" / (entry["id"] + ".json"), record)
            except Exception as error:
                record["screening_error"] = type(error).__name__ + ": " + str(error)
                record["traceback"] = traceback.format_exc()
            records.append(record)
            log.write(json.dumps(record, allow_nan=False) + "\n")
            log.flush()
            summary = summarize(records, metadata, time.monotonic() - wall_started)
            save(HERE / "summary.json", summary)
            print(entry["id"], "CPU=%.3f" % champion["solve_cpu_seconds"],
                  "ratio=", record.get("champion_over_baseline_lower", "screen-only"),
                  "valid=", champion["valid_output"], flush=True)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
