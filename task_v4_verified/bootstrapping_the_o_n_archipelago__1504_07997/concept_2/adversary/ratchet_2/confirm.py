import concurrent.futures
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import mpmath as mp


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("checker", ROOT / "evaluator/hidden/checker.py")
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def independent_check(instance, answer):
    with mp.workdps(80):
        residual = mp.mpf(0)
        trace = mp.mpf(0)
        shared = None
        indices = set()
        for atom in answer["atoms"]:
            index = atom["index"]
            assert type(index) is int and 0 <= index < len(instance["candidates"]) and index not in indices
            indices.add(index)
            vector = list(map(lambda value: mp.mpf(str(value)), atom["ope"]))
            assert len(vector) == 2 and all(mp.isfinite(value) and abs(value) <= 4 for value in vector)
            trace += sum(value ** 2 for value in vector)
            if index == 0:
                shared = vector[0] ** 2
        for row, target in enumerate(instance["target"]):
            for component in range(3):
                predicted = mp.mpf(0)
                for atom in answer["atoms"]:
                    first, second = [mp.mpf(str(value)) for value in atom["ope"]]
                    product = (first ** 2, first * second, second ** 2)[component]
                    predicted += mp.mpf(str(instance["design"][row][atom["index"]])) * product
                residual = max(residual, abs(predicted - mp.mpf(str(target[component]))) / mp.mpf(str(instance["scales"][row][component])))
        valid = (1 <= len(indices) <= instance["max_atoms"] and shared is not None
                 and abs(shared - mp.mpf(str(instance["shared_ope_squared"]))) <= mp.mpf("2e-10")
                 and trace <= mp.mpf(str(instance["trace_budget"])) + mp.mpf("2e-10")
                 and residual <= mp.mpf("2e-8"))
        return {"valid": bool(valid), "residual": mp.nstr(residual, 20), "trace": mp.nstr(trace, 20)}


def run_case(instance, witness, cpu, seconds=300):
    directory = HERE / "confirmations" / instance["id"]
    directory.mkdir(parents=True, exist_ok=True)
    input_path = directory / "instance.json"
    output_path = directory / "answer.json"
    input_path.write_text(json.dumps({"instances": [instance]}))
    planted = independent_check(instance, witness)
    assert planted["valid"] and checker.check_case(instance, witness)[0]
    command = ["taskset", "-c", str(cpu), sys.executable, str(ROOT.parent / "authoring/sandbox.py"),
               "--submission", str(HERE / "replay"), "--participant", str(ROOT / "participant"),
               "--scratch", str(directory), "--entry", "solve.py", "--seconds", str(seconds + 10),
               "--memory-mib", "1024", "--", str(input_path), str(output_path),
               "--seconds-per-case", str(seconds)]
    started = time.monotonic()
    with (directory / "stdout.log").open("w") as stdout, (directory / "stderr.log").open("w") as stderr:
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True,
                                   env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", OPENBLAS_NUM_THREADS="1"))
        timed_out = False
        try:
            process.wait(timeout=seconds + 20)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
    elapsed = time.monotonic() - started
    answer = json.loads(output_path.read_text())["cases"][0] if output_path.exists() else {"id": instance["id"], "atoms": []}
    valid, residual, reason = checker.check_case(instance, answer)
    independently = independent_check(instance, answer)
    record = {"id": instance["id"], "family": instance["family"], "budget_seconds": seconds,
              "elapsed_seconds": elapsed, "cpu": cpu, "exit_code": process.returncode, "timed_out": timed_out,
              "valid": bool(valid), "residual": residual if residual != float("inf") else None,
              "reason": reason, "independent": independently, "planted": planted,
              "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
              "source_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (HERE / "replay").glob("*.py")}}
    (directory / "record.json").write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")
    print(json.dumps(record), flush=True)
    return record


def main():
    candidates = json.loads((ROOT / "adversary/sweep_1/candidates.json").read_text())["instances"]
    witnesses = {case["id"]: case for case in json.loads((ROOT / "adversary/sweep_1/witnesses.json").read_text())["cases"]}
    completed = [json.loads(path.read_text()) for path in (ROOT / "adversary/sweep_1").glob("*/record.json")]
    selected = []
    for family in ("crowded_singlets", "spin_aliases", "mixed_cancellation", "weak_residues"):
        ranked = sorted([record for record in completed if record["family"] == family and not record["valid"]
                         and record["reason"] == "moment residual" and record["residual"] is not None],
                        key=lambda record: record["residual"], reverse=True)
        selected.extend(record["id"] for record in ranked[:2])
    assert len(selected) == 8
    instances = {instance["id"]: instance for instance in candidates}
    (HERE / "selection.json").write_text(json.dumps({"selection_rule": "two highest completed moment-residual failures per family",
                                                    "ids": selected}, indent=2) + "\n")
    cpus = sorted(os.sched_getaffinity(0))[-8:]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(run_case, instances[identifier], witnesses[identifier], cpus[index % len(cpus)])
                   for index, identifier in enumerate(selected)]
        records = [future.result() for future in futures]
    (HERE / "results.json").write_text(json.dumps({"records": records}, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
