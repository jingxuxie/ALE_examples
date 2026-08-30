import json
import math
import sys


def exchange(message):
    print(json.dumps(message, allow_nan=False), flush=True)
    line = sys.stdin.readline()
    if not line:
        raise RuntimeError("evaluator_closed")
    response = json.loads(line)
    if response["type"] == "error":
        raise RuntimeError(response["reason"])
    return response


def main():
    hello = json.loads(sys.stdin.readline())
    edge_count = len(hello["edges"])
    budget = hello["limits"]["shots_budget"]
    control_count = min(edge_count + 1, budget // (2 * hello["limits"]["min_shots"]))
    measured_count = max(0, control_count - 1)
    selected_edges = [index * edge_count // measured_count for index in range(measured_count)]
    controls = [[]] + [[edge] for edge in selected_edges]
    shots = min(4096, budget // (2 * len(controls)))
    rates = []
    floor = 2.0 ** (-hello["qubits"])
    for matching in controls:
        depth = 256 if not matching else 128
        reference = exchange({"type": "experiment", "matching": matching, "depth": 0, "shots": shots})
        decayed = exchange({"type": "experiment", "matching": matching, "depth": depth, "shots": shots})
        reference_probability = (reference["successes"] + 0.5) / (shots + 1.0)
        decayed_probability = (decayed["successes"] + 0.5) / (shots + 1.0)
        ratio = max(1e-8, decayed_probability - floor) / max(1e-8, reference_probability - floor)
        rates.append(max(0.0, -math.log(ratio) / depth))
    idle = rates[0]
    measured_base = [max(0.0, rate - idle) for rate in rates[1:]]
    average_base = sum(measured_base) / max(1, len(measured_base))
    base = [average_base] * edge_count
    for edge, rate in zip(selected_edges, measured_base):
        base[edge] = rate
    targets = exchange({"type": "ready"})
    predictions = [(1.0 - 4.0 ** (-hello["qubits"])) *
                   (-math.expm1(-(idle + sum(base[edge] for edge in matching))))
                   for matching in targets["matchings"]]
    exchange({"type": "final", "predictions": predictions})


if __name__ == "__main__":
    main()
