import argparse
import json
from pathlib import Path


def validate(deployment, errors):
    size = deployment["n"]
    if type(size) is not int or size < 2:
        raise ValueError("invalid frame length")
    if not isinstance(errors, list) or any(type(position) is not int for position in errors):
        raise ValueError("errors must be integer positions")
    if len(set(errors)) != len(errors) or any(not 0 <= position < size for position in errors):
        raise ValueError("errors must be distinct and in range")
    if not deployment.get("passes"):
        raise ValueError("no passes")
    for specification in deployment["passes"]:
        if type(specification["block_size"]) is not int or not 1 <= specification["block_size"] <= size:
            raise ValueError("invalid block size")
        permutation = specification["permutation"]
        if len(permutation) != size or any(type(position) is not int for position in permutation) or set(permutation) != set(range(size)):
            raise ValueError("invalid permutation")


def replay(deployment, errors, priority="earliest"):
    validate(deployment, errors)
    if priority not in ("earliest", "shortest"):
        raise ValueError("invalid priority")
    remaining = sum(1 << position for position in errors)
    known = {}
    corrected = []
    initial_odd = 0

    def register(order, origin):
        mask = sum(1 << position for position in order)
        if mask not in known:
            known[mask] = (tuple(order), origin, len(known))
        return mask

    for pass_index, specification in enumerate(deployment["passes"]):
        permutation = specification["permutation"]
        block_size = specification["block_size"]
        for start in range(0, deployment["n"], block_size):
            mask = register(permutation[start:start + block_size], pass_index)
            if pass_index == 0:
                initial_odd += (mask & remaining).bit_count() % 2
        while True:
            choices = []
            for mask, (order, origin, insertion) in known.items():
                if (mask & remaining).bit_count() % 2:
                    ranking = (origin, len(order), insertion) if priority == "earliest" else (len(order), origin, insertion)
                    choices.append((ranking, mask))
            if not choices:
                break
            selected = min(choices)[1]
            order, origin, insertion = known[selected]
            while len(order) > 1:
                midpoint = len(order) // 2
                left = order[:midpoint]
                right = order[midpoint:]
                left_mask = register(left, origin)
                right_mask = register(right, origin)
                selected = left_mask if (left_mask & remaining).bit_count() % 2 else right_mask
                order, origin, insertion = known[selected]
            position = order[0]
            if not remaining & (1 << position):
                raise AssertionError("attempted to flip a correct bit")
            remaining ^= 1 << position
            corrected.append(position)
    residual = [position for position in range(deployment["n"]) if remaining & (1 << position)]
    return {"priority": priority, "initial_odd": initial_odd, "corrected": sorted(corrected), "residual": residual, "known_blocks": len(known)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--deployment", required=True)
    parser.add_argument("--witness", required=True)
    arguments = parser.parse_args()
    deployment = json.loads(Path(arguments.deployment).read_text())
    errors = json.loads(Path(arguments.witness).read_text())["errors"]
    print(json.dumps([replay(deployment, errors, priority) for priority in ("earliest", "shortest")], indent=2))
