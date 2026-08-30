"""Builder-only reproducible labels; private test entropy is never published."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import secrets
import sys
import time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "participant/input"))

import numpy as np

from distribution import draw_batch
from native_reference import label as label_instance


def initialize_worker():
    allowed = sorted(set(os.sched_getaffinity(0)) - {188, 380})
    identity = multiprocessing.current_process()._identity[0]
    os.sched_setaffinity(0, {allowed[(200 + identity * 2) % len(allowed)]})


def label_row(arguments):
    try:
        result = label_instance(*arguments)
        result["retry_count"] = 0
    except RuntimeError:
        result = label_instance(*arguments, tolerance=2e-11, ncv=32)
        result["retry_count"] = 1
    result["seconds"] = result["wall_seconds"]
    if result["gaps"][1] < -2e-8:
        raise RuntimeError("Spin-sector ordering failed")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=32)
    arguments = parser.parse_args()
    private = ROOT / "evaluator/hidden"
    config = json.loads((ROOT / "participant/input/scoring.json").read_text())
    seeds_path = private / "seeds.json"
    if seeds_path.exists():
        seeds = json.loads(seeds_path.read_text())
    else:
        seeds = {"train": 84620915, "validation": 91002031, "test": secrets.randbits(128)}
        seeds_path.write_text(json.dumps(seeds, indent=2) + "\n")
    report = {"config_sha256": hashlib.sha256((ROOT / "participant/input/scoring.json").read_bytes()).hexdigest(),
              "splits": {}}
    for split, count in (("train", config["train_count"]), ("validation", config["validation_count"]),
                         ("test", config["hidden_count"])):
        destination = private if split == "test" else ROOT / "participant/input"
        inputs = draw_batch(count // 4, seeds[split])
        output = destination / (split + ".npz")
        residual_output = private / (split + "_source.npz")
        start = time.perf_counter()
        rows = [(inputs["hopping"][index, :size, :size], inputs["interaction"][index, :size],
                 inputs["potential"][index, :size]) for index, size in enumerate(inputs["n_sites"])]
        with ProcessPoolExecutor(max_workers=arguments.workers, initializer=initialize_worker) as executor:
            labels = []
            for index, result in enumerate(executor.map(label_row, rows, chunksize=1)):
                labels.append(result)
                if (index + 1) % 32 == 0:
                    print(split, index + 1, "elapsed", round(time.perf_counter() - start, 2), flush=True)
        gaps = np.stack([row["gaps"] for row in labels])
        energies = np.stack([row["energies"] for row in labels])
        residuals = np.stack([row["residuals"] for row in labels])
        np.savez_compressed(output, **inputs, gaps=gaps)
        np.savez_compressed(residual_output, energies=energies, residuals=residuals,
                            wall_seconds=[row["seconds"] for row in labels],
                            cpu_seconds=[row["cpu_seconds"] for row in labels],
                            retry_count=[row["retry_count"] for row in labels],
                            matvec_counts=[[sector["matvec_count"] for sector in row["sectors"]] for row in labels])
        report["splits"][split] = {"count": count,
            "n10": int(np.sum(inputs["n_sites"] == 10)), "n12": int(np.sum(inputs["n_sites"] == 12)),
            "max_residual": float(np.max(residuals)), "build_wall_seconds": time.perf_counter() - start,
            "label_cpu_seconds": sum(row["cpu_seconds"] for row in labels),
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "gap_mean": gaps.mean(axis=0).tolist(), "gap_std": gaps.std(axis=0).tolist(),
            "gap_min": gaps.min(axis=0).tolist(), "gap_max": gaps.max(axis=0).tolist()}
        (private / "generation_report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(split, report["splits"][split], flush=True)
    example_inputs = draw_batch(1, 731491)
    np.savez_compressed(ROOT / "participant/input/example_inputs.npz", **example_inputs)


if __name__ == "__main__":
    main()
