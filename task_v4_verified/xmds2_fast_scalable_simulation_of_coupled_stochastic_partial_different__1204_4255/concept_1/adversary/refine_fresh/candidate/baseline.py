import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))
from model import home, reverse_distances


def plan(instance, policy="next_use"):
    dimensions = instance["dimensions"]
    sizes = instance["sizes"]
    requests = instance["requests"]
    cache = {(field, 0, 0) for field in range(len(sizes))}
    tables = {}
    actions = []

    def distances(mask, layout):
        target = (mask, layout)
        if target not in tables:
            tables[target] = reverse_distances(instance, target)
        return tables[target]

    def next_use(key, position):
        for future in range(position, len(requests)):
            request = requests[future]
            if key == (request["field"], request["mask"], request["layout"]):
                return future - position
            if key[0] in request["updates"]:
                break
        return len(requests) + 1

    for position, request in enumerate(requests):
        field = request["field"]
        wanted = (field, request["mask"], request["layout"])
        if wanted not in cache:
            distance, successor = distances(wanted[1], wanted[2])
            source = min((key for key in cache if key[0] == field), key=lambda key: (distance[key[1] * dimensions + key[2]], key))
            while source != wanted:
                index = successor[source[1] * dimensions + source[2]]
                mask, layout = divmod(index, dimensions)
                destination = (field, mask, layout)
                keep = True
                while sum(sizes[key[0]] for key in cache if not home(key)) + sizes[field] > instance["capacity"]:
                    candidates = [key for key in cache if not home(key)]
                    victim = max(candidates, key=lambda key: (next_use(key, position + 1), sizes[key[0]], key))
                    cache.remove(victim)
                    if victim == source:
                        keep = False
                    else:
                        actions.append(["drop", *victim])
                if source[2] == layout:
                    axis = (source[1] ^ mask).bit_length() - 1
                    actions.append(["axis", *source, axis, keep])
                else:
                    actions.append(["transpose", *source, layout, keep])
                cache.add(destination)
                source = destination
        actions.append(["read"])
        updates = request["updates"]
        cache = {key for key in cache if home(key) or key[0] not in updates}
    return {"actions": actions}


def main():
    for line in sys.stdin:
        if line.strip():
            print(json.dumps(plan(json.loads(line)), separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
