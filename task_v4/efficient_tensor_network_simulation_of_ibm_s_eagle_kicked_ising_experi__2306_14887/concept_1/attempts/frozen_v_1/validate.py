import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time

import contraction


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    available = os.sched_getaffinity(0)
    os.sched_setaffinity(0, {min(available)})


def validate(instance, index):
    baseline = contraction.assess(instance, contraction.baseline_plan(instance))
    started = time.monotonic()
    process = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("solve.py"))],
        input=json.dumps(instance), text=True, capture_output=True,
        timeout=45, check=True, preexec_fn=limits,
    )
    seconds = time.monotonic() - started
    assert seconds < 45, seconds
    plan = json.loads(process.stdout)
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
        instance_path = Path(directory) / "instance.json"
        plan_path = Path(directory) / "plan.json"
        instance_path.write_text(json.dumps(instance))
        plan_path.write_text(json.dumps(plan))
        check = subprocess.run(
            [sys.executable, str(Path(contraction.__file__).with_name("check_plan.py")),
             str(instance_path), str(plan_path)],
            text=True, capture_output=True, check=True,
        )
        metrics = json.loads(check.stdout)
    assert metrics["feasible"]
    assert metrics["work"] <= baseline["work"]
    return dict(index=index, n=instance["n"], seconds=seconds,
                baseline_work=baseline["work"], work=metrics["work"],
                improvement=baseline["work"] / metrics["work"],
                peak_elements=metrics["peak_elements"], slice_bits=metrics["slice_bits"])


if __name__ == "__main__":
    instances = json.loads(Path(sys.argv[1]).read_text())
    results = []
    for index, instance in enumerate(instances):
        result = validate(instance, index)
        results.append(result)
        print(json.dumps(result), flush=True)
    report = dict(results=results,
                  geometric_mean_improvement=math.prod(result["improvement"] for result in results) ** (1 / len(results)))
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(report, indent=2) + "\n")
    print("geometric_mean_improvement", report["geometric_mean_improvement"])
