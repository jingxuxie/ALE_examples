import json
import os
import stat
from collections import Counter

from router import dependencies, hardware


class InvalidWitness(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InvalidWitness(message)


def integer(value, lower, upper, label):
    require(type(value) is int and lower <= value <= upper, f"invalid {label}")
    return value


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(value):
    raise InvalidWitness(f"nonfinite JSON value: {value}")


def load_witness(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as handle:
        metadata = os.fstat(handle.fileno())
        require(stat.S_ISREG(metadata.st_mode), "witness must be a regular file")
        require(metadata.st_size <= 1_000_000, "witness exceeds 1 MB")
        content = handle.read(1_000_001)
        require(len(content) <= 1_000_000, "witness exceeds 1 MB")
    return json.loads(content.decode("utf-8"), object_pairs_hook=unique_object,
                      parse_constant=reject_constant)


def validate_demands(witness):
    require(type(witness) is dict, "witness must be an object")
    require(set(witness) == {"version", "hardware", "gates", "route", "final_mapping"},
            "unexpected or missing witness fields")
    integer(witness["version"], 1, 1, "version")
    require(type(witness["hardware"]) is str, "hardware must be a string")
    count, edges = hardware(witness["hardware"])
    gates = witness["gates"]
    require(type(gates) is list and 48 <= len(gates) <= 200, "require 48..200 gates")
    coverage = [0] * count
    partners = [set() for _ in range(count)]
    pair_counts = Counter()
    previous = [-1] * count
    for index, gate in enumerate(gates):
        require(type(gate) is list and len(gate) == 2, "gate must be [control, target]")
        left = integer(gate[0], 0, count - 1, "gate control")
        right = integer(gate[1], 0, count - 1, "gate target")
        require(left != right, "gate operands must differ")
        require(previous[left] != previous[right] or previous[left] == -1,
                "successive gates on both wires may not repeat a pair")
        previous[left] = previous[right] = index
        coverage[left] += 1
        coverage[right] += 1
        partners[left].add(right)
        partners[right].add(left)
        pair_counts[tuple(sorted(gate))] += 1
    require(min(coverage) >= 4, "every wire needs at least four gates")
    require(max(coverage) <= min(40, (4 * len(gates) + count - 1) // count),
            "wire coverage is too concentrated")
    require(min(map(len, partners)) >= 2, "every wire needs two distinct partners")
    require(max(pair_counts.values()) <= 8, "a pair may occur at most eight times")
    reached = {0}
    pending = [0]
    while pending:
        for neighbor in partners[pending.pop()]:
            if neighbor not in reached:
                reached.add(neighbor)
                pending.append(neighbor)
    require(len(reached) == count, "logical interaction graph must be connected")
    require(len(pair_counts) >= count, "interaction graph is too small")
    return count, edges, gates


def replay(gates, count, edges, operations, final_mapping, initial=None):
    require(type(operations) is list and len(operations) <= 20_000,
            "route must contain at most 20000 operations")
    require(type(final_mapping) is list and len(final_mapping) == count,
            "final_mapping must have one entry per logical wire")
    for node in final_mapping:
        integer(node, 0, count - 1, "final mapping node")
    require(len(set(final_mapping)) == count, "final_mapping must be a permutation")
    position = list(range(count)) if initial is None else list(initial)
    occupants = [0] * count
    for qubit, node in enumerate(position):
        occupants[node] = qubit
    edge_set = {tuple(sorted(edge)) for edge in edges}
    predecessors, _ = dependencies(gates, count)
    completed = set()
    swaps = 0
    for operation in operations:
        require(type(operation) is list and len(operation) >= 1, "invalid route operation")
        kind = operation[0]
        require(type(kind) is str, "operation kind must be a string")
        if kind == "swap":
            require(len(operation) == 3, "swap must be [swap, physical_a, physical_b]")
            left = integer(operation[1], 0, count - 1, "swap endpoint")
            right = integer(operation[2], 0, count - 1, "swap endpoint")
            require(tuple(sorted((left, right))) in edge_set, "nonadjacent SWAP")
            first, second = occupants[left], occupants[right]
            occupants[left], occupants[right] = second, first
            position[first], position[second] = right, left
            swaps += 1
        elif kind == "gate":
            require(len(operation) == 4, "gate operation must include ID and physical operands")
            index = integer(operation[1], 0, len(gates) - 1, "gate ID")
            left = integer(operation[2], 0, count - 1, "physical control")
            right = integer(operation[3], 0, count - 1, "physical target")
            require(index not in completed, "duplicate gate execution")
            require(all(parent in completed for parent in predecessors[index]),
                    "per-wire gate dependency violated")
            control, target = gates[index]
            require((position[control], position[target]) == (left, right),
                    "physical operands disagree with fixed initial mapping and SWAPs")
            require(tuple(sorted((left, right))) in edge_set, "nonadjacent gate")
            completed.add(index)
        else:
            raise InvalidWitness("unknown route operation")
    require(len(completed) == len(gates), "route does not execute every gate")
    require(position == final_mapping, "incorrect final_mapping")
    return {"swaps": swaps, "native_2q": len(gates) + 3 * swaps}


def validate(witness):
    count, edges, gates = validate_demands(witness)
    costs = replay(gates, count, edges, witness["route"], witness["final_mapping"])
    require(8 <= costs["swaps"] <= 200, "reference route needs 8..200 SWAPs")
    return count, edges, gates, costs
