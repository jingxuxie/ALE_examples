"""Public generative model. Private instances live only in the evaluator parent."""

import json
import random
import re
from pathlib import Path


CONTRACT = json.loads(Path(__file__).with_name("contract.json").read_text())


class ProtocolError(ValueError):
    pass


def component_edges(kind):
    edges = set()
    for first in range(16):
        first_row, first_column = divmod(first, 4)
        for second in range(first + 1, 16):
            second_row, second_column = divmod(second, 4)
            if kind == "R":
                adjacent = first_row == second_row or first_column == second_column
            elif kind == "S":
                displacement = (
                    (second_row - first_row) % 4,
                    (second_column - first_column) % 4,
                )
                adjacent = displacement in {
                    (1, 0), (3, 0), (0, 1), (0, 3), (1, 1), (3, 3)
                }
            else:
                raise ValueError("unknown component kind")
            if adjacent:
                edges.add((first, second))
    return sorted(edges)


def anchor_mask(sites):
    return sum(
        1 << (8 * site + offset)
        for site in sites
        for offset in (0, 2, 4, 6)
    )


class Device:
    def __init__(self, family, contamination_denominator, seed):
        if family not in CONTRACT["families"]:
            raise ValueError("unknown family")
        if contamination_denominator not in CONTRACT["contamination_denominators"]:
            raise ValueError("unknown contamination")
        self.family = family
        self.contamination_denominator = contamination_denominator
        self.random = random.Random(seed)
        permutation = list(range(32))
        self.random.shuffle(permutation)
        self.neighbors = [set() for site in range(32)]
        for component, kind in enumerate(family):
            for first, second in component_edges(kind):
                first = permutation[16 * component + first]
                second = permutation[16 * component + second]
                self.neighbors[first].add(second)
                self.neighbors[second].add(first)
        self.neighbors = [tuple(sorted(neighbors)) for neighbors in self.neighbors]
        self.frames = 0
        self.queries = 0
        self.frame_queries = 0
        self.residual = None
        self.finished = False

    def hello(self):
        return {"op": "hello", "contract": CONTRACT}

    def _budget(self):
        return {
            "frames_left": CONTRACT["frames"] - self.frames,
            "queries_left": CONTRACT["parity_queries"] - self.queries,
            "frame_queries_left": CONTRACT["queries_per_frame"] - self.frame_queries,
        }

    def handle(self, request):
        if self.finished or not isinstance(request, dict):
            raise ProtocolError("invalid request")
        operation = request.get("op")
        if operation == "start":
            if set(request) != {"op", "source"}:
                raise ProtocolError("invalid start fields")
            source = request["source"]
            if type(source) is not int or not 0 <= source < 32:
                raise ProtocolError("invalid source")
            if self.frames >= CONTRACT["frames"]:
                raise ProtocolError("frame budget exceeded")
            contaminated = self.contamination_denominator and (
                self.random.randrange(self.contamination_denominator) == 0
            )
            if contaminated:
                echo = self.random.randrange(31)
                if echo >= source:
                    echo += 1
            else:
                echo = self.random.choice(self.neighbors[source])
            self.residual = 0
            for site in (source, echo):
                doublet = self.random.randrange(4)
                self.residual |= 3 << (8 * site + 2 * doublet)
            self.frames += 1
            self.frame_queries = 0
            return {"op": "started", **self._budget()}
        if operation == "parity":
            if set(request) != {"op", "mask"}:
                raise ProtocolError("invalid parity fields")
            encoded = request["mask"]
            if not isinstance(encoded, str) or not re.fullmatch("[0-9a-fA-F]{1,64}", encoded):
                raise ProtocolError("invalid mask encoding")
            mask = int(encoded, 16)
            if mask.bit_count() > CONTRACT["mask_weight"]:
                raise ProtocolError("mask weight exceeded")
            if self.residual is None:
                raise ProtocolError("no active frame")
            if self.queries >= CONTRACT["parity_queries"]:
                raise ProtocolError("parity budget exceeded")
            if self.frame_queries >= CONTRACT["queries_per_frame"]:
                raise ProtocolError("per-frame budget exceeded")
            self.queries += 1
            self.frame_queries += 1
            return {
                "op": "parity",
                "value": (self.residual & mask).bit_count() & 1,
                **self._budget(),
            }
        if operation == "guess":
            if set(request) != {"op", "family"} or request["family"] not in CONTRACT["families"]:
                raise ProtocolError("invalid classification")
            self.finished = True
            return {"op": "finished"}
        raise ProtocolError("unknown operation")
