"""Eight new n12 pilot cases, eight existing n10 controls, no task regeneration."""

from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import resource
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"
PILOT = Path(__file__).resolve().parent
ROOT = PILOT.parents[1]
sys.path.insert(0, str(PILOT / "reference"))

import numpy as np

from distribution import draw_batch
from exact import label_instance, sector_matrix
from native_reference import label, native_operator


def initialize_worker():
    allowed = sorted(os.sched_getaffinity(0))
    identity = multiprocessing.current_process()._identity[0]
    selected = allowed[(242 + 2 * identity) % len(allowed)]
    os.sched_setaffinity(0, {selected})
    memory = 6 * 1024 ** 3
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    resource.setrlimit(resource.RLIMIT_CPU, (600, 600))


def run_reference(arguments):
    size, index, family, hopping, interaction, potential, known = arguments
    result = label(hopping, interaction, potential)
    result.update(n_sites=size, index=index, family=family,
                  peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  affinity=sorted(os.sched_getaffinity(0)))
    if known is not None:
        result["existing_source_gap_error"] = float(np.max(abs(np.asarray(result["gaps"]) - known)))
    return result


def main():
    inputs12 = draw_batch(2, 202608281117, n_sites=12)
    with np.load(ROOT / "participant/input/validation.npz", allow_pickle=False) as archive:
        existing = dict(archive)
    selected = np.concatenate([np.flatnonzero((existing["family"] == family)
                                               & (existing["n_sites"] == 10))[:2] for family in range(4)])
    inputs10 = {key: value[selected] for key, value in existing.items() if key != "gaps"}
    np.savez_compressed(PILOT / "inputs_12.npz", **inputs12)
    np.savez_compressed(PILOT / "inputs_10.npz", **inputs10)
    specification = {"seed_12": 202608281117, "new_cases": 8, "family_counts_12": [2, 2, 2, 2],
        "existing_validation_indices_10": selected.tolist(),
        "distribution_source_sha256": hashlib.sha256((PILOT / "reference/distribution.py").read_bytes()).hexdigest(),
        "distribution_change": "only fixed n_sites=12; all continuous distributions and families unchanged",
        "proposed_mixture_only": "iid equal-probability n10/n12, not generated as a new task"}
    (PILOT / "cases.json").write_text(json.dumps(specification, indent=2) + "\n")
    rng = np.random.default_rng(74193)
    tiny_hopping = rng.uniform(0.1, 1.0, (4, 4))
    tiny_hopping = (tiny_hopping + tiny_hopping.T) / 2.0
    np.fill_diagonal(tiny_hopping, 0.0)
    tiny_interaction = rng.uniform(2.0, 8.0, 4)
    tiny_potential = rng.uniform(-1.0, 1.0, 4)
    errors = []
    for up, down in ((2, 2), (2, 1), (3, 2), (3, 1), (0, 2)):
        matrix = sector_matrix(tiny_hopping, tiny_interaction, tiny_potential, up, down)
        operator, _ = native_operator(tiny_hopping, tiny_interaction, tiny_potential, up, down)
        vector = rng.normal(size=matrix.shape[0])
        errors.append(float(np.max(abs(matrix @ vector - operator @ vector))))
    assert max(errors) < 1e-11
    (PILOT / "native_operator_check.json").write_text(json.dumps({"max_action_error": max(errors),
        "sectors_checked": 5, "passed": True}, indent=2) + "\n")
    jobs = []
    for size, data in ((10, inputs10), (12, inputs12)):
        for index in range(8):
            jobs.append((size, index, int(data["family"][index]), data["hopping"][index],
                data["interaction"][index], data["potential"][index],
                existing["gaps"][selected[index]] if size == 10 else None))
    started = time.perf_counter()
    results = []
    with ProcessPoolExecutor(max_workers=4, initializer=initialize_worker) as executor:
        for result in executor.map(run_reference, jobs, chunksize=1):
            results.append(result)
            (PILOT / "reference_progress.json").write_text(json.dumps(results, indent=2) + "\n")
            print(json.dumps({key: result[key] for key in ("n_sites", "index", "family", "gaps", "cpu_seconds", "peak_rss_kib")}), flush=True)
    report = {"method": "source spin bases and Hamiltonian; double native tensor matvec; scipy eigsh random start",
              "tol": 2e-11, "residual_acceptance": 2e-8, "ncv": 32,
              "workers": 4, "elapsed_wall_seconds": time.perf_counter() - started, "rows": results}
    for size in (10, 12):
        size_results = [row for row in results if row["n_sites"] == size]
        np.savez_compressed(PILOT / f"labels_{size}.npz",
            gaps=[row["gaps"] for row in size_results], energies=[row["energies"] for row in size_results],
            residuals=[row["residuals"] for row in size_results])
    assert max(row.get("existing_source_gap_error", 0.0) for row in results) < 2e-8
    report["passed"] = True
    (PILOT / "reference_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("REFERENCE_COMPLETE", report["elapsed_wall_seconds"], flush=True)


if __name__ == "__main__":
    main()
