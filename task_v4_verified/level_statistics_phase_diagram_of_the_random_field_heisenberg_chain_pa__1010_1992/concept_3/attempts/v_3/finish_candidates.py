import search
import concurrent.futures
import hashlib
import json
import secrets
import time
import numpy as np
from select_candidate import measure


def main():
    started = time.monotonic()
    candidates = json.loads((search.OUTPUT / "local-widths.json").read_text())[:3]
    candidates.append(json.loads((search.OUTPUT / "witness.json").read_text()))
    directory = search.OUTPUT / "last-check"
    directory.mkdir(exist_ok=True)
    protocols = [search.bank("last-check", seed_hex=secrets.token_hex(32)) for repeat in range(8)]
    protocols.append(json.loads((search.ASSETS / "input/protocol.json").read_text()))
    for index, protocol in enumerate(protocols):
        (directory / f"protocol-{index}.json").write_text(json.dumps(protocol, indent=2))
    (directory / "candidates.json").write_text(json.dumps(candidates, indent=2))
    tasks = [(candidate, protocol, candidate_index, bank_index) for candidate_index, candidate in enumerate(candidates) for bank_index, protocol in enumerate(protocols)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        reports = list(executor.map(measure, tasks))
    (directory / "reports.json").write_text(json.dumps(reports, indent=2))
    random = np.random.default_rng(712026)
    summaries = []
    for index, candidate in enumerate(candidates):
        selected = [report for report in reports if report["candidate"] == index]
        if not all(report["valid"] for report in selected):
            continue
        banks = [report for report in selected if report["bank"] < 8]
        public = next(report for report in selected if report["bank"] == 8)
        values = np.concatenate([report["values"] for report in banks], axis=1)
        means = values.mean(axis=1)
        indices = random.integers(values.shape[1], size=(20000, 4, 32))
        samples = values[np.arange(4)[None, :, None], indices]
        sampled_means = samples.mean(axis=2)
        passes = (sampled_means.mean(axis=1) >= .060) & (sampled_means.min(axis=1) >= .050) & ((samples >= .025).sum(axis=2).min(axis=1) >= 24)
        summaries.append({"index": index, "fields": candidate["fields"], "orientation": candidate["orientation"],
                          "core": float(means.mean()), "worst": float(means.min()), "family_means": means.tolist(),
                          "independent_banks_passed": sum(report["pass"] for report in banks), "independent_banks": len(banks),
                          "bootstrap_pass_fraction": float(passes.mean()), "public": {key: value for key, value in public.items() if key != "values"},
                          "all_tested_constraints_valid": True, "minimum_tested_gap": min(report["minimum_gap"] for report in selected)})
    summaries.sort(key=lambda row: (row["bootstrap_pass_fraction"], row["core"]), reverse=True)
    chosen = summaries[0]
    witness = {"schema_version": 1, "fields": chosen["fields"], "orientation": chosen["orientation"]}
    witness_bytes = (json.dumps(witness, indent=2) + "\n").encode()
    (search.OUTPUT / "witness.json").write_bytes(witness_bytes)
    result = {"witness_sha256": hashlib.sha256(witness_bytes).hexdigest(), "chosen": chosen,
              "comparisons": summaries, "validation_directory": "last-check", "private_bank_tested": False,
              "maximum_search_workers": 8, "blas_threads_per_worker": 1, "seconds": time.monotonic() - started}
    (directory / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    (search.OUTPUT / "submission_report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
