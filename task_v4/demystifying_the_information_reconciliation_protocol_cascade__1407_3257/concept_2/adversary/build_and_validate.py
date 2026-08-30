import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
sys.path.insert(0, str(ROOT / "evaluator"))
from replay import replay, validate
from reproduce import reproduce
from evaluate import evaluate


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def build():
    generator = random.Random(847168589446632447872343)
    size = 2048
    block_size = 32
    root_count = size // block_size
    core_blocks = generator.sample(range(root_count), 7)
    core = sorted(position for block in core_blocks for position in generator.sample(range(block * block_size, (block + 1) * block_size), 2))
    trigger_blocks = generator.sample([block for block in range(root_count) if block not in core_blocks], 8)
    triggers = [block * block_size + generator.randrange(block_size) for block in trigger_blocks]
    passes = [{"block_size": block_size, "permutation": list(range(size))}]
    for pass_index in range(1, 6):
        selected_blocks = generator.sample(range(root_count), 7)
        selected_positions = [position for block in selected_blocks for position in generator.sample(range(block * block_size, (block + 1) * block_size), 2)]
        shuffled_core = list(core)
        generator.shuffle(shuffled_core)
        remainder = [position for position in range(size) if position not in core]
        generator.shuffle(remainder)
        permutation = [None] * size
        for slot, position in zip(selected_positions, shuffled_core):
            permutation[slot] = position
        available = iter(remainder)
        permutation = [next(available) if position is None else position for position in permutation]
        passes.append({"block_size": block_size, "permutation": permutation})
    deployment = {"n": size, "passes": passes, "version": 1}
    validate(deployment, core + triggers)
    deployment_path = ROOT / "participant/input/deployment.json"
    write_json(deployment_path, deployment)
    write_json(ROOT / "evaluator/hidden/manifest.json", {"deployment_sha256": hashlib.sha256(deployment_path.read_bytes()).hexdigest(), "bounds": {"max_errors": 24, "min_residual": 8, "min_corrected": 6, "min_initial_odd": 6}})
    write_json(ROOT / "evaluator/hidden/privileged_witness.json", {"errors": sorted(core + triggers)})
    write_json(ROOT / "adversary/construction.json", {"generation_method": "Condition fixed valid interleavers on a private even-parity 14-bit core; add eight separate first-pass triggers. This is a planted deployment audit, not evidence about uniform fresh shuffles or BSC frequency.", "core": core, "triggers": sorted(triggers), "selection_before_fresh_attempt": True})


def check():
    generator = random.Random(749877)
    checked = 0
    for size in range(2, 9):
        for repetition in range(8):
            passes = []
            for pass_index in range(4):
                permutation = list(range(size))
                generator.shuffle(permutation)
                passes.append({"block_size": generator.randrange(1, size + 1), "permutation": permutation})
            deployment = {"n": size, "passes": passes}
            for mask in range(1 << size):
                errors = [position for position in range(size) if mask & (1 << position)]
                for priority in ("earliest", "shortest"):
                    observed = replay(deployment, errors, priority)
                    independent = reproduce(deployment, errors, priority)
                    assert observed == independent, (deployment, errors, priority, observed, independent)
                    checked += 1
    deployment = json.loads((ROOT / "participant/input/deployment.json").read_text())
    witness = json.loads((ROOT / "evaluator/hidden/privileged_witness.json").read_text())
    for priority in ("earliest", "shortest"):
        assert replay(deployment, witness["errors"], priority) == reproduce(deployment, witness["errors"], priority)
    certificate = evaluate(ROOT / "evaluator/hidden/privileged_witness.json")
    assert certificate["passed"]
    write_json(ROOT / "adversary/privileged_score.json", certificate)
    bad_cases = [{"errors": []}, {"errors": [False]}, {"errors": [deployment["n"]]}, {"errors": [1, 1]}, {"errors": list(range(25))}, {"errors": [0], "extra": 1}]
    temporary = ROOT / "adversary/invalid_probe.json"
    for bad in bad_cases:
        write_json(temporary, bad)
        assert not evaluate(temporary)["valid"]
    write_json(ROOT / "adversary/validation.json", {"independent_replays": checked, "malformed_artifacts_rejected": len(bad_cases), "privileged_certificate_passed": True, "bounds_frozen_before_first_attempt": True})
    print(json.dumps({"independent_replays": checked, "certificate": certificate}, indent=2))


if __name__ == "__main__":
    for directory in ("attempts", "champions", "adversary", "evaluator/hidden", "participant/input"):
        (ROOT / directory).mkdir(parents=True, exist_ok=True)
    if "--build" in sys.argv:
        build()
    check()
