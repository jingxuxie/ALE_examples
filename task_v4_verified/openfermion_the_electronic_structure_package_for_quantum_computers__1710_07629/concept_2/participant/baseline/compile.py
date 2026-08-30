"""Exact occupied-frame elimination, edge routing, and ASAP scheduling."""

import argparse
from collections import deque
import json
import math
from pathlib import Path
import sys

import numpy as np


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))
from simulator import apply_gate, projector


def shortest_path(edges, start, finish, size):
    neighbors = [[] for _ in range(size)]
    for first, second in edges:
        neighbors[first].append(second)
        neighbors[second].append(first)
    queue = deque([[start]])
    seen = {start}
    while queue:
        path = queue.popleft()
        if path[-1] == finish:
            return path
        for neighbor in sorted(neighbors[path[-1]]):
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(path + [neighbor])
    raise ValueError("disconnected hardware")


def route(gate, instance):
    path = shortest_path(instance["edges"], gate["u"], gate["v"], instance["n_modes"])
    transport = [{"u": path[index], "v": path[index + 1], "theta": math.pi / 2, "phi": 0.0}
                 for index in range(len(path) - 2)]
    center = dict(gate, u=path[-2], v=path[-1])
    restore = [dict(step, theta=-step["theta"]) for step in reversed(transport)]
    return transport + [center] + restore


def schedule(gates, size):
    last_layer = [-1] * size
    layers = []
    for gate in gates:
        first, second = gate["u"], gate["v"]
        layer_index = 1 + max(last_layer[first], last_layer[second])
        while len(layers) <= layer_index:
            layers.append([])
        layers[layer_index].append(gate)
        last_layer[first] = last_layer[second] = layer_index
    return layers


def compile_instance(instance):
    _, frame = np.linalg.eigh(projector(instance))
    frame = frame[:, -instance["n_particles"]:].copy()
    occupied = instance["initial_occupied"]
    ordering = occupied + [mode for mode in range(instance["n_modes"]) if mode not in occupied]
    elimination = []
    for column, first in enumerate(occupied):
        for second in ordering[column + 1:]:
            upper, lower = frame[first, column], frame[second, column]
            if abs(lower) < 2e-14:
                continue
            angle = math.atan2(abs(lower), abs(upper))
            phase = float(np.angle(-lower / upper)) if abs(upper) > 1e-30 else 0.0
            gate = {"u": first, "v": second, "theta": angle, "phi": phase}
            apply_gate(frame, gate)
            elimination.append(gate)
    native = []
    for gate in reversed(elimination):
        native.extend(route(dict(gate, theta=-gate["theta"]), instance))
    circuit = {"id": instance["id"], "layers": schedule(native, instance["n_modes"])}
    diagnostic = {"id": instance["id"], "logical_gates": len(elimination),
                  "routed_gates": len(native), "scheduled_depth": len(circuit["layers"])}
    return circuit, diagnostic


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(__file__).resolve().parents[1] / "input/instances.json")
    parser.add_argument("--output-dir", type=Path, required=True)
    arguments = parser.parse_args()
    instances = json.loads(arguments.input.read_text())["instances"]
    compiled = [compile_instance(instance) for instance in instances]
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    solution = {"version": 1, "circuits": [result[0] for result in compiled]}
    (arguments.output_dir / "solution.json").write_text(json.dumps(solution, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"compiler": "occupied-frame elimination with signed-swap routing",
                      "instances": [result[1] for result in compiled]}, indent=2))


if __name__ == "__main__":
    main()
