"""Weak baseline: decode echoes with fixed cuts, then count observed four-cliques."""

import itertools
import json
import sys


def exchange(request):
    print(json.dumps(request, separators=(",", ":")), flush=True)
    response = sys.stdin.readline()
    if not response:
        raise RuntimeError("oracle closed")
    return json.loads(response)


def main():
    hello = json.loads(sys.stdin.readline())
    contract = hello["contract"]
    masks = [
        sum(
            1 << (8 * site + offset)
            for site in range(32) if (site >> coordinate) & 1
            for offset in (0, 2, 4, 6)
        )
        for coordinate in range(5)
    ]
    adjacency = [set() for site in range(32)]
    for frame in range(min(contract["frames"], contract["parity_queries"] // 5)):
        source = frame % 32
        exchange({"op": "start", "source": source})
        echo = 0
        for coordinate, mask in enumerate(masks):
            reply = exchange({"op": "parity", "mask": format(mask, "x")})
            bit = reply["value"] ^ ((source >> coordinate) & 1)
            echo |= bit << coordinate
        adjacency[source].add(echo)
        adjacency[echo].add(source)
    clique_vertices = set()
    for vertices in itertools.combinations(range(32), 4):
        if all(second in adjacency[first] for first, second in itertools.combinations(vertices, 2)):
            clique_vertices.update(vertices)
    if len(clique_vertices) >= 20:
        family = "RR"
    elif clique_vertices:
        family = "RS"
    else:
        family = "SS"
    exchange({"op": "guess", "family": family})


if __name__ == "__main__":
    main()
