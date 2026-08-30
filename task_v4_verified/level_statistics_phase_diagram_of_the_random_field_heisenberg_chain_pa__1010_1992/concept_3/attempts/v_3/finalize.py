import search
import hashlib
import json
import numpy as np


def main():
    random = np.random.default_rng(397225)
    options = []
    for directory, witness_name in (("selection-validation", "selection-witness.json"), ("final-validation", "final-selection-witness.json")):
        summary_path = search.OUTPUT / directory / "summary.json"
        if not summary_path.exists():
            continue
        summary = json.loads(summary_path.read_text())
        witness_bytes = (search.OUTPUT / witness_name).read_bytes()
        assert hashlib.sha256(witness_bytes).hexdigest() == summary["witness_sha256"]
        banks = [json.loads((search.OUTPUT / directory / f"replication-{index}.json").read_text()) for index in range(summary["independent_bank_count"])]
        values = np.concatenate([np.array([[member["signed_difference"] for member in report["members"] if member["family"] == family["family"]] for family in report["families"]]) for report in banks], axis=1)
        means = values.mean(axis=1)
        indices = random.integers(values.shape[1], size=(20000, 4, 32))
        samples = values[np.arange(4)[None, :, None], indices]
        sampled_means = samples.mean(axis=2)
        passes = (sampled_means.mean(axis=1) >= .060) & (sampled_means.min(axis=1) >= .050) & ((samples >= .025).sum(axis=2).min(axis=1) >= 24)
        options.append({"validation_directory": directory, "witness_file": witness_name,
                        "independent_banks": len(banks), "independent_banks_passed": sum(report["pass"] for report in banks),
                        "pooled_core": float(means.mean()), "pooled_worst_family": float(means.min()),
                        "pooled_family_means": means.tolist(), "bootstrap_pass_fraction": float(passes.mean()),
                        "public": summary["reports"][0], "private_bank_tested": False,
                        "all_tested_constraints_valid": all(report["valid"] for report in summary["reports"]),
                        "minimum_tested_gap": min(report["minimum_gap"] for report in summary["reports"])})
    options.sort(key=lambda row: (row["bootstrap_pass_fraction"], row["pooled_core"]), reverse=True)
    chosen = options[0]
    witness_bytes = (search.OUTPUT / chosen["witness_file"]).read_bytes()
    (search.OUTPUT / "witness.json").write_bytes(witness_bytes)
    report = {"witness_sha256": hashlib.sha256(witness_bytes).hexdigest(), "chosen": chosen,
              "comparisons": options, "private_bank_tested": False, "maximum_search_workers": 8, "blas_threads_per_worker": 1}
    (search.OUTPUT / "submission_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
