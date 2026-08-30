import search
import concurrent.futures
import json
import time
import numpy as np


def main():
    started = time.monotonic()
    random = np.random.default_rng(55120260828)
    protocol = search.bank("fresh-domain-discovery")
    fields_list = []
    while len(fields_list) < 4500:
        split = int(random.choice([4, 5, 6, 7, 8], p=[.05, .1, .7, .1, .05]))
        strength = random.uniform(1.2, 4.5) if random.random() < .9 else random.uniform(4.5, 7.0)
        noise = np.exp(random.uniform(np.log(.15), np.log(1.2)))
        fields = strength * np.where(np.arange(12) < split, 1.0, -1.0)
        deviations = random.uniform(-noise, noise, 12)
        if split == 6 and random.random() < .25:
            deviations[6:] = random.choice([-1, 1]) * deviations[:6][::-1] + random.uniform(-.25, .25, 6)
        fields += deviations
        fields -= fields.mean()
        try:
            search.validate_fields(fields)
        except ValueError:
            continue
        fields_list.append(fields.tolist())
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(search.evaluate, [(fields, 0, protocol, 0) for fields in fields_list], chunksize=4))
        results.sort(key=lambda row: row["score"], reverse=True)
        print("screened", time.monotonic() - started, results[0]["score"], flush=True)
        results = list(executor.map(search.evaluate, [(row["fields"], row["orientation"], protocol, 4) for row in results[:400]]))
        results.sort(key=lambda row: row["score"], reverse=True)
        (search.OUTPUT / "domains-screen.json").write_text(json.dumps(results, indent=2))
        print("calibrated", time.monotonic() - started, [{key: row.get(key) for key in ("base", "core", "worst", "score")} for row in results[:5]], flush=True)
        protocol = search.bank("fresh-domain-confirmation")
        results = list(executor.map(search.evaluate, [(row["fields"], row["orientation"], protocol, 16) for row in results[:32]]))
        results.sort(key=lambda row: row["score"], reverse=True)
        (search.OUTPUT / "domains.json").write_text(json.dumps(results, indent=2))
        print("confirmed", time.monotonic() - started, [{key: row.get(key) for key in ("base", "core", "worst", "score")} for row in results[:8]], flush=True)


if __name__ == "__main__":
    main()
