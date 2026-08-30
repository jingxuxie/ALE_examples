import heapq
import math


def home(key):
    return key[1:] == (0, 0)


def reverse_distances(instance, target):
    dimensions = instance["dimensions"]
    count = (1 << dimensions) * dimensions
    distance = [math.inf] * count
    successor = [None] * count
    target_index = target[0] * dimensions + target[1]
    distance[target_index] = 0
    queue = [(0, target_index)]
    while queue:
        cost, index = heapq.heappop(queue)
        if cost != distance[index]:
            continue
        mask, layout = divmod(index, dimensions)
        edges = []
        for axis in range(dimensions):
            if axis != layout:
                previous_mask = mask ^ (1 << axis)
                weight = instance["axis_cost"][layout][axis][(previous_mask >> axis) & 1]
                edges.append((previous_mask * dimensions + layout, weight))
        for previous_layout in range(dimensions):
            if previous_layout != layout:
                weight = instance["transpose_cost"][previous_layout][layout]
                edges.append((mask * dimensions + previous_layout, weight))
        for previous_index, weight in edges:
            if previous_index == 0 and index == target_index == 0:
                continue
            alternative = cost + weight
            if alternative < distance[previous_index]:
                distance[previous_index] = alternative
                successor[previous_index] = index
                if previous_index != 0:
                    heapq.heappush(queue, (alternative, previous_index))
    return distance, successor


def check(instance, answer):
    if not isinstance(answer, dict) or set(answer) != {"actions"}:
        raise ValueError("answer must contain only actions")
    actions = answer["actions"]
    if not isinstance(actions, list) or len(actions) > 100000:
        raise ValueError("invalid action list")
    dimensions = instance["dimensions"]
    sizes = instance["sizes"]
    representations = {(field, 0, 0) for field in range(len(sizes))}
    memory = 0
    peak = 0
    cost = 0
    position = 0
    for number, action in enumerate(actions):
        if not isinstance(action, list) or not action or not isinstance(action[0], str):
            raise ValueError(f"malformed action {number}")
        kind = action[0]
        if kind == "read":
            if len(action) != 1 or position >= len(instance["requests"]):
                raise ValueError("extra or malformed read")
            request = instance["requests"][position]
            wanted = (request["field"], request["mask"], request["layout"])
            if wanted not in representations:
                raise ValueError(f"read {position} has no current representation")
            updates = set(request["updates"])
            representations = {key for key in representations if home(key) or key[0] not in updates}
            memory = sum(sizes[key[0]] for key in representations if not home(key))
            position += 1
            continue
        if kind not in ("axis", "transpose", "drop"):
            raise ValueError("unknown action")
        if len(action) != (4 if kind == "drop" else 6):
            raise ValueError("wrong action length")
        if any(type(value) is not int for value in action[1:4]):
            raise ValueError("representation coordinates must be integers")
        field, mask, layout = action[1:4]
        if not (0 <= field < len(sizes) and 0 <= mask < (1 << dimensions) and 0 <= layout < dimensions):
            raise ValueError("representation out of bounds")
        source = (field, mask, layout)
        if source not in representations:
            raise ValueError("source unavailable or invalidated")
        if kind == "drop":
            if home(source):
                raise ValueError("cannot drop home")
            representations.remove(source)
            memory -= sizes[field]
            continue
        coordinate, keep = action[4:]
        if type(coordinate) is not int or not 0 <= coordinate < dimensions or type(keep) is not bool:
            raise ValueError("invalid transform coordinate or keep flag")
        if coordinate == layout:
            raise ValueError("cannot transform distributed axis or transpose to same layout")
        if kind == "axis":
            destination = (field, mask ^ (1 << coordinate), layout)
            weight = instance["axis_cost"][layout][coordinate][(mask >> coordinate) & 1]
        else:
            destination = (field, mask, coordinate)
            weight = instance["transpose_cost"][layout][coordinate]
        if destination in representations or home(destination):
            raise ValueError("destination already exists or is pinned")
        if not keep:
            if home(source):
                raise ValueError("cannot overwrite home")
            representations.remove(source)
            memory -= sizes[field]
        representations.add(destination)
        memory += sizes[field]
        cost += sizes[field] * weight
        peak = max(peak, memory)
        if memory > instance["capacity"]:
            raise ValueError(f"scratch budget exceeded at action {number}")
    if position != len(instance["requests"]):
        raise ValueError("not all requests were read")
    return {"cost": cost, "peak_memory": peak, "actions": len(actions), "reads": position}
