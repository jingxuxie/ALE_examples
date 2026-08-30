import json
import os
import subprocess
import sys


def main():
    executable = os.path.join(os.path.dirname(os.path.abspath(__file__)), "planner")
    process = subprocess.Popen([executable], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            instance = json.loads(line)
            state_count = (1 << instance["dimensions"]) * instance["dimensions"]
            capacity = min(instance["capacity"], sum(instance["sizes"]) * (state_count - 1))
            largest_cost = max(max(pair) for row in instance["axis_cost"] for pair in row)
            largest_cost = max(largest_cost, max(max(row) for row in instance["transpose_cost"]))
            divisor = max(1, (largest_cost + 10**12 - 1) // 10**12)
            values = [instance["dimensions"], len(instance["sizes"]), capacity, len(instance["requests"])]
            values.extend(instance["sizes"])
            for row in instance["axis_cost"]:
                for pair in row:
                    values.extend(max(1, cost // divisor) for cost in pair)
            for row in instance["transpose_cost"]:
                values.extend(max(1, cost // divisor) if cost else 0 for cost in row)
            for request in instance["requests"]:
                values.extend((request["field"], request["mask"], request["layout"], len(request["updates"])))
                values.extend(request["updates"])
            process.stdin.write(" ".join(map(str, values)) + "\n")
            process.stdin.flush()
            answer = process.stdout.readline()
            if not answer:
                raise RuntimeError("planner terminated")
            sys.stdout.write(answer)
            sys.stdout.flush()
    finally:
        process.stdin.close()
        process.wait()


if __name__ == "__main__":
    main()
