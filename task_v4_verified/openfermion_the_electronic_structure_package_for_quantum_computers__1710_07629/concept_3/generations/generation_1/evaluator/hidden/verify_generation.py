"""Private distribution, residual, restart, and site-covariance checks."""

from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "participant/input"))

import numpy as np

from distribution import draw_batch
from exact import label_instance as full_csr_label
from native_reference import label


def recompute_case(arguments):
    index, family, size, hopping, interaction, potential, expected = arguments
    os.sched_setaffinity(0, {160 + family})
    permutation = np.random.default_rng(302311 + index).permutation(size)
    result = label(hopping[np.ix_(permutation, permutation)], interaction[permutation],
                   potential[permutation], seed=981183 + index, tolerance=2e-12, ncv=32,
                   action_check=family == 0 and size == 12)
    error = float(np.max(np.abs(np.asarray(result["gaps"]) - expected)))
    independent_error = None
    if family == 0 and size == 10:
        independent = full_csr_label(hopping, interaction, potential)
        independent_error = float(np.max(np.abs(np.asarray(independent["gaps"]) - expected)))
    return {"validation_index": index, "family": family, "n_sites": size,
            "permuted_restart_gap_max_error": error, "full_csr_solver_gap_max_error": independent_error,
            "permutation": permutation.tolist(), "result": result}


def main():
    private = ROOT / "evaluator/hidden"
    settings = json.loads((ROOT / "evaluator/settings.json").read_text())
    assert settings == json.loads((ROOT / "participant/input/scoring.json").read_text())
    seeds = json.loads((private / "seeds.json").read_text())
    hashes = set()
    report = {"splits": {}, "recomputations": [], "passed": False}
    cases = []
    for split, count in (("train", settings["train_count"]),
                         ("validation", settings["validation_count"]),
                         ("test", settings["hidden_count"])):
        path = private / "test.npz" if split == "test" else ROOT / "participant/input" / (split + ".npz")
        with np.load(path, allow_pickle=False) as archive:
            data = dict(archive)
        with np.load(private / (split + "_source.npz"), allow_pickle=False) as archive:
            source = dict(archive)
        regenerated = draw_batch(count // 4, seeds[split])
        for key, values in regenerated.items():
            assert np.array_equal(values, data[key]), (split, key, "sampler replay")
        assert data["gaps"].shape == (count, 2)
        assert set(data) == {"hopping", "interaction", "potential", "n_sites", "family", "gaps"}
        assert np.all(np.isfinite(data["gaps"]))
        assert set(data["n_sites"]) == {10, 12}
        assert np.array_equal(np.bincount(data["family"]), np.repeat(count // 4, 4))
        energies = source["energies"]
        reconstructed = np.column_stack((energies[:, 1] + energies[:, 2] - 2 * energies[:, 0],
                                          energies[:, 3] - energies[:, 0]))
        assert np.array_equal(reconstructed, data["gaps"])
        assert np.max(source["residuals"]) <= 2e-8
        for index, size in enumerate(data["n_sites"]):
            hopping = data["hopping"][index]
            interaction = data["interaction"][index]
            potential = data["potential"][index]
            assert np.array_equal(hopping, hopping.T)
            assert np.all(np.diag(hopping) == 0)
            assert np.all(hopping[size:] == 0) and np.all(hopping[:, size:] == 0)
            assert np.all(interaction[size:] == 0) and np.all(potential[size:] == 0)
            assert abs(np.sum(potential[:size])) < 2e-12
            assert np.all(interaction[:size] > 0)
            fingerprint = hashlib.sha256(hopping.tobytes() + interaction.tobytes() + potential.tobytes()).hexdigest()
            assert fingerprint not in hashes, (split, index, "duplicate Hamiltonian")
            hashes.add(fingerprint)
        report["splits"][split] = {"count": count, "size_counts": {str(size): int(np.sum(data["n_sites"] == size))
             for size in (10, 12)}, "max_residual": float(np.max(source["residuals"])),
             "retry_count": int(np.sum(source["retry_count"])), "sampler_replay_exact": True,
             "source_gap_reconstruction_exact": True,
             "cpu_seconds": float(np.sum(source["cpu_seconds"]))}
        if split == "validation":
            for family in range(4):
                for size in (10, 12):
                    index = int(np.flatnonzero((data["family"] == family) & (data["n_sites"] == size))[0])
                    cases.append((index, family, size, data["hopping"][index, :size, :size],
                                  data["interaction"][index, :size], data["potential"][index, :size],
                                  data["gaps"][index]))
    with ProcessPoolExecutor(max_workers=4) as executor:
        report["recomputations"] = list(executor.map(recompute_case, cases))
    report["max_permuted_restart_gap_error"] = max(row["permuted_restart_gap_max_error"]
                                                 for row in report["recomputations"])
    assert report["max_permuted_restart_gap_error"] < 2e-8
    for row in report["recomputations"]:
        if row["full_csr_solver_gap_max_error"] is not None:
            assert row["full_csr_solver_gap_max_error"] < 2e-8
    report["distinct_hamiltonians"] = len(hashes)
    report["passed"] = True
    (private / "dataset_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "recomputations"}, indent=2))


if __name__ == "__main__":
    main()
