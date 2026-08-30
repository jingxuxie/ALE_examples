import search
import concurrent.futures
import json
import time
import numpy as np


def merge(first, second):
    result = dict(second)
    values = np.concatenate([first["values"], second["values"]], axis=1)
    means = values.mean(axis=1)
    core = float(means.mean())
    worst = float(means.min())
    floor = float(np.quantile(values, .15, axis=1).min())
    result.update(values=values.tolist(), core=core, worst=worst, floor=floor,
                  score=core - .45 * (core - worst) - .5 * max(.035 - floor, 0) - .5 * max(.06 - result["base"], 0),
                  training_core=first["core"], holdout_core=second["core"])
    return result


def load_seeds():
    seeds = []
    seen = set()
    for filename in ("domains.json", "refinement/archive.json", "full_archive.json", "refinement/full_archive.json"):
        path = search.OUTPUT / filename
        if not path.exists():
            continue
        for row in json.loads(path.read_text())[:8]:
            key = tuple(row["fields"])
            if key not in seen:
                seen.add(key)
                seeds.append(row)
    return seeds


def propose(random, parents, generation):
    proposals = []
    best = np.asarray(parents[0]["fields"])
    step = [.04, .06, .025][generation % 3]
    for site in range(12):
        fields = best.copy()
        fields[site] += random.choice([-1, 1]) * step
        proposals.append(fields)
    pattern = np.sign(best)
    pattern -= pattern.mean()
    amplitude = np.dot(best, pattern) / np.dot(pattern, pattern)
    residual = best - amplitude * pattern
    for delta in (-.10, -.05, .05, .10):
        proposals.append(best + delta * pattern)
        proposals.append(best + delta * residual)
    for parent in parents[1:3]:
        for repeat in range(4):
            proposals.append(np.asarray(parent["fields"]) + random.normal(0, .04, 12))
    result = []
    for fields in proposals:
        fields -= fields.mean()
        try:
            search.validate_fields(fields)
        except ValueError:
            continue
        result.append(fields.tolist())
    return result


def main():
    started = time.monotonic()
    random = np.random.default_rng(3807239)
    archive = load_seeds()
    monitors = []
    protocol = search.bank("polishing-full-training-0")
    generation = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        archive = list(executor.map(search.evaluate, [(row["fields"], row["orientation"], protocol, 32) for row in archive]))
        while time.monotonic() - started < 1300 and not (search.OUTPUT / "POLISH_STOP").exists():
            generation += 1
            archive.sort(key=lambda row: row["score"], reverse=True)
            archive = archive[:16]
            (search.OUTPUT / "polish-archive.json").write_text(json.dumps(archive, indent=2))
            print({"generation": generation, "seconds": round(time.monotonic() - started), "top": [{key: row.get(key) for key in ("base", "core", "worst", "floor", "score")} for row in archive[:3]]}, flush=True)
            if generation % 2 == 1:
                heldout = search.bank("polishing-monitor-" + str(generation))
                results = list(executor.map(search.evaluate, [(row["fields"], row["orientation"], heldout, 32) for row in archive[:4]]))
                monitors.extend(merge(first, second) for first, second in zip(archive[:4], results))
                monitors.sort(key=lambda row: row["score"], reverse=True)
                (search.OUTPUT / "polish-candidates.json").write_text(json.dumps(monitors, indent=2))
                print({"monitor": generation, "seconds": round(time.monotonic() - started), "best": {key: monitors[0].get(key) for key in ("base", "core", "worst", "floor", "score", "training_core", "holdout_core")}}, flush=True)
            proposals = propose(random, archive[:3], generation)
            base_rows = list(executor.map(search.evaluate, [(fields, -1, protocol, 0) for fields in proposals]))
            base_rows = [row for row in base_rows if row["base"] >= .045]
            results = list(executor.map(search.evaluate, [(row["fields"], -1, protocol, 32) for row in base_rows]))
            archive.extend(results)
            archive.sort(key=lambda row: row["score"], reverse=True)
            archive = archive[:16]
            if generation % 4 == 0:
                protocol = search.bank("polishing-full-training-" + str(generation))
                fresh = load_seeds()
                archive.extend(fresh[:4] + fresh[8:12])
                archive = list(executor.map(search.evaluate, [(row["fields"], row["orientation"], protocol, 32) for row in archive]))
    print({"finished_seconds": time.monotonic() - started}, flush=True)


if __name__ == "__main__":
    main()
