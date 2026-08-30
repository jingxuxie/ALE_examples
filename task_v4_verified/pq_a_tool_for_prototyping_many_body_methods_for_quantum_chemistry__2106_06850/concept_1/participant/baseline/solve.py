import argparse
import itertools
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))
from contract import validate, volume


def pareto(records):
    records.sort(key=lambda record: (record[0], record[1]))
    frontier = []
    peak = math.inf
    for record in records:
        if record[1] < peak:
            frontier.append(record)
            peak = record[1]
    return frontier


def term_frontier(case, term):
    inputs = term["inputs"]
    count = len(inputs)
    complete = (1 << count) - 1
    dimensions = case["dimensions"]
    types = case["index_types"]
    boundaries = {}
    sizes = {}
    table = {}
    for mask in range(1, complete + 1):
        inside = set().union(*(set(inputs[position][1]) for position in range(count) if mask >> position & 1))
        outside = set(term["output"]).union(*(set(inputs[position][1]) for position in range(count) if not mask >> position & 1))
        boundary = "".join(sorted(inside & outside))
        boundaries[mask] = boundary
        sizes[mask] = volume(boundary, types, dimensions) if mask & (mask - 1) else 0
        if not mask & (mask - 1):
            position = mask.bit_length() - 1
            if set(inputs[position][1]) != set(boundary):
                raise ValueError("unsupported trace input")
            table[mask] = [(0, 0, position)]
            continue
        choices = []
        left = (mask - 1) & mask
        while left:
            right = mask ^ left
            if left < right:
                axes = set(boundaries[left]) | set(boundaries[right])
                work = volume(axes, types, dimensions) * (2 if axes - set(boundary) else 1)
                for first, second in itertools.product(table[left], table[right]):
                    allocation = sizes[left] + sizes[right] + sizes[mask]
                    peak_left = max(first[1], sizes[left] + second[1], allocation)
                    peak_right = max(second[1], sizes[right] + first[1], allocation)
                    order = (first[2], second[2]) if peak_left <= peak_right else (second[2], first[2])
                    choices.append((first[0] + second[0] + work, min(peak_left, peak_right), (order, boundary)))
            left = (left - 1) & mask
        table[mask] = pareto(choices)
    return table[complete]


def solve(case):
    steps = []
    counter = itertools.count()
    for term_number, term in enumerate(case["terms"]):
        feasible = [entry for entry in term_frontier(case, term) if entry[1] <= case["memory_cap"]]
        if not feasible:
            raise ValueError("no feasible independent contraction")
        tree = min(feasible, key=lambda entry: (entry[0], entry[1]))[2]

        def emit(node):
            if isinstance(node, int):
                return list(term["inputs"][node]), False
            children, boundary = node
            first, first_temp = emit(children[0])
            second, second_temp = emit(children[1])
            name = "tmp_" + str(next(counter))
            steps.append({"id": name, "inputs": [first, second], "output": boundary})
            if first_temp:
                steps.append({"delete": first[0]})
            if second_temp:
                steps.append({"delete": second[0]})
            return [name, boundary], True

        reference, temporary = emit(tree)
        steps.append({"emit": term_number, "input": reference, "output": term["output"]})
        if temporary:
            steps.append({"delete": reference[0]})
    return {"steps": steps}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()
    case = json.load(open(args.input))
    plan = solve(case)
    validate(case, plan)
    Path(args.output).write_text(json.dumps(plan))


if __name__ == "__main__":
    main()
