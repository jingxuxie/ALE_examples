import argparse
import hashlib
import json
import os
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np

from audit import evaluate_dataset
from metrics import Benchmark, HERE, ROOT, REFERENCE, TARGETS

sys.path.insert(0, str(ROOT / "participant/workspace"))
from physics import FAMILIES, fisher_features, sample_parameters


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fresh-per-family", type=int, default=100)
    args = parser.parse_args()
    started = time.monotonic()
    benchmark = Benchmark()
    designs = {"reference": benchmark.reference_counts}
    for mode in ["single", "double"]:
        counts = np.array(json.loads((HERE / f"robust_{mode}.json").read_text())["batches"])
        benchmark.validate(counts)
        designs[mode] = counts
    with np.load(HERE / "broad_features.npz", allow_pickle=False) as data:
        broad_features = data["features"].copy()
        broad_families = data["families"].copy()
        broad_parameters = data["parameters"].copy()
        union = data["candidate_union"].copy()
    for counts in designs.values():
        assert set(np.flatnonzero(counts)).issubset(set(union))
    hidden = evaluate_dataset("robust_hidden", benchmark.features[:, union], benchmark.families,
                              benchmark.parameters, designs, union, benchmark)
    broad = evaluate_dataset("robust_broad", broad_features, broad_families, broad_parameters,
                             designs, union, benchmark)
    fresh = None
    if args.fresh_per_family:
        rng = np.random.default_rng(2174495931)
        parameters, families, feature_rows = [], [], []
        candidates = [benchmark.candidates[index] for index in union]
        for family in FAMILIES:
            for iteration in range(args.fresh_per_family):
                parameter = sample_parameters(rng, family)
                parameters.append(parameter)
                families.append(family)
                feature_rows.append(fisher_features(parameter, candidates))
            print(json.dumps(dict(event="new_holdout_features", family=family,
                                  seconds=time.monotonic() - started)), flush=True)
        features, families, parameters = np.array(feature_rows), np.array(families), np.array(parameters)
        np.savez_compressed(HERE / "fresh_features.npz", features=features, families=families,
                            parameters=parameters, candidate_union=union)
        fresh = evaluate_dataset("fresh", features, families, parameters, designs, union, benchmark)
    result = dict(targets=TARGETS, hidden=hidden, broad=broad, fresh=fresh,
                  broad_used_for_training_and_selection=True, fresh_used_for_training_or_selection=False,
                  fresh_seed=2174495931, fresh_per_family=args.fresh_per_family,
                  separate_designs=True, seconds=time.monotonic() - started,
                  reference_design_sha256=hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
                  original_reference_unchanged=True, fresh_agent_artifacts_read=False)
    (HERE / "verified_summary.json").write_text(json.dumps(result, indent=2) + "\n")
    for mode in ["single", "double"]:
        (HERE / f"{mode}_design.json").write_text(json.dumps({"batches": designs[mode].tolist()}) + "\n")
        (HERE / f"{mode}_score.json").write_text(json.dumps(benchmark.evaluate(designs[mode], direct=True), indent=2) + "\n")
    (HERE / "design.json").write_bytes((HERE / "double_design.json").read_bytes())
    (HERE / "score.json").write_bytes((HERE / "double_score.json").read_bytes())
    print(json.dumps(dict(event="verified", seconds=result["seconds"],
                          single_hidden=hidden["single"]["single"]["passed"], single_broad=broad["single"]["single"]["passed"],
                          double_hidden=hidden["double"]["double"]["passed"], double_broad=broad["double"]["double"]["passed"])), flush=True)


if __name__ == "__main__":
    main()
