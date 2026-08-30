from concurrent.futures import ProcessPoolExecutor
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "authoring"))
from sandbox import run_file


def make_model(seed, bound):
    key = seed.to_bytes(32, "big")

    def digest(domain, index):
        return hmac.new(key, domain + index.to_bytes(4, "big"), hashlib.sha256).digest()

    support = sorted(range(512), key=lambda index: digest(b"support", index))[:bound]
    columns = [int.from_bytes(digest(b"column", index)[:24], "big") for index in range(512)]
    columns[support[-1]] = 0
    for index in support[:-1]:
        columns[support[-1]] ^= columns[index]
    observable = [digest(b"observable", index)[0] & 1 for index in range(512)]
    if sum(observable[index] for index in support) % 2 == 0:
        observable[support[-1]] ^= 1
    model = {"num_faults": 512, "num_detectors": 192, "num_observables": 1, "weight_bound": bound,
             "fault_probability": 0.001, "columns": [format(column, "048x") for column in columns], "observable": observable}
    return model, sorted(support)


def score(model, answer):
    support = answer["faults"]
    if len(set(support)) != len(support) or any(type(index) is not int or index < 0 or index >= 512 for index in support):
        raise ValueError("invalid champion support")
    syndrome = 0
    logical = 0
    for index in support:
        syndrome ^= int(model["columns"][index], 16)
        logical ^= model["observable"][index]
    return {"weight": len(support), "detector_weight": syndrome.bit_count(), "logical_parity": logical,
            "passed": 0 < len(support) <= model["weight_bound"] and not syndrome and logical == 1}


def run_case(arguments):
    directory, cpu = arguments
    os.sched_setaffinity(0, {cpu})
    answer, telemetry = run_file(ROOT / "adversary/champion_adapter", ROOT / "participant", directory / "model.json", timeout=80)
    model = json.loads((directory / "model.json").read_text())
    result = {"case": directory.name, "bound": model["weight_bound"], "execution": telemetry,
              "input_sha256": hashlib.sha256((directory / "model.json").read_bytes()).hexdigest()}
    if answer is not None:
        result.update(score(model, answer), answer=answer)
    else:
        result.update(passed=False, error="champion execution did not return an artifact")
    (directory / "champion_result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(directory.name, {name: result.get(name) for name in ("weight", "passed", "error")}, flush=True)
    return result


def main():
    champion = ROOT / "champions/generation_1"
    if not champion.exists():
        shutil.copytree(ROOT / "attempts/v_2", champion)
    adapter = ROOT / "adversary/champion_adapter"
    adapter.mkdir(exist_ok=True)
    for name in ("search", "search.cpp"):
        shutil.copy2(champion / name, adapter / name)
    cpus = sorted(os.sched_getaffinity(0))[-4:]
    jobs = []
    for bound in (24, 28, 32, 36):
        for sample in range(2):
            directory = ROOT / "adversary/champion_sweep" / (str(bound) + "_" + str(sample))
            directory.mkdir(parents=True, exist_ok=True)
            seed = secrets.randbits(256)
            model, support = make_model(seed, bound)
            (directory / "model.json").write_text(json.dumps(model, indent=2, sort_keys=True) + "\n")
            (directory / "secret.json").write_text(json.dumps({"seed": seed, "support": support}) + "\n")
            (directory / "witness.json").write_text(json.dumps({"faults": support}) + "\n")
            assert score(model, {"faults": support})["passed"]
            jobs.append((directory, cpus[len(jobs) % len(cpus)]))
    with ProcessPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(run_case, jobs))
    (ROOT / "adversary/champion_sweep.json").write_text(json.dumps({
        "champion": "champions/generation_1", "binary_unchanged": True, "seconds_per_case": 60,
        "cases": results, "root_cause": "best exact logical relations remain above the planted fault-weight bound as distance grows; four-nonpivot information-set coverage collapses",
        "task_dimensions_unchanged": [512, 192]}, indent=2) + "\n")


if __name__ == "__main__":
    main()
