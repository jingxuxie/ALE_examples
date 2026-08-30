import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import time


def main():
    participant = Path(__file__).resolve().parents[2] / "participant"
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("validator", participant / "workspace/routing.py")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    public_baselines = json.loads((participant / "input/baseline_scores.json").read_text())
    cases = []
    for path in sorted((participant / "input").glob("public_*.json")):
        instance = json.loads(path.read_text())
        cases.append((instance, public_baselines[instance["id"]]["cost"], True))
    for family in ["chain", "ring", "grid", "ladder", "tree", "modular"]:
        for mode in [0, 1, 3, 4]:
            name = f"stress_{family}_{mode}"
            instance = json.loads((Path("stress_cases") / (name + ".json")).read_text())
            baseline = json.loads((Path("stress_cases") / (name + ".baseline.json")).read_text())
            cases.append((instance, baseline["cost"], False))

    def constrain():
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
        resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
        if hasattr(os, "sched_getaffinity"):
            os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})

    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(("ROUTE_", "BEAM_")) and key not in ("OLD_SEARCH", "NO_SIMPLIFY", "NO_BEAM_PORTFOLIO")}
    directory = Path("validated_routes")
    directory.mkdir(exist_ok=True)
    started = time.monotonic()
    summaries = {}
    ratios = {}
    public_ratios = {}
    for instance, baseline, public in cases:
        case_started = time.monotonic()
        process = subprocess.run([sys.executable, "solve.py"], input=json.dumps(instance),
                                 text=True, capture_output=True, timeout=7.8, env=environment,
                                 preexec_fn=constrain)
        elapsed = time.monotonic() - case_started
        if process.returncode:
            raise RuntimeError(f'{instance["id"]}: {process.stderr}')
        answer = json.loads(process.stdout)
        score = validator.validate(instance, answer)
        assert score["valid"] and elapsed < 8
        ratio = score["cost"] / baseline
        family = instance["family"]
        ratios.setdefault(family, []).append(ratio)
        if public:
            public_ratios.setdefault(family, []).append(ratio)
        summaries[instance["id"]] = dict(score, baseline=baseline, reduction=1-ratio, seconds=elapsed)
        (directory / (instance["id"] + ".json")).write_text(process.stdout)
        print(f'{instance["id"]:22} {score["cost"]:10.3f} reduction={100*(1-ratio):7.3f}% {elapsed:.3f}s', flush=True)
    elapsed = time.monotonic() - started

    def quality(values):
        return 1 - math.exp(sum(map(math.log, values)) / len(values))

    report = dict(cases=summaries, all_valid=True, case_count=len(cases), seconds=elapsed,
                  max_instance_seconds=max(score["seconds"] for score in summaries.values()),
                  max_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                  quality=quality([ratio for values in ratios.values() for ratio in values]),
                  family_quality={family: quality(values) for family, values in ratios.items()},
                  public_quality=quality([ratio for values in public_ratios.values() for ratio in values]),
                  public_family_quality={family: quality(values) for family, values in public_ratios.items()})
    assert elapsed < 240
    Path("validation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key != "cases"}, indent=2))


if __name__ == "__main__":
    main()
