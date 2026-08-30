import json
import os
import subprocess
import sys
import time

from contraction import assess


def solve(instance):
    started = time.monotonic()
    if instance["n"] < 3:
        from contraction import baseline_plan
        return baseline_plan(instance)
    best = {"slices": list(range(len(instance["edges"]))), "merges": []}
    current = 0
    for vertex in range(1, instance["n"]):
        best["merges"].append([current, vertex])
        current = instance["n"] + vertex - 1
    best_metrics = assess(instance, best)
    rows = [f"{instance['n']} {len(instance['edges'])} {instance['memory_elements']}"]
    rows.extend(f"{edge['u']} {edge['v']} {edge['dim'].bit_length() - 1}" for edge in instance['edges'])
    seconds = min(float(os.environ.get("SEARCH_SECONDS", "36")), 36 - (time.monotonic() - started))
    output = ""
    try:
        result = subprocess.run(
            [os.path.join(os.path.dirname(os.path.abspath(__file__)), "optimizer"), str(max(0, seconds))],
            input="\n".join(rows) + "\n", text=True, capture_output=True,
            timeout=max(5, seconds + 2),
        )
        output = result.stdout
        if os.environ.get("SEARCH_DEBUG"):
            print(result.stderr, file=sys.stderr, end="")
    except subprocess.TimeoutExpired as error:
        output = error.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError):
        pass
    for line in output.splitlines():
        try:
            candidate = json.loads(line)
            metrics = assess(instance, candidate)
        except (ValueError, TypeError, KeyError):
            continue
        if metrics["feasible"] and metrics["work"] < best_metrics["work"]:
            best, best_metrics = candidate, metrics
    return best


if __name__ == "__main__":
    print(json.dumps(solve(json.load(sys.stdin)), separators=(",", ":")))
