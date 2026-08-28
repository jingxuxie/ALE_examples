import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "pilots" / "c02_multiscale_protection"
spec = importlib.util.spec_from_file_location("many_body_evaluator", PILOT / "private" / "evaluator.py")
evaluator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluator)


def wait_json(path, deadline):
    while not path.is_file():
        if time.monotonic() > deadline:
            raise TimeoutError("author precomputation or fresh-run metadata missing: " + str(path))
        time.sleep(10)
    return json.loads(path.read_text())


def normalized_convergence(record):
    block_bounds = []
    for name, floor in (("density", 0.001), ("violation", 0.00002), ("correlation", 0.0001)):
        expected = evaluator.np.asarray(record["reference"][name])
        scale = max(floor, float(evaluator.np.sqrt(evaluator.np.mean(expected**2))))
        block_bounds.append(math.exp(-math.log(10) * record["audit"]["max_differences"][name] / scale))
    return math.prod(block_bounds) ** 0.25


def evaluate_one(split, identifier, metadata, logs, deadline):
    source = PILOT / "private" / "challenge_pool" / split / (identifier + ".json")
    record = wait_json(source, deadline)
    convergence = normalized_convergence(record)
    if convergence < 0.97:
        raise RuntimeError("reference needs independent refinement: " + identifier + " " + str(convergence))
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    result = evaluator.evaluate_record(record, metadata["attempt"], metadata["participant"],
                                       logs / (split + "_executions"))
    if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
        raise RuntimeError("reference changed during evaluation: " + identifier)
    result.update({"reference_sha256": digest, "convergence_lower_bound": convergence})
    checkpoint = logs / "incremental_rows" / split
    checkpoint.mkdir(parents=True, exist_ok=True)
    (checkpoint / (identifier + ".json")).write_text(json.dumps(result, indent=2, allow_nan=False))
    return split, result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--submission-reentrant", action="store_true", required=True)
    arguments = parser.parse_args()
    logs = ROOT / "authoring" / "runs" / PILOT.name / "screening"
    deadline = time.monotonic() + 18000
    metadata = wait_json(logs / "result.json", deadline)
    if not metadata["participant_unchanged"]:
        raise RuntimeError("public artifact changed during fresh attempt")
    jobs = []
    for split, seed_base, count in (("screening", 18300, 2), ("challenge", 29400, 3)):
        for family_index, family in enumerate(("full_half", "linear_spin_one", "inhomogeneous_weak")):
            for index in range(count):
                jobs.append((split, family + "_" + str(seed_base + 17 * family_index + index)))
    rows = {"screening": [], "challenge": []}
    with concurrent.futures.ThreadPoolExecutor(max_workers=arguments.workers) as executor:
        futures = [executor.submit(evaluate_one, split, identifier, metadata, logs, deadline)
                   for split, identifier in jobs]
        for future in concurrent.futures.as_completed(futures):
            split, result = future.result()
            rows[split].append(result)
            expected = 6 if split == "screening" else 9
            print(json.dumps({"split": split, "completed": len(rows[split]), "expected": expected,
                              "id": result["id"], "score": result["score"]}), flush=True)
            if len(rows[split]) == expected:
                report = evaluator.summarize(sorted(rows[split], key=lambda item: item["id"]), split)
                report["execution_policy"] = "Independent one-CPU workers; submission reentrancy audited before launch."
                report["submission_sha256"] = metadata["submission_sha256"]
                (logs / (split + "_evaluation.json")).write_text(json.dumps(report, indent=2, allow_nan=False))
                print(json.dumps({"split": split, "mean_core": report["mean_core"],
                                  "worst_family": report["worst_family"]}), flush=True)


if __name__ == "__main__":
    main()
