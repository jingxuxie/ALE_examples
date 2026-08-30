import argparse
import glob
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--time", type=float, default=0.5)
    parser.add_argument("--filter", default="*")
    parser.add_argument("--tag", default="bench")
    args = parser.parse_args()
    participant = Path(__file__).resolve().parents[2] / "participant"
    spec = importlib.util.spec_from_file_location("routing", participant / "workspace/routing.py")
    checker = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(checker)
    baselines = json.loads((participant / "input/baseline_scores.json").read_text())
    directory = Path(__file__).resolve().parent / args.tag
    directory.mkdir(exist_ok=True)
    summaries = {}
    family_ratios = {}
    for filename in sorted(glob.glob(str(participant / "input" / f"public_{args.filter}.json"))):
        instance = json.loads(Path(filename).read_text())
        environment = dict(os.environ, ROUTE_TIME=str(args.time), ROUTE_DEBUG="1")
        start = time.monotonic()
        process = subprocess.run([sys.executable, "solve.py"], input=json.dumps(instance), text=True,
                                 capture_output=True, env=environment, timeout=args.time + 5)
        elapsed = time.monotonic() - start
        if process.returncode:
            raise RuntimeError(process.stderr)
        answer = json.loads(process.stdout)
        score = checker.validate(instance, answer)
        if not score["valid"]:
            raise RuntimeError(score)
        baseline = baselines[instance["id"]]["cost"]
        ratio = score["cost"] / baseline
        family_ratios.setdefault(instance["family"], []).append(ratio)
        print(f'{instance["id"]:20} {score["cost"]:9.3f} {100*(1-ratio):7.2f}% {elapsed:6.3f}s {process.stderr.splitlines()[-1]}', flush=True)
        (directory / (instance["id"] + ".json")).write_text(process.stdout)
        (directory / (instance["id"] + ".log")).write_text(process.stderr)
        summaries[instance["id"]] = dict(score, seconds=elapsed, reduction=1-ratio)
    ratios = []
    for family, values in sorted(family_ratios.items()):
        ratios.extend(values)
        print(f"{family:10} {100*(1-math.exp(sum(map(math.log,values))/len(values))):.3f}%")
    print(f"overall    {100*(1-math.exp(sum(map(math.log,ratios))/len(ratios))):.3f}%")
    (directory / "summary.json").write_text(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
