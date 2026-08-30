import copy
import json
import random
import string
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
sys.path.insert(0, str(ROOT / "participant/baseline"))
sys.path.insert(0, str(ROOT / "adversary"))
from contract import validate
from solve import solve
from audit import numerical


def make_case(generator):
    count = generator.randint(3, 6)
    edges = [(vertex, generator.randrange(vertex)) for vertex in range(1, count)]
    candidates = [(left, right) for left in range(count) for right in range(left) if (left, right) not in edges]
    generator.shuffle(candidates)
    edges += candidates[:generator.randint(0, min(2, len(candidates)))]
    labels = iter(string.ascii_letters)
    axes = [[] for unused in range(count)]
    for left, right in edges:
        label = next(labels)
        axes[left].append(label)
        axes[right].append(label)
    output = []
    for unused in range(generator.randint(1, 5)):
        label = next(labels)
        axes[generator.randrange(count)].append(label)
        output.append(label)
    generator.shuffle(output)
    tensors = {}
    inputs = []
    for local in axes:
        generator.shuffle(local)
        name = "input_" + str(len(local)) + "_" + str(generator.randrange(2))
        tensors[name] = ["o"] * len(local)
        inputs.append([name, "".join(local)])
    generator.shuffle(inputs)
    return {"dimensions": {"o": 2, "v": 3}, "tensors": tensors,
            "index_types": {label: "o" for label in string.ascii_letters},
            "terms": [{"inputs": inputs, "output": "".join(output)}], "memory_cap": 10**12}


def main():
    generator = random.Random(589121)
    maximum = 0
    rejected = accepted_equivalent = 0
    for iteration in range(300):
        case = make_case(generator)
        plan = solve(case)
        validate(case, plan)
        maximum = max(maximum, numerical(case, plan))
        altered = copy.deepcopy(plan)
        choices = [reference for step in altered["steps"] if "id" in step for reference in step["inputs"] if len(reference[1]) > 1]
        if choices:
            reference = generator.choice(choices)
            axes = list(reference[1])
            first, second = generator.sample(range(len(axes)), 2)
            axes[first], axes[second] = axes[second], axes[first]
            reference[1] = "".join(axes)
            try:
                validate(case, altered)
            except ValueError:
                rejected += 1
            else:
                error = numerical(case, altered)
                assert error < 1e-10, (iteration, error)
                maximum = max(maximum, error)
                accepted_equivalent += 1
    assert maximum < 1e-10
    result = {"passed": True, "random_networks": 300, "max_numerical_relative_error": maximum,
              "axis_mutations_rejected": rejected, "accepted_equivalent_mutations": accepted_equivalent,
              "false_acceptances": 0}
    (ROOT / "adversary/checker_fuzz.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
