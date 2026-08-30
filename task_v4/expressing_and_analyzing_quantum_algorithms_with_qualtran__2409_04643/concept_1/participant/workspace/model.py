import heapq
import math


def graph_arrays(case):
    count = len(case["nodes"])
    successors = [[] for _ in range(count)]
    predecessors = [[] for _ in range(count)]
    incoming = [0] * count
    outgoing = [0] * count
    indegree = [0] * count
    for source, destination, width in case["edges"]:
        successors[source].append(destination)
        predecessors[destination].append(source)
        incoming[destination] += width
        outgoing[source] += width
        indegree[destination] += 1
    return successors, predecessors, incoming, outgoing, indegree


def source_greedy_order(case):
    successors, _, incoming, outgoing, indegree = graph_arrays(case)
    priority = []
    for node in range(len(indegree)):
        if not incoming[node]:
            priority.append(10**30)
        elif not outgoing[node]:
            priority.append(-(10**30))
        else:
            priority.append(outgoing[node] - incoming[node])
    ready = [(priority[node], node) for node, degree in enumerate(indegree) if not degree]
    heapq.heapify(ready)
    order = []
    while ready:
        _, node = heapq.heappop(ready)
        order.append(node)
        for successor in successors[node]:
            indegree[successor] -= 1
            if not indegree[successor]:
                heapq.heappush(ready, (priority[successor], successor))
    if len(order) != len(indegree):
        raise ValueError("cyclic graph")
    return order


def baseline_order(case):
    import json
    from pathlib import Path
    schedules = json.loads((Path(__file__).resolve().parents[1] / "baseline/schedules.json").read_text())["schedules"]
    if case.get("id") in schedules:
        return schedules[case["id"]].copy()
    return source_greedy_order(case)


def metrics(case, order):
    count = len(case["nodes"])
    if not isinstance(order, list) or len(order) != count:
        raise ValueError("schedule must contain every node")
    if any(type(node) is not int for node in order) or set(order) != set(range(count)):
        raise ValueError("schedule is not an integer permutation")
    positions = [0] * count
    for position, node in enumerate(order):
        positions[node] = position
    for source, destination, _ in case["edges"]:
        if positions[source] >= positions[destination]:
            raise ValueError("dependency violation")
    _, _, incoming, outgoing, _ = graph_arrays(case)
    live = 0
    peak = 0
    area = 0
    for node in order:
        operation = case["nodes"][node]
        footprint = live - incoming[node] + max(incoming[node], outgoing[node]) + operation["workspace"]
        area += operation["duration"] * footprint
        live += outgoing[node] - incoming[node]
        peak = max(peak, footprint, live)
    if live != 0:
        raise ValueError("unconsumed registers")
    return {"peak": peak, "qubit_time": area}


def improvement(before, after):
    return math.exp(0.7 * math.log(before["peak"] / after["peak"]) +
                    0.3 * math.log(before["qubit_time"] / after["qubit_time"]))
