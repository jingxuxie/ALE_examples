import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "authoring"))
from isolation import clean_environment, run_bounded, submission_command


def independent_check(case, schedule):
    if type(schedule) is not list or not schedule:
        raise ValueError("missing nonempty block schedule")
    flattened = []
    cost = 0.0
    operations = case["gates"]
    for block in schedule:
        if type(block) is not list or not 1 <= len(block) <= case["max_block_operations"]:
            raise ValueError("empty or oversized block")
        if any(type(index) is not int or not 0 <= index < len(operations) for index in block):
            raise ValueError("index is not an in-range integer")
        qubits = {qubit for index in block for qubit in operations[index]["qubits"]}
        epochs = {operations[index]["epoch"] for index in block}
        if len(qubits) > case["max_block_qubits"] or len(epochs) != 1:
            raise ValueError("support cap or epoch boundary violated")
        kinds = {operations[index]["kind"] for index in block}
        specialized = kinds in ({"permutation"}, {"diagonal"})
        hardware = case["hardware"]
        width = len(qubits)
        arithmetic = 1 if specialized else 2 ** width
        entries = 2 ** width if specialized else 4 ** width
        memory = hardware["memory"] * (1 + hardware["stride_penalty"] * max(0, min(qubits) - hardware["cache_qubits"]))
        update = hardware["launch"] + max(memory, arithmetic * hardware["compute"])
        cost += case["repetitions"] * update + hardware["build"] * (len(block) - 1) * entries
        flattened.extend(block)
    if len(flattened) != len(operations) or set(flattened) != set(range(len(operations))):
        raise ValueError("schedule must be an exact permutation of all gates")
    position = {index: order for order, index in enumerate(flattened)}
    last = {}
    for index, operation in enumerate(operations):
        for qubit in operation["qubits"]:
            if qubit in last and position[last[qubit]] >= position[index]:
                raise ValueError("noncommuting dependency reversed")
            last[qubit] = index
    epoch_sequence = [operations[index]["epoch"] for index in flattened]
    if epoch_sequence != sorted(epoch_sequence):
        raise ValueError("nonunitary barrier crossed")
    if not math.isfinite(cost) or cost <= 0:
        raise ValueError("invalid modeled cost")
    return cost


def geometric(values):
    return math.exp(sum(math.log(value) for value in values) / len(values))


def score(entries, response, execution):
    results = []
    families = {}
    schedules = response.get("schedules")
    if not isinstance(schedules, dict):
        raise ValueError("missing schedules object")
    for entry in entries:
        case = entry["case"]
        submitted = independent_check(case, schedules[case["id"]])
        ratio = entry["baseline_cost"] / submitted
        families.setdefault(entry["family"], []).append(ratio)
        results.append({"id": case["id"], "family": entry["family"], "baseline_cost": entry["baseline_cost"], "cost": submitted, "speedup": ratio})
    family_scores = {family: geometric(values) for family, values in families.items()}
    core = geometric([entry["speedup"] for entry in results])
    worst = min(family_scores.values())
    passed = core >= 1.20 and worst >= 0.98
    return {"core_score": core, "worst_family_score": worst, "family_scores": family_scores,
            "runtime_seconds": execution["elapsed_seconds"], "resource_score": min(1.0, 180 / max(0.001, execution["elapsed_seconds"])),
            "valid": True, "passed": passed, "reason": "target met" if passed else "speedup or worst-family target not met",
            "target": {"core_score_min": 1.20, "worst_family_min": 0.98}, "cases": results}


def evaluate(submission, public=False):
    submission = submission.resolve(strict=True)
    if public:
        import importlib.util
        spec = importlib.util.spec_from_file_location("supplied_baseline", ROOT / "participant/baseline/solution.py")
        baseline = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(baseline)
        cases = json.loads((ROOT / "participant/input/examples.json").read_text())["cases"]
        entries = [{"case": case, "family": f"example_{index}", "baseline_cost": independent_check(case, baseline.plan(case))} for index, case in enumerate(cases)]
    else:
        entries = json.loads((ROOT / "evaluator/hidden/cases.json").read_text())
    with tempfile.TemporaryDirectory(prefix="qulacs_fusion_") as temporary:
        work = Path(temporary)
        request_path = work / "request.json"
        response_path = work / "response.json"
        processors = ",".join(map(str, sorted(os.sched_getaffinity(0))[:4]))
        command = ["/usr/bin/taskset", "-c", processors, "/usr/bin/prlimit", "--as=4294967296", "--cpu=720", "--fsize=52428800", "--", "/usr/bin/python3", str(submission / "solution.py"), str(request_path), str(response_path)]
        command = submission_command(submission, work, command)
        request_path.write_text(json.dumps({"cases": [entry["case"] for entry in entries]}))
        execution = run_bounded(command, clean_environment(), 180, work / "process.log")
        if execution["returncode"] != 0 or execution["remaining_owned_descendants"]:
            raise RuntimeError(f"submission process failed: {execution}; { (work / 'process.log').read_text()[-1200:]}")
        if response_path.is_symlink() or not response_path.is_file() or response_path.stat().st_size > 52428800:
            raise ValueError("missing, linked or oversized response")
        response = json.loads(response_path.read_text())
        report = score(entries, response, execution)
    report["submission_sha256"] = hashlib.sha256((submission / "solution.py").read_bytes()).hexdigest()
    report["evaluation_set"] = "public" if public else "hidden"
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--public", action="store_true")
    args = parser.parse_args()
    try:
        report = evaluate(args.submission, args.public)
    except Exception as error:
        report = {"core_score": 0.0, "worst_family_score": 0.0, "resource_score": 0.0, "valid": False,
                  "passed": False, "reason": f"{type(error).__name__}: {error}"}
    text = json.dumps(report, indent=2, allow_nan=False)
    if args.output:
        args.output.write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
