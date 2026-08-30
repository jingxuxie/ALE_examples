import argparse
import json
import random
from pathlib import Path


WORDS = ("I", "H", "S", "HS", "SH", "HSH")


def random_circuit(family, rng):
    layers = []
    for _ in range(family["max_rounds"]):
        best = []
        for _ in range(5):
            edges = [edge[:] for edge in family["edges"]]
            rng.shuffle(edges)
            occupied = set()
            selected = []
            for first, second in edges:
                if first not in occupied and second not in occupied:
                    selected.append([first, second] if rng.randrange(2) else [second, first])
                    occupied.update((first, second))
            if len(selected) > len(best):
                best = selected
        layers.append({"local": [rng.choice(WORDS) for _ in range(family["n"])], "cx": best})
    excess = sum(len(layer["cx"]) for layer in layers) - family["max_cx"]
    while excess > 0:
        layer = rng.choice(layers)
        if layer["cx"]:
            del layer["cx"][rng.randrange(len(layer["cx"]))]
            excess -= 1
    return {"family": family["id"], "layers": layers}


def propagate(n, packed, layers, inverse=False):
    xbits = packed & ((1 << n) - 1)
    zbits = packed >> n
    ordered = reversed(layers) if inverse else layers
    for layer in ordered:
        if inverse:
            for control, target in reversed(layer["cx"]):
                xbits ^= ((xbits >> control) & 1) << target
                zbits ^= ((zbits >> target) & 1) << control
        for qubit, word in enumerate(layer["local"]):
            for gate in reversed(word) if inverse else word:
                if gate == "H":
                    difference = ((xbits ^ zbits) >> qubit) & 1
                    xbits ^= difference << qubit
                    zbits ^= difference << qubit
                elif gate == "S":
                    zbits ^= ((xbits >> qubit) & 1) << qubit
        if not inverse:
            for control, target in layer["cx"]:
                xbits ^= ((xbits >> control) & 1) << target
                zbits ^= ((zbits >> target) & 1) << control
    return xbits | (zbits << n)


def measurements(family, circuit):
    n = family["n"]
    mask = (1 << n) - 1
    measurements = []
    for inverse in (False, True):
        images = []
        for qubit in range(n):
            images.extend(propagate(n, packed, circuit["layers"], inverse)
                          for packed in (1 << qubit, (1 << qubit) | (1 << (n + qubit)), 1 << (n + qubit)))
        singles = [((image | (image >> n)) & mask).bit_count() for image in images]
        doubles = []
        for first in range(n):
            for second in range(first + 1, n):
                for first_axis in range(3):
                    for second_axis in range(3):
                        image = images[3 * first + first_axis] ^ images[3 * second + second_axis]
                        doubles.append(((image | (image >> n)) & mask).bit_count())
        measurements.extend((singles, doubles))
    return measurements


def ranking(family, circuit):
    samples = measurements(family, circuit)
    targets = family["targets"]
    ratios = []
    for index, values in enumerate(samples):
        kind = "single" if index % 2 == 0 else "double"
        ratios.extend((min(values) / targets["min_" + kind],
                       1000 * sum(values) / (len(values) * targets["mean_" + kind + "_milli"])))
    return min(ratios), sum(min(values) for values in samples), sum(sum(values) / len(values) for values in samples)


def main():
    parser = argparse.ArgumentParser(description="Deterministic random-restart reference, not a witness of feasibility.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=211209853)
    parser.add_argument("--trials", type=int, default=64)
    args = parser.parse_args()
    if not 1 <= args.trials <= 100000:
        parser.error("trials must be between 1 and 100000")
    spec = json.loads(Path(args.input).read_text())
    rng = random.Random(args.seed)
    circuits = []
    for family in spec["families"]:
        candidates = [random_circuit(family, rng) for _ in range(args.trials)]
        circuits.append(max(candidates, key=lambda candidate: ranking(family, candidate)))
    Path(args.output).write_text(json.dumps({"schema_version": 1, "circuits": circuits}, indent=2) + "\n")


if __name__ == "__main__":
    main()
