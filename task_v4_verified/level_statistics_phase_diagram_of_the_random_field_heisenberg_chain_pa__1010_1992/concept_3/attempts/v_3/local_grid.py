import search
import concurrent.futures
import json
import secrets
import time
import numpy as np
from select_candidate import measure


def summarize(fields, reports, random):
    if not all(report["valid"] for report in reports):
        return {"fields": fields, "orientation": -1, "base": -1, "score": -1}
    values = np.concatenate([report["values"] for report in reports], axis=1)
    means = values.mean(axis=1)
    indices = random.integers(values.shape[1], size=(6000, 4, 32))
    samples = values[np.arange(4)[None, :, None], indices]
    sampled_means = samples.mean(axis=2)
    passes = (sampled_means.mean(axis=1) >= .06) & (sampled_means.min(axis=1) >= .05) & ((samples >= .025).sum(axis=2).min(axis=1) >= 24)
    base = reports[0]["base"]
    return {"fields": fields, "orientation": -1, "base": base,
            "core": float(means.mean()), "worst": float(means.min()),
            "score": float(passes.mean()) if base >= .055 else -1,
            "values": values.tolist(), "family_means": means.tolist(),
            "floor_fractions": (values >= .025).mean(axis=1).tolist()}


def stage(executor, profiles, label):
    protocols = [search.bank(label, seed_hex=secrets.token_hex(32)) for repeat in range(2)]
    for index, protocol in enumerate(protocols):
        (search.OUTPUT / f"{label}-protocol-{index}.json").write_text(json.dumps(protocol, indent=2))
    candidates = [{"fields": fields, "orientation": -1} for fields in profiles]
    tasks = [(candidate, protocol, candidate_index, bank_index) for candidate_index, candidate in enumerate(candidates) for bank_index, protocol in enumerate(protocols)]
    reports = list(executor.map(measure, tasks))
    random = np.random.default_rng(405134)
    results = [summarize(fields, [report for report in reports if report["candidate"] == index], random) for index, fields in enumerate(profiles)]
    results.sort(key=lambda row: (row["score"], row.get("core", -1)), reverse=True)
    (search.OUTPUT / f"{label}.json").write_text(json.dumps(results, indent=2))
    return results


def main():
    started = time.monotonic()
    witness = json.loads((search.OUTPUT / "selection-witness.json").read_text())
    fields = np.asarray(witness["fields"])
    pattern = np.sign(fields)
    assert np.sum(pattern) == 0
    amplitude = np.dot(fields, pattern) / 12
    residual = fields - amplitude * pattern
    profiles = []
    for delta in (-.10, -.05, 0, .05, .10, .15, .20):
        for width in (.94, 1.0, 1.06):
            profile = (amplitude + delta) * pattern + width * residual
            profile -= profile.mean()
            profiles.append(profile.tolist())
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        first = stage(executor, profiles, "local-strength")
        print({"stage": "strength", "seconds": round(time.monotonic() - started), "top": [{key: row.get(key) for key in ("base", "core", "worst", "score")} for row in first[:5]]}, flush=True)
        fields = np.asarray(first[0]["fields"])
        amplitude = np.dot(fields, pattern) / 12
        residual = fields - amplitude * pattern
        positive = residual * (pattern > 0)
        negative = residual * (pattern < 0)
        profiles = []
        for positive_width in (.90, .95, 1.0, 1.05, 1.10):
            for negative_width in (.90, .95, 1.0, 1.05, 1.10):
                profile = amplitude * pattern + positive_width * positive + negative_width * negative
                profile -= profile.mean()
                profiles.append(profile.tolist())
        second = stage(executor, profiles, "local-widths")
        combined = sorted(first + second, key=lambda row: (row["score"], row.get("core", -1)), reverse=True)
        (search.OUTPUT / "local-grid.json").write_text(json.dumps(combined, indent=2))
        print({"stage": "widths", "seconds": round(time.monotonic() - started), "top": [{key: row.get(key) for key in ("base", "core", "worst", "score")} for row in second[:5]]}, flush=True)


if __name__ == "__main__":
    main()
