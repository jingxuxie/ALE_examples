import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.linalg import expm


def hopping(size=4):
    matrix = np.zeros((size * size, size * size))
    for horizontal in range(size):
        for vertical in range(size):
            source = horizontal * size + vertical
            for delta_horizontal, delta_vertical in [(1, 0), (0, 1)]:
                target = ((horizontal + delta_horizontal) % size) * size + (vertical + delta_vertical) % size
                matrix[source, target] = matrix[target, source] = -1.0
    return matrix


def scan(beta, interaction, chemical, slices, count, seed):
    random = np.random.default_rng(seed)
    kinetic = expm(-beta / slices * hopping())
    coupling = np.arccosh(np.exp(beta / slices * interaction / 2))
    statistics = []
    start = time.monotonic()
    for offset in range(0, count, 256):
        fields = random.choice([-1, 1], size=(min(256, count - offset), slices, 16))
        products = np.broadcast_to(np.eye(16), (len(fields), 2, 16, 16)).copy()
        for time_index in range(slices):
            diagonal = np.exp(coupling * fields[:, time_index, None, :] * np.array([1, -1])[None, :, None])
            products = kinetic @ (diagonal[..., :, None] * products)
        signs, logarithms = np.linalg.slogdet(np.eye(16) + np.exp(beta * chemical) * products)
        negative = np.flatnonzero(np.prod(signs, axis=1) < 0)
        statistics.append(len(negative))
        if len(negative):
            destination = Path(__file__).parent / f"negative_{beta}_{interaction}_{chemical}_{slices}.json"
            destination.write_text(json.dumps({"beta": beta, "interaction": interaction, "chemical": chemical, "slices": slices, "fields": fields[negative[0]].tolist()}))
            print(json.dumps({"found": str(destination), "draws": offset + 256, "negative_in_batch": len(negative), "seconds": time.monotonic() - start}), flush=True)
            return
    print(json.dumps({"beta": beta, "interaction": interaction, "chemical": chemical, "slices": slices, "negative": sum(statistics), "draws": count, "seconds": time.monotonic() - start}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--beta", type=float, default=2.0)
    parser.add_argument("--interaction", type=float, default=4.0)
    parser.add_argument("--chemical", type=float, default=1.0)
    parser.add_argument("--slices", type=int, default=16)
    parser.add_argument("--count", type=int, default=8192)
    parser.add_argument("--seed", type=int, default=8172)
    arguments = parser.parse_args()
    scan(arguments.beta, arguments.interaction, arguments.chemical, arguments.slices, arguments.count, arguments.seed)
