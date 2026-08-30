#!/usr/bin/env python3
import json
import sys
import time

sys.dont_write_bytecode = True

try:
    from native_backend import compile_native, improve_native
except (ImportError, OSError):
    compile_native = None


def valid(instance, response):
    size = instance['n']
    rows = [1 << qubit for qubit in range(size)]
    edges = {(edge[0], edge[1]) for edge in instance['edges']}
    seen = set()
    operations = response.get('ops', [])
    if len(operations) > 100000:
        return False
    for kind, first, second in operations:
        if not 0 <= first < size:
            return False
        if kind == 'cx':
            if (first, second) not in edges:
                return False
            rows[second] ^= rows[first]
        elif kind == 'rz':
            if second in seen or not 0 <= second < len(instance['terms']):
                return False
            if rows[first] != instance['terms'][second]:
                return False
            seen.add(second)
        else:
            return False
    return len(seen) == len(instance['terms']) and rows == [1 << qubit for qubit in range(size)]


def fallback(instance):
    size = instance['n']
    neighbors = [[] for unused in range(size)]
    for control, target, weight, duration in instance['edges']:
        neighbors[target].append((weight + 0.2 * duration, control))
    for neighborhood in neighbors:
        neighborhood.sort()
    operations = []
    for term, mask in enumerate(instance['terms']):
        root = (mask & -mask).bit_length() - 1
        parents = [-1] * size
        parents[root] = root
        order = [root]
        for vertex in order:
            for unused, neighbor in neighbors[vertex]:
                if parents[neighbor] < 0:
                    parents[neighbor] = vertex
                    order.append(neighbor)
        included = {root}
        for vertex in range(size):
            if mask & (1 << vertex):
                while vertex not in included:
                    included.add(vertex)
                    vertex = parents[vertex]
        order = [vertex for vertex in order if vertex in included]
        sequence = [['cx', vertex, parents[vertex]] for vertex in order[1:]
                    if not mask & (1 << vertex)]
        sequence.extend(['cx', vertex, parents[vertex]] for vertex in reversed(order[1:]))
        operations.extend(sequence)
        operations.append(['rz', root, term])
        operations.extend(reversed(sequence))
    return {'ops': operations}


def compile_circuit(instance, budget=11.8):
    started = time.monotonic()
    response = None
    if compile_native is not None and any(mask & (mask - 1) for mask in instance['terms']):
        try:
            response, unused = compile_native(instance, budget)
            available = min(0.4, max(0.0, 13.0 - (time.monotonic() - started)))
            if available > 0.02:
                response, unused = improve_native(instance, response, available, True)
            if not valid(instance, response):
                response = None
        except Exception:
            response = None
    if response is None:
        response = fallback(instance)
    if not any(operation[0] == 'cx' for operation in response['ops']):
        control, target, unused_weight, unused_duration = min(instance['edges'], key=lambda edge: edge[2] + 0.2 * edge[3])
        response['ops'].extend([['cx', control, target], ['cx', control, target]])
    return response


def main():
    for line in sys.stdin:
        if line.strip():
            response = compile_circuit(json.loads(line))
            print(json.dumps(response, separators=(',', ':')), flush=True)


if __name__ == '__main__':
    main()
