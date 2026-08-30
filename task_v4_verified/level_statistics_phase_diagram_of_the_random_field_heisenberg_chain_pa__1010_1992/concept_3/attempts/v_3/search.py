import os
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np

ASSETS = Path("/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/level_statistics_phase_diagram_of_the_random_field_heisenberg_chain_pa__1010_1992/concept_3/generations/generation_2/participant")
sys.path.insert(0, str(ASSETS / "workspace"))
from exact import spectrum, proxy_statistics, validate_fields, assess

OUTPUT = Path(__file__).resolve().parent
FAMILIES = (("jitter_004", 1.0, 0.04), ("jitter_012", 1.0, 0.12), ("scale_096", 0.96, 0.08), ("scale_104", 1.04, 0.08))


def bank(seed, count=32, seed_hex=None):
    seed_hex = seed_hex or hashlib.sha256(str(seed).encode()).hexdigest()
    families = []
    for name, scale, amplitude in FAMILIES:
        offsets = []
        for member in range(count):
            uniforms = np.array([2.0 * int.from_bytes(hashlib.sha256(f"{seed_hex}|{name}|{member}|{site}".encode()).digest()[:8], "big") / (2**64 - 1) - 1.0 for site in range(12)])
            offsets.append((amplitude * (uniforms - uniforms.mean())).tolist())
        families.append({"name": name, "scale": scale, "amplitude_before_centering": amplitude, "offsets": offsets})
    protocol = json.loads((ASSETS / "input/protocol.json").read_text())
    protocol["families"] = families
    protocol["generator"]["seed_hex"] = seed_hex
    return protocol


def evaluate(task):
    fields, orientation, protocol, count = task
    try:
        validate_fields(fields)
        base = proxy_statistics(spectrum(fields))["difference"]
        orientation = orientation or (1 if base >= 0 else -1)
        values = []
        for family in protocol["families"]:
            family_values = []
            for offset in family["offsets"][:count]:
                profile = family["scale"] * np.asarray(fields) + offset
                family_values.append(orientation * proxy_statistics(spectrum(profile))["difference"])
            values.append(family_values)
        if count:
            array = np.array(values)
            means = array.mean(axis=1)
            core = float(means.mean())
            worst = float(means.min())
            floor = float(np.quantile(array, 0.15, axis=1).min())
            score = core - 0.45 * (core - worst) - 0.5 * max(0.035 - floor, 0) - 0.5 * max(0.06 - orientation * base, 0)
        else:
            core = worst = floor = 0.0
            score = abs(base)
        return {"fields": list(fields), "orientation": orientation, "base": orientation * base, "core": core, "worst": worst, "floor": floor, "score": score, "values": values}
    except ValueError:
        return {"fields": list(fields), "orientation": orientation or 1, "base": -1.0, "core": -1.0, "score": -1.0}


def candidate(random):
    while True:
        mode = int(random.integers(12))
        width = float(np.exp(random.uniform(np.log(0.8), np.log(7.5))))
        noise = float(np.exp(random.uniform(np.log(0.10), np.log(1.5))))
        sites = np.arange(12)
        if mode <= 2:
            fields = random.uniform(-width, width, 12)
        elif mode == 3:
            fields = np.zeros(12)
            selected = random.choice(12, size=int(random.integers(1, 5)), replace=False)
            fields[selected] = random.choice([-1, 1], len(selected)) * width
        elif mode == 4:
            fields = width * (-1.0) ** sites
        elif mode == 5:
            fields = width * (sites < int(random.integers(2, 11)))
        elif mode == 6:
            fields = width * random.choice([-1, 1], 12)
        elif mode == 7:
            fields = width * np.cos(2 * np.pi * random.uniform(0.06, 0.5) * sites + random.uniform(0, 2 * np.pi))
        elif mode == 8:
            fields = width * (sites / 5.5 - 1)
        elif mode == 9:
            pattern = random.uniform(-width, width, int(random.choice([2, 3, 4, 6])))
            fields = np.tile(pattern, 12 // len(pattern))
        elif mode == 10:
            fields = random.uniform(-width, width, 6)
            fields = np.concatenate([fields, random.choice([-1, 1]) * fields[::-1]])
        else:
            fields = random.uniform(-width, width, 12)
            fields[::2] *= 0.1
        fields = np.asarray(fields, dtype=float) + random.uniform(-noise, noise, 12)
        fields -= fields.mean()
        try:
            validate_fields(fields)
        except ValueError:
            continue
        return fields.tolist()


def mutate(random, parents, generation):
    while True:
        parent = parents[int(random.integers(len(parents)))]
        fields = np.asarray(parent["fields"]).copy()
        mode = random.random()
        width = random.choice([0.01, 0.025, 0.05, 0.10, 0.20, 0.40], p=[0.08, 0.15, 0.25, 0.25, 0.20, 0.07])
        if mode < 0.60:
            fields += random.normal(0, width, 12)
        elif mode < 0.76:
            fields[int(random.integers(12))] += random.normal(0, width * 3)
        elif mode < 0.9:
            fields *= random.uniform(0.94, 1.06)
            fields += random.normal(0, width / 3, 12)
        else:
            other = np.asarray(parents[int(random.integers(len(parents)))]["fields"])
            if np.linalg.norm(fields - other) < 3:
                fields += random.uniform(-0.6, 0.6) * (other - fields)
            else:
                fields += random.normal(0, width, 12)
        fields -= fields.mean()
        try:
            validate_fields(fields)
        except ValueError:
            continue
        return fields.tolist(), parent["orientation"]


def log(message):
    print(message, flush=True)


def main():
    global OUTPUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=2500)
    parser.add_argument("--initial", type=int, default=3000)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=831901)
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--probes", type=int, default=6)
    parser.add_argument("--output-directory", type=Path, default=OUTPUT)
    args = parser.parse_args()
    OUTPUT = args.output_directory.resolve()
    OUTPUT.mkdir(exist_ok=True)
    random = np.random.default_rng(args.seed)
    started = time.monotonic()
    training = bank("training-" + str(args.seed))
    public = json.loads((ASSETS / "input/protocol.json").read_text())
    archive = []
    full_archive = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
        if args.resume:
            seeds = json.loads(args.resume.read_text())[:40]
            archive = list(executor.map(evaluate, [(row["fields"], row["orientation"], training, args.probes) for row in seeds]))
        else:
            tasks = [(candidate(random), 0, training, 0) for _ in range(args.initial)]
            screened = list(executor.map(evaluate, tasks, chunksize=4))
            screened.sort(key=lambda row: row["score"], reverse=True)
            (OUTPUT / "screened.json").write_text(json.dumps(screened[:300]))
            log({"phase": "base_screen", "seconds": time.monotonic() - started, "top": [(row["base"], row["fields"]) for row in screened[:8]]})
            tasks = [(row["fields"], row["orientation"], training, 4) for row in screened[:200]]
            archive = list(executor.map(evaluate, tasks))
        archive.sort(key=lambda row: row["score"], reverse=True)
        generation = 0
        while time.monotonic() - started < args.seconds and not (OUTPUT / "STOP").exists():
            generation += 1
            archive.sort(key=lambda row: row["score"], reverse=True)
            archive = archive[:40]
            (OUTPUT / "archive.json").write_text(json.dumps(archive, indent=2))
            log({"generation": generation, "seconds": round(time.monotonic() - started), "top": [{key: row.get(key) for key in ("base", "core", "worst", "floor", "score")} for row in archive[:5]]})
            if generation % 3 == 1:
                finalists = archive[:8]
                checked = list(executor.map(evaluate, [(row["fields"], row["orientation"], public, 32) for row in finalists]))
                full_archive.extend(checked)
                full_archive.sort(key=lambda row: row["score"], reverse=True)
                (OUTPUT / "full_archive.json").write_text(json.dumps(full_archive, indent=2))
                best = full_archive[0]
                witness = {"schema_version": 1, "fields": best["fields"], "orientation": best["orientation"]}
                (OUTPUT / "witness.json").write_text(json.dumps(witness, indent=2) + "\n")
                log({"phase": "public_full", "seconds": round(time.monotonic() - started), "best": {key: best[key] for key in ("base", "core", "worst", "floor", "score")}})
            parents = archive[:16]
            proposals = [mutate(random, parents, generation) for _ in range(100)]
            proposals += [(candidate(random), 0) for _ in range(12)]
            base_rows = list(executor.map(evaluate, [(fields, orientation, training, 0) for fields, orientation in proposals]))
            base_rows = [row for row in base_rows if row["base"] >= 0.045]
            if generation % 3 == 0:
                training = bank("training-" + str(args.seed) + "-" + str(generation))
                base_rows.extend(archive[:24])
                archive = []
            results = list(executor.map(evaluate, [(row["fields"], row["orientation"], training, args.probes) for row in base_rows]))
            archive.extend(results)
    log({"finished_seconds": time.monotonic() - started})


if __name__ == "__main__":
    main()
