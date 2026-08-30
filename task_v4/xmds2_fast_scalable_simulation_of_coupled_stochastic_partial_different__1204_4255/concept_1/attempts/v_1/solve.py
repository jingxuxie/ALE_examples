import heapq
import json
import math
from pathlib import Path
import subprocess
import sys


def baseline_plan(instance):
    actions = []
    dimensions = instance["dimensions"]
    sizes = instance["sizes"]
    requests = instance["requests"]
    cache = {(field, 0, 0) for field in range(len(sizes))}
    tables = {}

    def next_use(key, position):
        for future in range(position, len(requests)):
            request = requests[future]
            if key == (request["field"], request["mask"], request["layout"]):
                return future - position
            if key[0] in request["updates"]:
                break
        return len(requests) + 1

    for position, request in enumerate(requests):
        field = request["field"]
        wanted = (field, request["mask"], request["layout"])
        if wanted not in cache:
            target = wanted[1:]
            if target not in tables:
                distance = [math.inf] * ((1 << dimensions) * dimensions)
                successor = [None] * len(distance)
                target_index = target[0] * dimensions + target[1]
                distance[target_index] = 0
                queue = [(0, target_index)]
                while queue:
                    cost, index = heapq.heappop(queue)
                    if cost != distance[index]:
                        continue
                    mask, layout = divmod(index, dimensions)
                    edges = []
                    for axis in range(dimensions):
                        if axis != layout:
                            previous_mask = mask ^ (1 << axis)
                            edges.append((previous_mask * dimensions + layout, instance["axis_cost"][layout][axis][(previous_mask >> axis) & 1]))
                    for previous_layout in range(dimensions):
                        if previous_layout != layout:
                            edges.append((mask * dimensions + previous_layout, instance["transpose_cost"][previous_layout][layout]))
                    for previous, weight in edges:
                        alternative = cost + weight
                        if alternative < distance[previous]:
                            distance[previous] = alternative
                            successor[previous] = index
                            if previous:
                                heapq.heappush(queue, (alternative, previous))
                tables[target] = distance, successor
            distance, successor = tables[target]
            source = min((key for key in cache if key[0] == field), key=lambda key: (distance[key[1] * dimensions + key[2]], key))
            while source != wanted:
                mask, layout = divmod(successor[source[1] * dimensions + source[2]], dimensions)
                destination = (field, mask, layout)
                keep = True
                while sum(sizes[key[0]] for key in cache if key[1:] != (0, 0)) + sizes[field] > instance["capacity"]:
                    victim = max((key for key in cache if key[1:] != (0, 0)), key=lambda key: (next_use(key, position + 1), sizes[key[0]], key))
                    cache.remove(victim)
                    if victim == source:
                        keep = False
                    else:
                        actions.append(["drop", *victim])
                if source[2] == layout:
                    actions.append(["axis", *source, (source[1] ^ mask).bit_length() - 1, keep])
                else:
                    actions.append(["transpose", *source, layout, keep])
                cache.add(destination)
                source = destination
        actions.append(["read"])
        cache = {key for key in cache if key[1:] == (0, 0) or key[0] not in request["updates"]}
    return {"actions": actions}


def main():
    executable = Path(__file__).resolve().with_name("planner")
    process = subprocess.Popen([str(executable)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            instance = json.loads(line)
            dimensions = instance["dimensions"]
            sizes = instance["sizes"]
            requests = instance["requests"]
            axis_costs = [value for row in instance["axis_cost"] for pair in row for value in pair]
            transpose_costs = [value for row in instance["transpose_cost"] for value in row]
            if max(axis_costs + transpose_costs) > 1000000:
                divisor = 0
                for value in axis_costs + transpose_costs:
                    divisor = math.gcd(divisor, value)
                if divisor > 1:
                    axis_costs = [value // divisor for value in axis_costs]
                    transpose_costs = [value // divisor for value in transpose_costs]
                if max(axis_costs + transpose_costs) > 1000000:
                    print(json.dumps(baseline_plan(instance), separators=(",", ":")), flush=True)
                    continue
            capacity = min(instance["capacity"], (1 << dimensions) * dimensions * sum(sizes))
            values = [dimensions, len(sizes), capacity, len(requests)] + sizes + axis_costs + transpose_costs
            for request in requests:
                updates = sum(1 << field for field in set(request["updates"]))
                values += [request["field"], request["mask"], request["layout"], updates]
            process.stdin.write(" ".join(map(str, values)) + "\n")
            process.stdin.flush()
            answer = process.stdout.readline()
            if not answer:
                raise RuntimeError("planner terminated unexpectedly")
            sys.stdout.write(answer)
            sys.stdout.flush()
    finally:
        process.stdin.close()
        process.wait()


if __name__ == "__main__":
    main()
