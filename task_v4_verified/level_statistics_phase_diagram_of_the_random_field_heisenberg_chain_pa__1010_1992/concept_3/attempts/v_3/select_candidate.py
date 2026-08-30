import search
import argparse
import concurrent.futures
import json
from pathlib import Path
import secrets
import time
import numpy as np
from exact import assess


def measure(task):
    candidate, protocol, candidate_index, bank_index = task
    witness = {"schema_version": 1, "fields": candidate["fields"], "orientation": candidate["orientation"]}
    try:
        report = assess(witness, protocol)
    except ValueError as error:
        return {"candidate": candidate_index, "bank": bank_index, "valid": False, "error": str(error)}
    values = [[member["signed_difference"] for member in report["members"] if member["family"] == family["family"]] for family in report["families"]]
    return {"candidate": candidate_index, "bank": bank_index, "valid": report["valid"], "pass": report["pass"],
            "core": report["core"], "worst": report["worst_family"], "base": report["base"]["signed_difference"],
            "coverage": [family["above_member_floor"] for family in report["families"]], "values": values,
            "minimum_gap": min([report["base"]["minimum_gap"]] + [member["minimum_gap"] for member in report["members"]])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=16)
    parser.add_argument("--banks", type=int, default=3)
    parser.add_argument("--tag", default="selection")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--sources", nargs="+", default=["polish-candidates.json", "polish-archive.json", "refinement/full_archive.json", "refinement/archive.json", "domains.json"])
    args = parser.parse_args()
    started = time.monotonic()
    sources = []
    for filename in args.sources:
        path = search.OUTPUT / filename
        if path.exists():
            rows = json.loads(path.read_text())
            sources.append(rows[:2] if filename == "domains.json" else rows)
    candidates = []
    for rank in range(20):
        for source in sources:
            if rank >= len(source):
                continue
            candidate = source[rank]
            if candidate["base"] < .055:
                continue
            fields = np.asarray(candidate["fields"])
            if any(np.sqrt(np.mean((fields - previous["fields"]) ** 2)) < .005 for previous in candidates):
                continue
            candidates.append(candidate)
    candidates = candidates[:args.limit]
    directory = search.OUTPUT / args.tag
    directory.mkdir(exist_ok=True)
    (directory / "candidates.json").write_text(json.dumps(candidates, indent=2))
    protocols = []
    for index in range(args.banks):
        protocol = search.bank(args.tag + str(index), seed_hex=secrets.token_hex(32))
        protocols.append(protocol)
        (directory / f"protocol-{index}.json").write_text(json.dumps(protocol, indent=2))
    tasks = [(candidate, protocol, candidate_index, bank_index) for candidate_index, candidate in enumerate(candidates) for bank_index, protocol in enumerate(protocols)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
        reports = list(executor.map(measure, tasks))
    (directory / "reports.json").write_text(json.dumps(reports, indent=2))
    random = np.random.default_rng(370122)
    summaries = []
    for index, candidate in enumerate(candidates):
        selected = [report for report in reports if report["candidate"] == index]
        if not all(report["valid"] for report in selected):
            continue
        values = np.concatenate([report["values"] for report in selected], axis=1)
        means = values.mean(axis=1)
        indices = random.integers(values.shape[1], size=(12000, 4, 32))
        samples = values[np.arange(4)[None, :, None], indices]
        sampled_means = samples.mean(axis=2)
        passes = (sampled_means.mean(axis=1) >= .060) & (sampled_means.min(axis=1) >= .050) & ((samples >= .025).sum(axis=2).min(axis=1) >= 24)
        summaries.append({"index": index, "fields": candidate["fields"], "orientation": candidate["orientation"],
                          "base": selected[0]["base"], "core": float(means.mean()), "worst": float(means.min()),
                          "family_means": means.tolist(), "family_floor_fractions": (values >= .025).mean(axis=1).tolist(),
                          "banks_passed": sum(report["pass"] for report in selected),
                          "bootstrap_pass_fraction": float(passes.mean())})
    summaries.sort(key=lambda row: (row["bootstrap_pass_fraction"], row["core"]), reverse=True)
    (directory / "summary.json").write_text(json.dumps({"seconds": time.monotonic() - started, "private_bank_tested": False, "candidates": summaries}, indent=2))
    best = summaries[0]
    witness = {"schema_version": 1, "fields": best["fields"], "orientation": best["orientation"]}
    (search.OUTPUT / f"{args.tag}-witness.json").write_text(json.dumps(witness, indent=2) + "\n")
    print(json.dumps(summaries[:5], indent=2), flush=True)


if __name__ == "__main__":
    main()
