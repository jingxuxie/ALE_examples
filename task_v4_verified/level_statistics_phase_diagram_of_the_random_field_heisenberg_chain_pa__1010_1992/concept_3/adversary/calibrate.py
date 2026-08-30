import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))

import numpy as np
from exact import ratios, spectrum, symmetry_distance


def window_statistics(energies):
    dimension = len(energies)
    lower, upper = dimension // 3, 2 * dimension // 3
    reference = float(np.mean(ratios(energies[lower:upper])))
    density = (energies - energies[0]) / (energies[-1] - energies[0])
    result = {"rank_r": reference, "rank_count": upper - lower - 2}
    for fraction in (1 / 3, 0.25, 0.2):
        selected = energies[(density >= fraction) & (density <= 1 - fraction)]
        name = f"energy_{fraction:.4f}"
        result[name] = float(np.mean(ratios(selected))) - reference
        result[name + "_count"] = len(selected) - 2
    center = int(np.argmin(np.abs(density - 0.5)))
    for count in (96, 128, 160, 192):
        start = max(0, min(dimension - count, center - count // 2))
        result[f"center_{count}"] = float(np.mean(ratios(energies[start:start + count]))) - reference
    for count in (96, 128, 160):
        estimates = []
        for target in (0.49, 0.5, 0.51):
            center = int(np.argmin(np.abs(density - target)))
            start = max(0, min(dimension - count, center - count // 2))
            estimates.append(float(np.mean(ratios(energies[start:start + count]))))
        result[f"triple_{count}"] = float(np.mean(estimates)) - reference
    return result


def generate(seed, count):
    random = np.random.default_rng(seed)
    sites = np.arange(12)
    candidates = []
    while len(candidates) < count:
        index = len(candidates)
        kind = index % 10
        strength = random.uniform(0.8, 7)
        noise = random.uniform(0.08, 1.2)
        if kind == 0:
            fields = random.uniform(-strength, strength, 12)
        elif kind in (1, 2, 3, 4, 5):
            block = (1, 2, 3, 4, 6)[kind - 1]
            fields = strength * (2 * ((sites // block) % 2) - 1)
            fields = fields + random.uniform(-noise, noise, 12)
        elif kind == 6:
            fields = strength * np.cos(2 * np.pi * random.choice([1, 2, 3, 5]) * sites / 12 + random.uniform(0, 6.28))
            fields += random.uniform(-noise, noise, 12)
        elif kind == 7:
            fields = np.linspace(-strength, strength, 12) + random.uniform(-noise, noise, 12)
        elif kind == 8:
            fields = random.uniform(-noise, noise, 12)
            impurities = random.choice(12, size=int(random.integers(1, 5)), replace=False)
            fields[impurities] += strength * random.choice([-1, 1], size=len(impurities))
        else:
            fields = strength * np.cos(2 * np.pi * 0.6180339887498949 * sites + random.uniform(0, 6.28))
            fields += random.uniform(-noise, noise, 12)
        fields -= fields.mean()
        if max(abs(fields)) > 7.8 or np.std(fields) < 0.65 or symmetry_distance(fields) < 0.12:
            continue
        candidates.append({"index": index, "kind": kind, "fields": fields.tolist()})
    return candidates


def measure(candidate):
    started = time.monotonic()
    try:
        return {**candidate, "statistics": window_statistics(spectrum(candidate["fields"])),
                "seconds": time.monotonic() - started}
    except ValueError as error:
        return {**candidate, "error": str(error)}


def robust(candidate):
    random = np.random.default_rng(74683)
    fields = np.array(candidate["fields"])
    rows = []
    for amplitude in (0.02, 0.06, 0.12):
        for repeat in range(4):
            displacement = random.uniform(-amplitude, amplitude, 12)
            displacement -= displacement.mean()
            rows.append(window_statistics(spectrum(fields + displacement)))
    for scale in (0.96, 1.04):
        rows.append(window_statistics(spectrum(fields * scale)))
    metrics = [name for name in rows[0] if not name.endswith("count") and name != "rank_r"]
    summaries = {}
    for name in metrics:
        values = [row[name] for row in rows]
        summaries[name] = {"mean": float(np.mean(values)), "min": min(values), "max": max(values),
                           "families": [float(np.mean(values[start:start + 4])) for start in (0, 4, 8)],
                           "scale": values[-2:]}
    return {**candidate, "robust": summaries}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=800)
    parser.add_argument("--seed", type=int, default=301992)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--shortlist", type=int, default=36)
    parser.add_argument("--label", default="pilot")
    arguments = parser.parse_args()
    started = time.monotonic()
    candidates = generate(arguments.seed, arguments.count)
    records = []
    destination = ROOT / "adversary" / (arguments.label + ".jsonl")
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(8, max(1, arguments.workers))) as executor:
        with destination.open("w") as output:
            for record in executor.map(measure, candidates, chunksize=1):
                output.write(json.dumps(record) + "\n")
                output.flush()
                records.append(record)
                if len(records) % 100 == 0:
                    print(json.dumps({"measured": len(records), "seconds": time.monotonic() - started}), flush=True)
        usable = [record for record in records if "statistics" in record]
        metrics = [name for name in usable[0]["statistics"] if not name.endswith("count") and name != "rank_r"]
        selected = {}
        for name in metrics:
            leaders = sorted(usable, key=lambda record: abs(record["statistics"][name]), reverse=True)
            for record in leaders[:arguments.shortlist]:
                selected[record["index"]] = record
        print(json.dumps({"robust_shortlist": len(selected)}), flush=True)
        checked = []
        with (ROOT / "adversary" / (arguments.label + "_robust.jsonl")).open("w") as output:
            for record in executor.map(robust, selected.values(), chunksize=1):
                checked.append(record)
                output.write(json.dumps(record) + "\n")
                output.flush()
        summary = {name: sorted(checked, key=lambda record: abs(record["robust"][name]["mean"]), reverse=True)[:5]
                   for name in metrics}
        (ROOT / "adversary" / (arguments.label + "_summary.json")).write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps({name: [{"index": row["index"], **row["robust"][name]} for row in leaders]
                          for name, leaders in summary.items()}, indent=2), flush=True)
    print(json.dumps({"total_seconds": time.monotonic() - started}), flush=True)


if __name__ == "__main__":
    main()
