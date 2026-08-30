import argparse
import random
from pathlib import Path

from common import CASES, verify, write_witness


def annotate(case, gates, rng):
    rows = [1 << wire for wire in range(case["n"])]
    occurrences = {parity: [] for parity in case["required_parities"]}
    for wire, row in enumerate(rows):
        if row in occurrences:
            occurrences[row].append((-1, wire))
    for index, (control, target) in enumerate(gates):
        rows[target] ^= rows[control]
        if rows[target] in occurrences:
            occurrences[rows[target]].append((index, target))
    events = {}
    for parity, places in occurrences.items():
        if not places:
            raise ValueError(parity)
        index, wire = rng.choice(places)
        events.setdefault(index, []).append((-1, wire))
    nodes = events.get(-1, [])[:]
    for index, gate in enumerate(gates):
        nodes.append(tuple(gate))
        nodes.extend(events.get(index, []))
    return nodes


def commute(first, second):
    control_a, target_a = first
    control_b, target_b = second
    if control_a == -1:
        return control_b == -1 or target_b != target_a
    if control_b == -1:
        return target_a != target_b
    return control_a != target_b and control_b != target_a


def cancel(nodes):
    changed = True
    while changed:
        changed = False
        for first, gate in enumerate(nodes):
            if gate[0] == -1:
                continue
            for second in range(first + 1, len(nodes)):
                if nodes[second] == gate:
                    del nodes[second]
                    del nodes[first]
                    changed = True
                    break
                if not commute(gate, nodes[second]):
                    break
            if changed:
                break
    return nodes


def schedule(nodes, rng):
    successors = [[] for _ in nodes]
    pending = [0] * len(nodes)
    for first, gate in enumerate(nodes):
        for second in range(first + 1, len(nodes)):
            if not commute(gate, nodes[second]):
                successors[first].append(second)
                pending[second] += 1
    critical = [0] * len(nodes)
    for index in reversed(range(len(nodes))):
        critical[index] = (nodes[index][0] != -1) + max((critical[child] for child in successors[index]), default=0)
    ready = {index for index, degree in enumerate(pending) if not degree}
    output = []
    def finish(index):
        ready.remove(index)
        for child in successors[index]:
            pending[child] -= 1
            if pending[child] == 0:
                ready.add(child)
    while ready:
        phases = [index for index in ready if nodes[index][0] == -1]
        while phases:
            for index in phases:
                finish(index)
            phases = [index for index in ready if nodes[index][0] == -1]
        candidates = sorted(ready, key=lambda index: -(critical[index] + rng.random() * 3))
        used = set()
        chosen = []
        for index in candidates:
            control, target = nodes[index]
            if control not in used and target not in used:
                chosen.append(index)
                used.update((control, target))
        for index in chosen:
            output.append(nodes[index])
            finish(index)
    return output


def optimize(case, gates, repeats=100):
    rng = random.Random(233)
    best = gates
    report = verify(case, gates)
    best_score = (report["depth"], report["count"])
    for repeat in range(repeats):
        nodes = cancel(annotate(case, best, rng))
        candidate = schedule(nodes, rng)
        report = verify(case, candidate)
        assert report["exact"] and not report["missing"]
        score = (report["depth"], report["count"])
        if score < best_score:
            best, best_score = candidate, score
    return best


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", default="best_")
    parser.add_argument("--repeats", type=int, default=100)
    args = parser.parse_args()
    for case in CASES:
        source = Path(args.prefix + case["id"] + ".txt")
        if not source.exists():
            continue
        gates = [tuple(map(int, line.split())) for line in source.read_text().splitlines()]
        before = verify(case, gates)
        gates = optimize(case, gates, args.repeats)
        after = verify(case, gates)
        Path("ordered_" + case["id"] + ".txt").write_text("".join(f"{control} {target}\n" for control, target in gates))
        print(case["id"], (before["count"], before["depth"]), "->", (after["count"], after["depth"]), flush=True)
