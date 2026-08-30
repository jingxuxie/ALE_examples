import gzip
import json
import os
import random
import stat
from pathlib import Path


AXES = "XYZ"


def read_design(path):
    path = Path(path)
    initial = path.lstat()
    if not stat.S_ISREG(initial.st_mode):
        raise ValueError("design must be a regular file, not a symlink or special file")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        current = os.fstat(descriptor)
        if not stat.S_ISREG(current.st_mode) or (initial.st_dev, initial.st_ino) != (current.st_dev, current.st_ino):
            raise ValueError("design changed or is not a regular file")
        if current.st_size > 16384:
            raise ValueError("design exceeds 16 KiB")
        raw = os.read(descriptor, 16385)
        if len(raw) > 16384 or os.fstat(descriptor).st_size > 16384:
            raise ValueError("design exceeds 16 KiB")
    finally:
        os.close(descriptor)
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique_keys)
    if not isinstance(value, dict) or set(value) != {"z_image"}:
        raise ValueError("expected exactly the key z_image")
    axes = value["z_image"]
    if not isinstance(axes, list) or len(axes) != 24:
        raise ValueError("z_image must contain exactly 24 integers")
    if any(type(axis) is not int or axis not in (0, 1, 2) for axis in axes):
        raise ValueError("axes must be integers 0=X, 1=Y, 2=Z")
    return axes


def load_case(path):
    with gzip.open(path, "rt") as stream:
        case = json.load(stream)
    case["columns"] = [[int(value, 16) for value in triple] for triple in case["columns"]]
    return case


def selected_columns(case, axes):
    return [triple[axes[cell]] for triple, cell in zip(case["columns"], case["slot_cells"])]


def ambiguity(vectors, stop_on_failure=False):
    pivots = {}
    logical_rank = 0
    for vector in vectors:
        while vector:
            pivot = vector.bit_length()
            previous = pivots.get(pivot)
            if previous is None:
                pivots[pivot] = vector
                if pivot <= 4:
                    logical_rank += 1
                    if stop_on_failure or logical_rank == 4:
                        return logical_rank
                break
            vector ^= previous
    return logical_rank


def generate_supports(case, seed, count_per_family, densities=None):
    generator = random.Random(seed)
    densities = densities or {"dense_iid": [0.28, 0.30, 0.32]}
    records = []
    if "dense_iid" in densities:
        slots = len(case["columns"])
        for density in densities["dense_iid"]:
            family = f"iid_{round(100 * density):02d}"
            for repeat in range(count_per_family):
                support = [slot for slot in range(slots) if generator.random() < density]
                records.append({"family": family, "support": support})
        return records
    positions = case["data_coordinates"]
    qubit_count = len(positions)
    rounds = case["noisy_subrounds"]
    width, height = case["coordinate_period"]
    for family in ("iid", "stripe", "burst"):
        for repeat in range(count_per_family):
            density = densities[family][repeat % len(densities[family])]
            orientation = generator.randrange(3)
            origin = generator.randrange(width if orientation != 1 else height)
            center = generator.randrange(rounds)
            support = []
            for time in range(rounds):
                for qubit, (horizontal, vertical) in enumerate(positions):
                    if family == "iid":
                        probability = density
                    elif family == "stripe":
                        period = height if orientation == 1 else width
                        coordinate = (horizontal, vertical, horizontal + 2 * vertical)[orientation]
                        inside = (coordinate - origin) % period < max(2, period // 3)
                        probability = min(0.98, density + 0.35) if inside else density * 0.45
                    else:
                        inside = (time - center) % rounds < max(2, rounds // 2)
                        probability = min(0.98, density + 0.30) if inside else density * 0.25
                    if generator.random() < probability:
                        support.append(time * qubit_count + qubit)
            records.append({"family": family, "support": support})
    return records


def score_case(case, records, axes, full_ambiguity=True):
    columns = selected_columns(case, axes)
    families = {}
    for record in records:
        amount = ambiguity((columns[index] for index in record["support"]), not full_ambiguity)
        result = families.setdefault(record["family"], {"correct": 0, "count": 0, "ambiguity_sum": 0})
        result["correct"] += int(amount == 0)
        result["count"] += 1
        result["ambiguity_sum"] += amount
    for result in families.values():
        result["fraction"] = result["correct"] / result["count"]
        result["mean_ambiguity"] = result["ambiguity_sum"] / result["count"] if full_ambiguity else None
    return families


def aggregate(results):
    groups = {}
    for case_id, families in results.items():
        for family, result in families.items():
            groups[case_id + "/" + family] = result
    core_score = sum(group["fraction"] for group in groups.values()) / len(groups)
    worst_score = min(group["fraction"] for group in groups.values())
    return {
        "core_score": core_score,
        "worst_family_score": worst_score,
        "correctness_fraction": core_score,
        "worst_group_fraction": worst_score,
        "mean_ambiguity": sum(group["mean_ambiguity"] for group in groups.values()) / len(groups),
        "groups": groups,
    }
