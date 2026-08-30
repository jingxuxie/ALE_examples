import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
WORKSPACE = Path("/task/workspace")
if not WORKSPACE.exists():
    WORKSPACE = HERE.parents[2] / "participant" / "workspace"
sys.path.insert(0, str(WORKSPACE))
from model import check
from baseline import plan as baseline_plan


def encode(instance, protocol):
    dimensions = instance["dimensions"]
    state_count = (1 << dimensions) * dimensions
    capacity = min(instance["capacity"], sum(instance["sizes"]) * (state_count - 1))
    largest_cost = max(value for row in instance["axis_cost"] for pair in row for value in pair)
    largest_cost = max(largest_cost, max(value for row in instance["transpose_cost"] for value in row))
    limit = 10 ** 6 if protocol == "v1" else 10 ** 12
    divisor = max(1, (largest_cost + limit - 1) // limit)
    values = [dimensions, len(instance["sizes"]), capacity, len(instance["requests"])]
    values.extend(instance["sizes"])
    values.extend(max(1, value // divisor) for row in instance["axis_cost"] for pair in row for value in pair)
    values.extend(max(1, value // divisor) if value else 0 for row in instance["transpose_cost"] for value in row)
    for request in instance["requests"]:
        values.extend([request["field"], request["mask"], request["layout"]])
        if protocol == "v1":
            values.append(sum(1 << field for field in set(request["updates"])))
        else:
            values.append(len(request["updates"]))
            values.extend(request["updates"])
    return " ".join(map(str, values)) + "\n"


def main():
    started = time.monotonic()
    configs = json.loads((HERE / "config.json").read_text())
    base_environment = {key: value for key, value in os.environ.items() if not key.startswith(("PLANNER_", "REFINE_"))}
    for line in sys.stdin:
        if not line.strip():
            continue
        instance = json.loads(line)
        best = baseline_plan(instance)
        best_cost = check(instance, best)["cost"]
        for config in configs:
            remaining = 109.0 - (time.monotonic() - started)
            if remaining <= 0.1:
                break
            environment = dict(base_environment)
            environment.update({key: str(value) for key, value in config["env"].items()})
            try:
                run = subprocess.run([str(HERE / config["binary"])], input=encode(instance, config["protocol"]), capture_output=True, text=True, env=environment, timeout=remaining)
                if run.returncode:
                    continue
                answer = json.loads(run.stdout)
                cost = check(instance, answer)["cost"]
                if cost < best_cost:
                    best, best_cost = answer, cost
            except (subprocess.TimeoutExpired, ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError):
                continue
        print(json.dumps(best, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
