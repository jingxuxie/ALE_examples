"""Validate inversion against independent public-generator Hamiltonians."""

import itertools
import json
import time
from pathlib import Path

import numpy as np

from reconstruct import DEFAULT_ASSETS, load_generator, metrics, reconstruct


def main():
    generator = load_generator(DEFAULT_ASSETS)
    rng = np.random.default_rng(202608280746)
    started = time.perf_counter()
    records = []
    for family, n_pairs, n_virtual, replicate in itertools.product(
            range(6), (2, 3), (6, 7, 8, 9), range(2)):
        model, features, truth, rejected = generator.accepted_sample(
            rng, n_pairs, n_virtual, family
        )
        prediction, diagnostics, inferred = reconstruct(features, generator)
        hopping_error = float(np.max(np.abs(model.hopping - inferred.hopping)))
        records.append({
            "family": family, "n_pairs": n_pairs, "n_virtual": n_virtual,
            "replicate": replicate, "rejections": rejected,
            "tail": truth["tail"], "prediction": prediction,
            "maximum_transfer_error": hopping_error,
            "triple_max_residual": diagnostics["triple_max_residual"],
        })
        if len(records) % 16 == 0:
            print(f"Independent validation: {len(records)}/96", flush=True)
    target = np.asarray([record["tail"] for record in records])
    predictions = np.asarray([record["prediction"] for record in records])
    families = np.asarray([record["family"] for record in records])
    report = {
        "rng_seed": 202608280746,
        "seed_role": "independent participant samples, not release seeds",
        "samples": len(records),
        "runtime_seconds": time.perf_counter() - started,
        "metrics": metrics(target, predictions, families),
        "maximum_transfer_error": max(record["maximum_transfer_error"] for record in records),
        "records": records,
    }
    assert report["metrics"]["maximum_absolute_error"] < 1e-9
    assert report["maximum_transfer_error"] < 1e-9
    (Path(__file__).resolve().parent / "synthetic_validation_report.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps({key: value for key, value in report.items() if key != "records"}), flush=True)


if __name__ == "__main__":
    main()
