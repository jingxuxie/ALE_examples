import json
import math
from pathlib import Path
import sys


def cost_from_stats(case, mask, kind_mask, count):
    width = mask.bit_count()
    specialized = kind_mask in (2, 4)
    arithmetic = 1 if specialized else 2 ** width
    hardware = case["hardware"]
    minimum = (mask & -mask).bit_length() - 1
    stride = 1 + hardware["stride_penalty"] * max(0, minimum - hardware["cache_qubits"])
    update = hardware["launch"] + max(hardware["memory"] * stride, arithmetic * hardware["compute"])
    entries = 2 ** width if specialized else 4 ** width
    return case["repetitions"] * update + hardware["build"] * (count - 1) * entries


def partition(case, order):
    count = len(order)
    gates = case["gates"]
    masks = [sum(1 << qubit for qubit in gate["qubits"]) for gate in gates]
    kinds = [{"dense": 1, "diagonal": 2, "permutation": 4}[gate["kind"]] for gate in gates]
    best = [math.inf] * (count + 1)
    following = [None] * count
    best[count] = 0.0
    for start in range(count - 1, -1, -1):
        mask = 0
        kind_mask = 0
        epoch = gates[order[start]]["epoch"]
        for stop in range(start, min(count, start + case["max_block_operations"])):
            index = order[stop]
            mask |= masks[index]
            kind_mask |= kinds[index]
            if mask.bit_count() > case["max_block_qubits"] or gates[index]["epoch"] != epoch:
                break
            value = cost_from_stats(case, mask, kind_mask, stop - start + 1) + best[stop + 1]
            if value < best[start]:
                best[start] = value
                following[start] = stop + 1
    blocks = []
    start = 0
    while start < count:
        stop = following[start]
        blocks.append(order[start:stop])
        start = stop
    return best[0], blocks


def reordered(case, window, preference):
    gates = case["gates"]
    masks = [sum(1 << qubit for qubit in gate["qubits"]) for gate in gates]
    children = [[] for _ in gates]
    unmet = [0] * len(gates)
    previous = {}
    epochs = {}
    for index, gate in enumerate(gates):
        dependencies = {previous[qubit] for qubit in gate["qubits"] if qubit in previous}
        unmet[index] = len(dependencies)
        for parent in dependencies:
            children[parent].append(index)
        for qubit in gate["qubits"]:
            previous[qubit] = index
        epochs.setdefault(gate["epoch"], []).append(index)
    order = []
    for epoch in sorted(epochs):
        members = epochs[epoch]
        ready = {index for index in members if unmet[index] == 0}
        history = []
        while ready:
            recent = 0
            for index in history[-window:]:
                recent |= masks[index]
            def priority(index):
                extra = (masks[index] & ~recent).bit_count()
                overlap = (masks[index] & recent).bit_count()
                specialized = 0 if gates[index]["kind"] == preference else 1
                return (extra, specialized, -overlap, index)
            chosen = min(ready, key=priority)
            ready.remove(chosen)
            order.append(chosen)
            history.append(chosen)
            for child in children[chosen]:
                unmet[child] -= 1
                if unmet[child] == 0 and gates[child]["epoch"] == epoch:
                    ready.add(child)
    return order


def plan(case):
    winner = partition(case, list(range(len(case["gates"]))))
    for window in (1, 3, 6):
        for preference in ("dense", "diagonal"):
            candidate = partition(case, reordered(case, window, preference))
            if candidate[0] < winner[0]:
                winner = candidate
    return winner[1]


if __name__ == "__main__":
    request = json.loads(Path(sys.argv[1]).read_text())
    response = {"schedules": {case["id"]: plan(case) for case in request["cases"]}}
    Path(sys.argv[2]).write_text(json.dumps(response))
