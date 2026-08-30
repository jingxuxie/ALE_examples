import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np
from scipy.special import eval_legendre


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT.parent


def candidate(seed, family, serial):
    random = np.random.default_rng(seed)
    count = 96
    spins = np.tile([0, 0, 2, 4, 6, 8], count // 6)
    dimensions = spins + random.uniform(1.2, 5.4, count)
    dimensions[spins == 0] += 2.0
    dimensions[0] = 1.511
    spins[:36] = 0
    dimensions[1:36] = 3.08 + np.arange(35)*random.uniform(0.04, 0.08)
    count_rows = 40
    times = np.geomspace(0.05, 1.25, count_rows)
    angles = random.uniform(-0.92, 0.99, count_rows)
    if family == "spin_aliases":
        angles = random.uniform(0.85, 0.997, count_rows)
    orders = np.arange(count_rows) % 5
    design = np.exp(-times[:, None]*dimensions)*eval_legendre(spins[None, :], angles[:, None])
    design *= (dimensions[None, :]/8)**orders[:, None]
    columns = np.sqrt(np.mean(design**2, axis=0))
    design /= columns
    max_atoms = 10 if serial % 2 == 0 else 12
    pool = np.arange(1, 36) if family == "crowded_singlets" else np.arange(1, count)
    support = np.r_[0, np.sort(random.choice(pool, max_atoms-1, replace=False))]
    vectors = random.normal(size=(max_atoms, 2))
    vectors /= np.linalg.norm(vectors, axis=1)[:, None]
    magnitudes = random.uniform(0.3, 1.0, max_atoms)
    if family == "mixed_cancellation":
        vectors[:, 0] = np.sqrt(0.5)
        vectors[:, 1] = np.sqrt(0.5)*np.where(np.arange(max_atoms)%2, -1., 1.)
    if family == "weak_residues":
        magnitudes[2:5] *= [0.04, 0.08, 0.16]
    vectors *= magnitudes[:, None]
    vectors[0, 0] = 0.73
    products = np.stack([vectors[:, 0]**2, vectors[:, 0]*vectors[:, 1], vectors[:, 1]**2], axis=1)
    target = design[:, support] @ products
    instance = {"id": f"{family}_{seed}", "family": family, "max_atoms": max_atoms,
                "trace_budget": float(np.sum(vectors**2)*1.03), "shared_ope_squared": 0.73**2,
                "candidates": [{"dimension": float(delta), "spin": int(spin), "column_scale": float(scale)}
                               for delta, spin, scale in zip(dimensions, spins, columns)],
                "probes": [{"t": float(value), "eta": float(angle), "order": int(order)}
                           for value, angle, order in zip(times, angles, orders)],
                "design": design.tolist(), "target": target.tolist(),
                "scales": np.maximum(0.15, np.abs(target)).tolist()}
    witness = {"id": instance["id"], "atoms": [{"index": int(index), "ope": vector.tolist()}
                                              for index, vector in zip(support, vectors)]}
    return instance, witness


def evaluate(item, source, seconds, directory):
    instance, witness = item
    scratch = directory / instance["id"]
    scratch.mkdir(exist_ok=True)
    command = [sys.executable, str(PACKAGE / "authoring/sandbox.py"), "--submission", str(source),
               "--participant", str(ROOT / "participant"), "--scratch", str(scratch),
               "--seconds", str(seconds+5), "--entry", "champion_replay.py"]
    started = time.monotonic()
    try:
        result = subprocess.run(command, input=json.dumps({"instance": instance, "seconds": seconds}),
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=seconds+15)
        (scratch / "stderr.log").write_text(result.stderr)
        (scratch / "stdout.log").write_text(result.stdout)
        answer = json.loads(result.stdout.strip().splitlines()[-1])
        failure = None
    except Exception as error:
        answer = {"id": instance["id"], "atoms": []}
        failure = str(error)
    specification = importlib.util.spec_from_file_location("checker", ROOT / "evaluator/hidden/checker.py")
    checker = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(checker)
    assert checker.check_case(instance, witness)[0]
    valid, residual, reason = checker.check_case(instance, answer)
    record = {"id": instance["id"], "family": instance["family"], "valid": bool(valid),
              "residual": residual if np.isfinite(residual) else None, "reason": failure or reason,
              "seconds": time.monotonic()-started, "planted_valid": True}
    (scratch / "record.json").write_text(json.dumps(record, indent=2)+"\n")
    print(json.dumps(record), flush=True)
    return record


def main():
    directory = ROOT / "adversary/sweep_1"
    directory.mkdir(exist_ok=True)
    source = directory / "replay"
    source.mkdir(exist_ok=True)
    for path in (ROOT / "champions/generation_1").glob("*.py"):
        shutil.copyfile(path, source / path.name)
    shutil.copyfile(ROOT / "adversary/champion_replay.py", source / "champion_replay.py")
    families = ["crowded_singlets", "spin_aliases", "mixed_cancellation", "weak_residues"]
    items = [candidate(7915000+100*family_index+serial, family, serial)
             for family_index, family in enumerate(families) for serial in range(8)]
    (directory / "candidates.json").write_text(json.dumps({"instances": [item[0] for item in items]}))
    (directory / "witnesses.json").write_text(json.dumps({"cases": [item[1] for item in items]}))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(lambda item: evaluate(item, source, 60, directory), items))
    (directory / "results.json").write_text(json.dumps({"tested": len(records), "records": records}, indent=2)+"\n")


if __name__ == "__main__":
    main()
