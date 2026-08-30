import argparse
import json
import time

import search
import numpy as np


def evaluate_file(name, count, seed, complete=False):
    candidate = search.model.load_witness(search.ROOT / name)
    pools = search.assay.training_uniforms(seed=seed, samples=count)
    started = time.monotonic()
    nominal = search.model.compute(candidate, complete=True)
    report = dict(file=name, nominal=search.model.score(nominal),
                  nominal_metrics={key: value for key, value in nominal.items() if not isinstance(value, dict)},
                  families={})
    for family, uniforms in pools.items():
        cases = []
        for row in uniforms:
            coefficients = search.assay.perturb(candidate, row, family)
            if complete:
                case = search.assay.evaluate_case(coefficients)
            else:
                metrics = search.model.compute_coefficients(coefficients, complete=False)
                case = search.model.score(metrics)
                case["metrics"] = {key: metrics[key] for key in search.assay.METRIC_FIELDS}
            cases.append(case)
        report["families"][family] = dict(successes=sum(case["passed"] for case in cases), count=count,
                                          metric_ranges={key: [min(case["metrics"][key] for case in cases), max(case["metrics"][key] for case in cases)]
                                                         for key in search.assay.METRIC_FIELDS},
                                          failure_counts={key: sum(not case["witness_checks"][key] for case in cases)
                                                          for key in cases[0]["witness_checks"]})
    report["seconds"] = time.monotonic() - started
    (search.ROOT / (name.removesuffix(".json") + f"_validation_{seed}_{count}.json")).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+")
    parser.add_argument("--count", type=int, default=128)
    parser.add_argument("--seed", type=int, default=991738)
    parser.add_argument("--complete", action="store_true")
    arguments = parser.parse_args()
    for name in arguments.files:
        evaluate_file(name, arguments.count, arguments.seed, arguments.complete)
