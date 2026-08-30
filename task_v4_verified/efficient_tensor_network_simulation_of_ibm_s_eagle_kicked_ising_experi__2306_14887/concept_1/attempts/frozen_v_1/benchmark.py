import json
import math
import sys
import time

from contraction import assess, baseline_plan
from solve import solve

instances = json.load(open(sys.argv[1]))
ratios = []
for index, instance in enumerate(instances):
    baseline = assess(instance, baseline_plan(instance))
    started = time.monotonic()
    plan = solve(instance)
    metrics = assess(instance, plan)
    ratio = baseline["work"] / metrics["work"]
    ratios.append(ratio)
    print(index, "n", instance["n"], "ratio", round(ratio, 3), "logwork", round(metrics["log2_work"], 4),
          "peak", metrics["peak_elements"], "slices", plan["slices"],
          "seconds", round(time.monotonic() - started, 3), flush=True)
print("geomean", math.prod(ratios) ** (1 / len(ratios)))
