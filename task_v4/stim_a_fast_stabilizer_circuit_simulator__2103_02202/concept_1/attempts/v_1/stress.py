import json
import os
from pathlib import Path
import random
import resource
import subprocess
import sys
import time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
ASSETS = ROOT.parent.parent / "participant"
sys.path.insert(0, str(ASSETS / "baseline"))
from solve import solve as baseline_solve
sys.path.pop(0)
sys.path.insert(0, str(ASSETS / "workspace"))
from channel import risk


def limit_memory():
    resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})


def main():
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 40.5
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 51501
    label = sys.argv[3] if len(sys.argv) > 3 else "wide"
    generator = random.Random(seed)
    directory = ROOT / ("stress_instances_" + label + "_" + str(seed))
    directory.mkdir(exist_ok=True)
    results = []
    for family in ["biased", "correlated", "drifting"]:
        instance = json.loads((ASSETS / "input" / (family + "_0.json")).read_text())
        detectors, tap_count, budget, channel_count, regime_count = {
            "wide": (28, 44, 7, 22, 6),
            "medium": (22, 40, 6, 18, 4),
            "small": (16, 28, 5, 12, 3),
        }[label]
        instance["detectors"] = detectors
        instance["budget"] = budget
        taps = [1 << position for position in range(detectors)]
        while len(taps) < tap_count:
            mask = generator.randrange(1, 1 << detectors)
            if mask not in taps:
                taps.append(mask)
        generator.shuffle(taps)
        instance["taps"] = taps
        instance["regimes"] = ["regime_" + str(index) for index in range(regime_count)]
        instance["channels"] = instance["channels"][:channel_count]
        for channel in instance["channels"]:
            channel["signatures"] = [generator.randrange(1, 1 << (detectors + 1))
                                     for branch in channel["signatures"]]
            channel["probabilities"].append([
                0.5 * (first + second) for first, second in
                zip(channel["probabilities"][0], channel["probabilities"][3])])
            channel["probabilities"] = channel["probabilities"][:regime_count]
        source = directory / (family + "_" + label + ".json")
        source.write_text(json.dumps(instance))
        baseline = max(risk(instance, baseline_solve(instance)))
        destination = directory / (family + "_answer.json")
        started = time.monotonic()
        subprocess.run([sys.executable, str(ROOT / "solve.py"), "--input", str(source),
                        "--output", str(destination), "--seconds", str(seconds)],
                       check=True, timeout=45, preexec_fn=limit_memory)
        elapsed = time.monotonic() - started
        answer = json.loads(destination.read_text())
        selected = answer["selected"]
        assert len(selected) <= instance["budget"]
        assert selected == sorted(set(selected))
        assert all(0 <= tap < len(taps) for tap in selected)
        assert len(answer["correction"]) == 1 << len(selected)
        score = max(risk(instance, answer))
        result = {"family": family, "seconds": elapsed, "baseline": baseline,
                  "score": score, "reduction": 1 - score / baseline,
                  "selected": selected}
        print(json.dumps(result), flush=True)
        results.append(result)
    (directory / "results.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
