import argparse
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

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
import mpmath as mp
import numpy as np
from scipy.special import eval_legendre


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FAMILIES = ("crowded_singlets", "spin_aliases", "mixed_cancellation", "weak_residues")
GRID = ((12, 18, 1), (14, 18, 2), (16, 16, 2), (18, 14, 1),
        (20, 12, 2), (22, 10, 3), (24, 16, 2), (26, 18, 3))


def module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(result)
    return result


previous = module("previous_confirmation", ROOT / "adversary/ratchet_2/confirm.py")
checker = previous.checker


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidate(family, serial, seed_offset=0):
    seed_value = 2026082811 + 1009 * FAMILIES.index(family) + serial * 104729 + seed_offset
    random = np.random.default_rng(seed_value)
    rows, count, order_cycle = GRID[serial]
    assert 3 * rows >= 2 * count - 1
    spins = np.tile([0, 0, 2, 4, 6, 8], 16)
    dimensions = spins + random.uniform(1.2, 5.4, 96)
    dimensions[spins == 0] += 2
    spins[:36] = 0
    dimensions[0] = 1.511
    dimensions[1:36] = 3.08 + np.arange(35) * random.uniform(0.04, 0.08)
    times = np.geomspace(0.05, 1.25, rows)
    angles = random.uniform(0.90, 0.998, rows) if family == "spin_aliases" else random.uniform(-0.92, 0.99, rows)
    orders = np.arange(rows) % order_cycle
    design = np.exp(-times[:, None] * dimensions) * eval_legendre(spins[None, :], angles[:, None])
    design *= (dimensions[None, :] / 8) ** orders[:, None]
    scales = np.sqrt(np.mean(design ** 2, axis=0))
    design /= scales
    pool = np.arange(1, 36) if family == "crowded_singlets" else np.arange(1, 96)
    support = np.r_[0, np.sort(random.choice(pool, count - 1, replace=False))]
    vectors = random.normal(size=(count, 2))
    vectors /= np.linalg.norm(vectors, axis=1)[:, None]
    magnitudes = random.uniform(0.3, 1, count)
    if family == "mixed_cancellation":
        vectors[:, 0] = np.sqrt(0.5)
        vectors[:, 1] = np.sqrt(0.5) * np.where(np.arange(count) % 2, -1, 1)
    if family == "weak_residues":
        magnitudes[2:5] *= [0.04, 0.08, 0.16]
    vectors *= magnitudes[:, None]
    vectors[0, 0] = 0.73
    products = np.stack([vectors[:, 0] ** 2, vectors[:, 0] * vectors[:, 1], vectors[:, 1] ** 2], axis=1)
    target = design[:, support] @ products
    identifier = "scan_%02d_%02d" % (FAMILIES.index(family), serial)
    instance = {"id": identifier, "family": family, "max_atoms": count,
                "trace_budget": float(np.sum(vectors ** 2) * 1.03), "shared_ope_squared": 0.73 ** 2,
                "candidates": [{"dimension": float(dimension), "spin": int(spin), "column_scale": float(scale)}
                               for dimension, spin, scale in zip(dimensions, spins, scales)],
                "probes": [{"t": float(position), "eta": float(angle), "order": int(order)}
                           for position, angle, order in zip(times, angles, orders)],
                "design": design.tolist(), "target": target.tolist(), "scales": np.maximum(0.15, np.abs(target)).tolist()}
    witness = {"id": identifier, "atoms": [{"index": int(index), "ope": vector.tolist()} for index, vector in zip(support, vectors)]}
    return instance, witness, {"seed": seed_value, "rows": rows, "max_atoms": count, "order_cycle": order_cycle,
                               "coupled_equations": 3 * rows, "fixed_support_ope_parameters": 2 * count - 1}


def validate(instance, witness):
    check = previous.independent_check(instance, witness)
    assert check["valid"] and checker.check_case(instance, witness)[0]
    with mp.workdps(80):
        maximum = mp.mpf(0)
        for row, probe in enumerate(instance["probes"]):
            for column, entry in enumerate(instance["candidates"]):
                dimension = mp.mpf(str(entry["dimension"]))
                expected = (mp.exp(-mp.mpf(str(probe["t"])) * dimension)
                            * mp.legendre(entry["spin"], mp.mpf(str(probe["eta"])))
                            * (dimension / 8) ** probe["order"] / mp.mpf(str(entry["column_scale"])))
                maximum = max(maximum, abs(expected - mp.mpf(str(instance["design"][row][column]))) / max(1, abs(expected)))
        assert maximum < mp.mpf("1e-12")
        check["kernel_error_80_digits"] = mp.nstr(maximum, 20)
    return check


def run(instance, seconds, cpu, label):
    directory = HERE / label / instance["id"]
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / "instance.json"
    output = directory / "answer.json"
    write(source, {"instances": [instance]})
    command = ["taskset", "-c", str(cpu), sys.executable, str(ROOT.parent / "authoring/sandbox.py"),
               "--submission", str(HERE / "replay"), "--participant", str(ROOT / "participant"),
               "--scratch", str(directory), "--entry", "solve.py", "--seconds", str(seconds + 10),
               "--memory-mib", "1024", "--", str(source), str(output), "--seconds-per-case", str(seconds)]
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
    answer = json.loads(output.read_text())["cases"][0] if output.exists() else {"id": instance["id"], "atoms": []}
    valid, residual, reason = checker.check_case(instance, answer)
    logs = (directory / "stderr.log").read_text()
    errors = [line for line in logs.splitlines() if line.startswith("STAGE_ERROR") and "StageTimeout" not in line]
    record = {"id": instance["id"], "family": instance["family"], "rows": len(instance["probes"]),
              "max_atoms": instance["max_atoms"], "budget_seconds": seconds, "elapsed_seconds": time.monotonic() - started,
              "exit_code": process.returncode, "timed_out": timed_out, "valid": bool(valid),
              "residual": residual if np.isfinite(residual) else None, "reason": reason,
              "continuous_attempted": "CONTINUOUS " in logs, "stage_errors": errors,
              "input_sha256": digest(source), "source_hashes": {path.name: digest(path) for path in (HERE / "replay").glob("*.py")},
              "independent": previous.independent_check(instance, answer)}
    write(directory / "record.json", record)
    print(json.dumps(record), flush=True)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true")
    arguments = parser.parse_args()
    if not arguments.confirm:
        cases, witnesses, validations = [], [], []
        for family in FAMILIES:
            for serial in range(8):
                instance, witness, specification = candidate(family, serial)
                validations.append(dict(validate(instance, witness), id=instance["id"], specification=specification))
                cases.append(instance)
                witnesses.append(witness)
        write(HERE / "candidates.json", {"instances": cases})
        write(HERE / "witnesses.json", {"cases": witnesses})
        write(HERE / "candidate_validation.json", {"cases": validations})
        label, seconds = "screening", 60
    else:
        all_cases = {instance["id"]: instance for instance in json.loads((HERE / "candidates.json").read_text())["instances"]}
        completed = [json.loads(path.read_text()) for path in (HERE / "screening").glob("*/record.json")]
        selected = []
        for family in FAMILIES:
            failures = [record for record in completed if record["family"] == family and not record["valid"]
                        and record["reason"] == "moment residual" and record["exit_code"] == 0
                        and not record["timed_out"] and record["continuous_attempted"] and not record["stage_errors"]]
            failures.sort(key=lambda record: record["residual"], reverse=True)
            selected.extend(failures[:3])
        if not selected:
            raise RuntimeError("no confirmed-eligible screening failures")
        cases = [all_cases[record["id"]] for record in selected]
        write(HERE / "confirmation_selection.json", {"records": selected})
        label, seconds = "confirmation", 300
    workers = 12 if arguments.confirm else 8
    cpus = sorted(os.sched_getaffinity(0))[-24:-12] if arguments.confirm else sorted(os.sched_getaffinity(0))[-8:]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run, instance, seconds, cpus[index % len(cpus)], label) for index, instance in enumerate(cases)]
        records = [future.result() for future in futures]
    write(HERE / (label + "_results.json"), {"records": records})


if __name__ == "__main__":
    main()
