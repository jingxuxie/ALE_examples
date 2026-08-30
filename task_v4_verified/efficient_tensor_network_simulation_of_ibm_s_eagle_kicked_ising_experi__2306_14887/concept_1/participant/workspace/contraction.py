import heapq
import math
import random


def make_masks(instance, slices=()):
    skipped = set(slices)
    masks = [0] * instance["n"]
    weights = []
    for edge_id, edge in enumerate(instance["edges"]):
        weights.append(edge["dim"].bit_length() - 1)
        if edge_id not in skipped:
            masks[edge["u"]] |= 1 << edge_id
            masks[edge["v"]] |= 1 << edge_id
    return masks, weights


def weight_function(weights):
    cache = {0: 0}

    def weight(mask):
        if mask not in cache:
            remaining = mask
            total = 0
            while remaining:
                bit = remaining & -remaining
                total += weights[bit.bit_length() - 1]
                remaining ^= bit
            cache[mask] = total
        return cache[mask]

    return weight


def assess(instance, plan):
    if not isinstance(plan, dict) or set(plan) != {"slices", "merges"}:
        raise ValueError("plan must have exactly slices and merges")
    slices = plan["slices"]
    if not isinstance(slices, list) or any(type(edge_id) is not int for edge_id in slices):
        raise ValueError("slices must be integer IDs")
    if len(set(slices)) != len(slices) or any(not 0 <= edge_id < len(instance["edges"]) for edge_id in slices):
        raise ValueError("invalid or repeated slice")
    merges = plan["merges"]
    if not isinstance(merges, list) or len(merges) != instance["n"] - 1:
        raise ValueError("wrong number of merges")
    masks, weights = make_masks(instance, slices)
    weight = weight_function(weights)
    live = dict(enumerate(masks))
    slice_bits = sum(weights[edge_id] for edge_id in slices)
    resident = sum(1 << weight(mask) for mask in masks) + bool(slices)
    peak = resident
    work = 0
    largest = []
    for offset, pair in enumerate(merges):
        if not isinstance(pair, list) or len(pair) != 2 or any(type(index) is not int for index in pair):
            raise ValueError("merge must contain two integer IDs")
        left, right = pair
        if left == right or left not in live or right not in live:
            raise ValueError("merge uses consumed or invalid tensor")
        left_mask, right_mask = live.pop(left), live.pop(right)
        result_mask = left_mask ^ right_mask
        output_size = 1 << weight(result_mask)
        work += 1 << weight(left_mask | right_mask)
        peak = max(peak, resident + output_size)
        resident += output_size - (1 << weight(left_mask)) - (1 << weight(right_mask))
        live[instance["n"] + offset] = result_mask
        largest.append((weight(result_mask), result_mask))
    if len(live) != 1 or next(iter(live.values())):
        raise ValueError("final result is not a scalar")
    total_work = (1 << slice_bits) * (work + 1) - 1
    return {"work": total_work, "log2_work": math.log2(total_work),
            "peak_elements": peak, "feasible": peak <= instance["memory_elements"],
            "slice_bits": slice_bits, "frontiers": sorted(largest, reverse=True)}


def greedy(instance, slices, seed, temperature=0.7):
    masks, weights = make_masks(instance, slices)
    weight = weight_function(weights)
    active = dict(enumerate(masks))
    rng = random.Random(seed)
    heap = []

    def push(left, right):
        left_mask, right_mask = active[left], active[right]
        if not left_mask & right_mask:
            return
        union_weight = weight(left_mask | right_mask)
        output_weight = weight(left_mask ^ right_mask)
        score = union_weight + 0.35 * output_weight + rng.gauss(0, temperature)
        heapq.heappush(heap, (score, left, right))

    for left in range(instance["n"]):
        for right in range(left + 1, instance["n"]):
            push(left, right)
    merges = []
    while len(active) > 1:
        while heap:
            _, left, right = heapq.heappop(heap)
            if left in active and right in active:
                break
        else:
            ranked = sorted(active, key=lambda index: weight(active[index]))
            left, right = ranked[:2]
        result_mask = active.pop(left) ^ active.pop(right)
        result_id = instance["n"] + len(merges)
        merges.append([left, right])
        active[result_id] = result_mask
        for other_id in active:
            if other_id != result_id:
                push(other_id, result_id)
    return {"slices": sorted(slices), "merges": merges}


def plan_trial(instance, seed, temperature=0.7):
    slices = set()
    rng = random.Random(seed + 761)
    while True:
        plan = greedy(instance, slices, seed, temperature)
        metrics = assess(instance, plan)
        if metrics["feasible"]:
            return plan, metrics
        candidates = {}
        highest = metrics["frontiers"][0][0]
        for rank, frontier in metrics["frontiers"]:
            if rank < highest - 5:
                break
            while frontier:
                bit = frontier & -frontier
                edge_id = bit.bit_length() - 1
                candidates[edge_id] = candidates.get(edge_id, 0) + 2 ** (rank - highest)
                frontier ^= bit
        if not candidates:
            candidates = {edge_id: 1 for edge_id in range(len(instance["edges"])) if edge_id not in slices}
        edge_id = max(candidates, key=lambda index: candidates[index] *
                      math.log2(instance["edges"][index]["dim"]) * rng.uniform(0.8, 1.2))
        slices.add(edge_id)


def baseline_plan(instance, trials=24, seed_offset=0):
    best = None
    best_work = None
    for trial in range(trials):
        temperature = (0.0, 0.4, 0.8, 1.2)[trial % 4]
        plan, metrics = plan_trial(instance, 1337 + seed_offset + trial * 7919, temperature)
        if best_work is None or metrics["work"] < best_work:
            best, best_work = plan, metrics["work"]
    return best
