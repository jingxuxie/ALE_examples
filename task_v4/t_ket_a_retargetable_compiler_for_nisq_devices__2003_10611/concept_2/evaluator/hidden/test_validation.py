import copy
import hashlib
import json
import os
import random
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "participant" / "input"))
sys.path.insert(0, str(ROOT / "evaluator"))

from benchmark import evaluate_file
from evaluate import evaluate
from router import dependencies, hardware, relabelings, route, settings, transform
from validation import InvalidWitness, load_witness, replay, validate


def main():
    started = time.monotonic()
    baseline_path = ROOT / "participant" / "baseline" / "witness.json"
    witness = load_witness(baseline_path)
    count, edges, gates, costs = validate(witness)
    report = {"checks": [], "baseline": evaluate(baseline_path.parent)}
    assert report["baseline"]["valid"] and not report["baseline"]["passed"]
    assert len(report["baseline"]["families"]) == 6
    assert all(len(family["settings"]) == 18 for family in report["baseline"]["families"])
    report["checks"].append("baseline valid, below frozen target; all 108 portfolio runs replayed")

    def reject(name, candidate):
        try:
            validate(candidate)
        except (InvalidWitness, ValueError):
            report["checks"].append(name)
        else:
            raise AssertionError(f"accepted invalid witness: {name}")

    mutations = []
    for name, field, value in (
        ("forged cost rejected", "native_2q", 0),
        ("initial mapping override rejected", "initial_mapping", list(reversed(range(16)))),
        ("boolean version rejected", "version", True),
        ("unknown hardware rejected", "hardware", "complete16"),
        ("null gates rejected", "gates", None),
        ("short circuit rejected", "gates", gates[:47]),
        ("overlong circuit rejected", "gates", gates * 3),
        ("empty route rejected", "route", []),
        ("overlong route rejected", "route", [["swap", 0, 1]] * 20001),
        ("nonpermutation final mapping rejected", "final_mapping", [0] * 16),
    ):
        candidate = copy.deepcopy(witness)
        candidate[field] = value
        mutations.append((name, candidate))
    for value, name in ((-1, "negative logical index"), (16, "out of range logical index"),
                        (True, "boolean logical index"), (0.0, "float logical index")):
        candidate = copy.deepcopy(witness)
        candidate["gates"][0][0] = value
        mutations.append((name, candidate))
    candidate = copy.deepcopy(witness)
    candidate["gates"][0][1] = candidate["gates"][0][0]
    mutations.append(("self interaction rejected", candidate))
    candidate = copy.deepcopy(witness)
    candidate["route"].insert(0, ["swap", 0, 15])
    mutations.append(("nonedge SWAP rejected", candidate))
    candidate = copy.deepcopy(witness)
    candidate["route"].insert(0, ["swap", -1, 0])
    mutations.append(("negative SWAP index rejected", candidate))
    candidate = copy.deepcopy(witness)
    candidate["route"].insert(0, ["gate", -1, 0, 1])
    mutations.append(("negative gate ID rejected", candidate))
    gate_slot = next(index for index, operation in enumerate(witness["route"])
                     if operation[0] == "gate")
    candidate = copy.deepcopy(witness)
    candidate["route"][gate_slot][2:4] = list(reversed(candidate["route"][gate_slot][2:4]))
    mutations.append(("reversed control and target rejected", candidate))
    candidate = copy.deepcopy(witness)
    candidate["route"].insert(gate_slot + 1, candidate["route"][gate_slot][:])
    mutations.append(("duplicate gate rejected", candidate))
    candidate = copy.deepcopy(witness)
    del candidate["route"][gate_slot]
    mutations.append(("missing gate rejected", candidate))
    candidate = copy.deepcopy(witness)
    candidate["route"].insert(0, ["bridge", 0, 1, 2])
    mutations.append(("unknown opcode rejected", candidate))
    candidate = copy.deepcopy(witness)
    candidate["final_mapping"][0], candidate["final_mapping"][1] = (
        candidate["final_mapping"][1], candidate["final_mapping"][0])
    mutations.append(("forged final mapping rejected", candidate))
    for name, candidate in mutations:
        reject(name, candidate)

    def reject_replay(name, small_gates, operations, final_mapping=None):
        try:
            replay(small_gates, count, edges, operations,
                   list(range(count)) if final_mapping is None else final_mapping)
        except InvalidWitness:
            report["checks"].append(name)
        else:
            raise AssertionError(name)

    reject_replay("dependency on control wire enforced", [[0, 1], [0, 4]],
                  [["gate", 1, 0, 4], ["gate", 0, 0, 1]])
    reject_replay("dependency on target wire enforced", [[0, 1], [2, 1]],
                  [["gate", 1, 2, 1], ["gate", 0, 0, 1]])
    reject_replay("physical gate adjacency enforced", [[0, 15]], [["gate", 0, 0, 15]])
    reject_replay("initial identity enforced", [[0, 1]], [["gate", 0, 4, 5]])
    reject_replay("SWAP updates both occupants", [[0, 2]],
                  [["swap", 0, 1], ["gate", 0, 0, 2]])
    replay([[0, 1], [4, 5]], count, edges,
           [["gate", 1, 4, 5], ["gate", 0, 0, 1]], list(range(count)))
    report["checks"].append("independent gates may reorder")
    small_final = list(range(count))
    small_final[0], small_final[1] = 1, 0
    replay([[0, 2]], count, edges, [["swap", 0, 1], ["gate", 0, 1, 2]], small_final)
    report["checks"].append("known one-SWAP route replays")

    with tempfile.TemporaryDirectory(dir=ROOT / "adversary", prefix="checks_") as temporary:
        directory = Path(temporary)
        artifact = directory / "witness.json"
        malformed = {
            "malformed JSON": b"{",
            "duplicate JSON keys": b'{"version":1,"version":1}',
            "nested duplicate keys": b'{"outer":{"same":1,"same":2}}',
            "NaN": b'{"version":NaN}',
            "Infinity": b'{"version":Infinity}',
            "invalid UTF8": b"\xff",
            "trailing JSON": b"{} {}",
            "oversized file": b" " * 1_000_001,
            "deep nesting": b"[" * 2000 + b"]" * 2000,
        }
        for name, content in malformed.items():
            artifact.write_bytes(content)
            result = evaluate_file(artifact)
            assert not result["valid"] and not result["passed"]
            assert result["core_score"] == result["worst_family_score"] == result["resource_score"] == 0
            report["checks"].append(f"{name} rejected")
        artifact.unlink()
        artifact.symlink_to(baseline_path)
        assert not evaluate_file(artifact)["valid"]
        report["checks"].append("symlink to valid witness rejected")
        artifact.unlink()
        artifact.symlink_to(directory / "absent")
        assert not evaluate_file(artifact)["valid"]
        report["checks"].append("dangling symlink rejected")
        artifact.unlink()
        os.mkfifo(artifact)
        assert not evaluate_file(artifact)["valid"]
        report["checks"].append("FIFO rejected without blocking")
        artifact.unlink()
        artifact.mkdir()
        assert not evaluate_file(artifact)["valid"]
        report["checks"].append("directory rejected")
        artifact.rmdir()
        assert not evaluate_file(artifact)["valid"]
        report["checks"].append("missing artifact rejected")
        artifact.write_bytes(baseline_path.read_bytes())
        for module in ("solution.py", "router.py", "validation.py", "benchmark.py", "json.py"):
            (directory / module).write_text("raise RuntimeError('untrusted code executed')\n")
        process = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "evaluator" / "evaluate.py"),
                                  "--solution-dir", str(directory)], cwd=directory,
                                 capture_output=True, text=True, timeout=120)
        assert process.returncode == 0, process.stderr
        assert json.loads(process.stdout) == report["baseline"]
        report["checks"].append("isolated evaluator ignores all submission Python modules")

    fuzz_runs = 0
    for graph in ("ring16", "ladder16", "grid16"):
        count, graph_edges = hardware(graph)
        for seed in (5, 17):
            generator = random.Random(seed)
            random_gates = [generator.sample(range(count), 2) for _ in range(48)]
            _, logical, physical = relabelings(count)[-1]
            mapped_gates, mapped_edges, initial = transform(random_gates, graph_edges, logical, physical)
            for setting in settings():
                result = route(mapped_gates, count, mapped_edges, initial, setting)
                measured = replay(mapped_gates, count, mapped_edges, result["route"],
                                  result["final_mapping"], initial)
                assert measured["swaps"] == result["swaps"]
                assert measured["native_2q"] == result["native_2q"]
                fuzz_runs += 1
    report["checks"].append(f"{fuzz_runs} randomized trusted routes independently replayed")
    report["passed"] = True
    report["seconds"] = time.monotonic() - started
    report["check_count"] = len(report["checks"])
    (ROOT / "adversary" / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    (ROOT / "adversary" / "baseline_result.json").write_text(json.dumps(report["baseline"], indent=2) + "\n")
    manifest = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted((ROOT / "participant").rglob("*")) if path.is_file()
                and "__pycache__" not in path.parts}
    manifest["evaluator/evaluate.py"] = hashlib.sha256((ROOT / "evaluator" / "evaluate.py").read_bytes()).hexdigest()
    (ROOT / "adversary" / "frozen_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"passed": True, "check_count": report["check_count"],
                      "seconds": report["seconds"],
                      "baseline_valid": report["baseline"]["valid"],
                      "baseline_passed": report["baseline"]["passed"],
                      "baseline_core_score": report["baseline"]["core_score"],
                      "reference": costs}, sort_keys=True))


if __name__ == "__main__":
    main()
