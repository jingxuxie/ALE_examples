import itertools
import json
import math
from collections import Counter, defaultdict
from functools import lru_cache


def volume(indices, types, dimensions):
    return math.prod(dimensions[types[index]] for index in set(indices))


@lru_cache(maxsize=200000)
def canonical(factors, output):
    groups = defaultdict(list)
    for name, indices in factors:
        groups[name].append(indices)
    options = [tuple(set(itertools.permutations(groups[name]))) for name in sorted(groups)]
    best = None
    for ordering in itertools.product(*options):
        labels = {label: position for position, label in enumerate(output)}
        encoded = []
        for name, block in zip(sorted(groups), ordering):
            for indices in block:
                converted = []
                for index in indices:
                    if index not in labels:
                        labels[index] = len(labels)
                    converted.append(labels[index])
                encoded.append((name, tuple(converted)))
        result = tuple(encoded)
        if best is None or result < best:
            best = result
    return best


def term_key(term):
    return canonical(tuple((name, tuple(indices)) for name, indices in term["inputs"]), tuple(term["output"]))


def validate(case, plan):
    if not isinstance(plan, dict) or not isinstance(plan.get("steps"), list):
        raise ValueError("plan must contain a steps list")
    if len(plan["steps"]) > 30000:
        raise ValueError("too many steps")
    tensors = case["tensors"]
    dimensions = case["dimensions"]
    live = {}
    ever = set(tensors)
    emitted = set()
    memory = peak = work = 0
    expected = [term_key(term) for term in case["terms"]]

    def resolve(reference, namespace):
        if not isinstance(reference, list) or len(reference) != 2:
            raise ValueError("reference must be [name, indices]")
        name, indices = reference
        if not isinstance(name, str) or not isinstance(indices, str) or not indices.isalpha() and indices != "":
            raise ValueError("invalid reference")
        if len(set(indices)) != len(indices):
            raise ValueError("diagonal indices are not supported")
        if name in tensors:
            types = tensors[name]
            factors = [(name, tuple(indices))]
        elif name in live:
            original, boundary, types, size = live[name]
            mapping = dict(zip(boundary, indices))
            factors = []
            for tensor, labels in original:
                remapped = []
                for label in labels:
                    if label not in mapping:
                        mapping[label] = (namespace, len(mapping))
                    remapped.append(mapping[label])
                factors.append((tensor, tuple(remapped)))
        else:
            raise ValueError("unknown or freed tensor " + name)
        if len(indices) != len(types):
            raise ValueError("rank mismatch")
        return factors, dict(zip(indices, types))

    for step_number, step in enumerate(plan["steps"]):
        if not isinstance(step, dict):
            raise ValueError("step must be an object")
        if "delete" in step:
            name = step["delete"]
            if set(step) != {"delete"} or name not in live:
                raise ValueError("invalid delete")
            memory -= live.pop(name)[3]
            continue
        if "emit" in step:
            index = step["emit"]
            if set(step) != {"emit", "input", "output"} or type(index) is not int or not 0 <= index < len(expected) or index in emitted:
                raise ValueError("invalid output index")
            factors, types = resolve(step["input"], (step_number, 0))
            labels = step["output"]
            if not isinstance(labels, str) or len(set(labels)) != len(labels) or set(labels) != set(types):
                raise ValueError("emit must preserve all axes")
            target = case["terms"][index]
            desired = [case["index_types"][index] for index in target["output"]]
            if [types[label] for label in labels] != desired or canonical(tuple(factors), tuple(labels)) != expected[index]:
                raise ValueError("output is not the specified contraction: " + str(index))
            emitted.add(index)
            continue
        if set(step) != {"id", "inputs", "output"}:
            raise ValueError("invalid contraction step")
        name = step["id"]
        if not isinstance(name, str) or not name or name in ever:
            raise ValueError("temporary name must be new")
        references = step["inputs"]
        boundary = step["output"]
        if not isinstance(references, list) or len(references) != 2 or not isinstance(boundary, str) or len(set(boundary)) != len(boundary):
            raise ValueError("binary contractions require distinct output axes")
        factors = []
        types = {}
        for position, reference in enumerate(references):
            expanded, local = resolve(reference, (step_number, position))
            factors.extend(expanded)
            for index, kind in local.items():
                if index in types and types[index] != kind:
                    raise ValueError("incompatible index spaces")
                types[index] = kind
        if len(factors) > 6 or any(index not in types for index in boundary):
            raise ValueError("invalid output axes or oversized monomial")
        size = volume(boundary, types, dimensions)
        work += volume(types, types, dimensions) * (2 if set(types) - set(boundary) else 1)
        memory += size
        peak = max(peak, memory)
        if peak > case["memory_cap"]:
            raise ValueError("scratch-memory cap exceeded")
        internal_mapping = {}
        stored = []
        for tensor, labels in factors:
            converted = []
            for label in labels:
                if label in set(boundary):
                    converted.append(label)
                else:
                    if label not in internal_mapping:
                        internal_mapping[label] = ("sum", len(internal_mapping))
                    converted.append(internal_mapping[label])
            stored.append((tensor, tuple(converted)))
        live[name] = (tuple(stored), tuple(boundary), [types[index] for index in boundary], size)
        ever.add(name)
    if len(emitted) != len(expected):
        raise ValueError("not every target was emitted")
    return {"valid": True, "flops": work, "peak_elements": peak,
            "resource_score": 1 - peak / case["memory_cap"], "outputs": len(emitted)}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("case")
    parser.add_argument("plan")
    args = parser.parse_args()
    try:
        result = validate(json.load(open(args.case)), json.load(open(args.plan)))
    except Exception as error:
        result = {"valid": False, "reason": str(error)}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
