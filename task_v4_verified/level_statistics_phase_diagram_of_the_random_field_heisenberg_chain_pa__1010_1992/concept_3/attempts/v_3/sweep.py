import search
import concurrent.futures
import json
import numpy as np


def main():
    rows = json.loads((search.OUTPUT / "full_archive.json").read_text())
    fields = np.asarray(rows[0]["fields"])
    pattern = np.where(fields > 0, 1.0, -1.0)
    if sum(pattern) != 0:
        return
    amplitude = np.dot(fields, pattern) / 12
    residual = fields - amplitude * pattern
    protocol = search.bank("amplitude-width-sweep")
    tasks = []
    parameters = []
    for strength in np.arange(1.5, 7.76, 0.25):
        for width in (0.5, 0.75, 1.0, 1.25):
            profile = strength * pattern + width * residual
            if max(abs(profile)) > 8:
                continue
            tasks.append((profile.tolist(), -1, protocol, 4))
            parameters.append([float(strength), width])
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(search.evaluate, tasks))
    for result, parameter in zip(results, parameters):
        result["parameters"] = parameter
    results.sort(key=lambda row: row["score"], reverse=True)
    (search.OUTPUT / "sweep.json").write_text(json.dumps(results, indent=2))
    for row in results[:10]:
        print({key: row.get(key) for key in ("parameters", "base", "core", "worst", "score")}, flush=True)


if __name__ == "__main__":
    main()
