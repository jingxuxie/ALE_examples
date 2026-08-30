import argparse
import json
import os
import resource
import sys
import time
from pathlib import Path

import numpy as np

import model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["fit", "predict", "probe"])
    parser.add_argument("--device", type=int)
    arguments = parser.parse_args()
    model.INPUT = Path("/input")
    model.ROOT = Path("/output")
    started = time.monotonic()
    if arguments.mode == "probe":
        print(json.dumps({"input_files": sorted(path.name for path in model.INPUT.iterdir()),
                          "output_files": sorted(path.name for path in model.ROOT.iterdir()),
                          "host_repository_visible": Path("/srv/home/xuandong/mnt/jingxu/ALE").exists(),
                          "private_directory_visible": Path("/private").exists(),
                          "affinity": sorted(os.sched_getaffinity(0)),
                          "address_space_limit": resource.getrlimit(resource.RLIMIT_AS)}))
        return
    if arguments.mode == "fit":
        import fit
        sys.argv = ["fit.py", "--device", str(arguments.device), "--include-development"]
        fit.main()
        artifact = f"resource_device_{arguments.device}.json"
    else:
        queries = model.load("queries")
        predictions = np.empty(len(queries["ids"]))
        for device in range(4):
            parameters = np.load(model.ROOT / f"fit_d{device}_all.npz", allow_pickle=False)["params"]
            selected = queries["device"] == device
            predictions[selected] = model.predict(parameters, model.select(queries, selected))
        (model.ROOT / "predictions.json").write_text(json.dumps({"ids": queries["ids"].tolist(), "p1": predictions.tolist()}, allow_nan=False))
        artifact = "resource_prediction.json"
    usage = resource.getrusage(resource.RUSAGE_SELF)
    record = {"elapsed_seconds": time.monotonic() - started, "user_cpu_seconds": usage.ru_utime,
              "system_cpu_seconds": usage.ru_stime, "max_rss_kib": usage.ru_maxrss,
              "voluntary_context_switches": usage.ru_nvcsw,
              "involuntary_context_switches": usage.ru_nivcsw,
              "cpu_affinity": sorted(os.sched_getaffinity(0)),
              "address_space_limit_bytes": resource.getrlimit(resource.RLIMIT_AS)[0],
              "openmp_threads": os.environ.get("OMP_NUM_THREADS"),
              "learner_received_true_parameters_or_probabilities": False}
    (model.ROOT / artifact).write_text(json.dumps(record, indent=2) + "\n")
    print("RESOURCE", json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
