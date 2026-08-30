"""Integrity, split independence, and post-generation convergence audit."""

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
from exact import label_instance


def audit_row(arguments):
    split, index, family, size, hopping, interaction, potential, labels = arguments
    rng = np.random.default_rng(19773 + index)
    permutation = rng.permutation(size)
    result = label_instance(hopping[np.ix_(permutation, permutation)],
                            interaction[permutation], potential[permutation],
                            seed=579191 + index, tolerance=4e-13)
    return {"split": split, "index": index, "family": family, "n_sites": size,
            "max_gap_error": float(np.max(abs(result["gaps"] - labels))),
            "max_residual": float(np.max(result["residuals"]))}


def main():
    os.sched_setaffinity(0, {162, 164, 166, 168})
    seeds = json.loads((ROOT / "evaluator/hidden/seeds.json").read_text())
    config_path = ROOT / "participant/input/scoring.json"
    settings = json.loads(config_path.read_text())
    assert settings == json.loads((ROOT / "evaluator/settings.json").read_text())
    generated = json.loads((ROOT / "evaluator/hidden/generation_report.json").read_text())
    assert generated["config_sha256"] == hashlib.sha256(config_path.read_bytes()).hexdigest()
    hashes = set()
    rows = []
    report = {"splits": {}, "duplicate_hamiltonians": 0, "config_unchanged": True}
    for split in ("train", "validation", "test"):
        source = ROOT / ("evaluator/hidden/test.npz" if split == "test" else f"participant/input/{split}.npz")
        with np.load(source, allow_pickle=False) as archive:
            data = dict(archive)
        assert generated["splits"][split]["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
        count = len(data["gaps"])
        regenerated = draw_batch(count // 4, seeds[split])
        assert set(data) == {"hopping", "interaction", "potential", "n_sites", "family", "gaps"}
        for key, value in regenerated.items():
            assert np.array_equal(value, data[key]), (split, key)
        assert data["hopping"].shape == (count, 10, 10)
        assert np.array_equal(data["hopping"], data["hopping"].transpose(0, 2, 1))
        assert np.all(np.diagonal(data["hopping"], axis1=1, axis2=2) == 0.0)
        assert np.max(abs(data["potential"].sum(axis=1))) < 1e-12
        for index, size in enumerate(data["n_sites"]):
            assert np.all(data["interaction"][index, :size] > 0.0)
            assert np.all(data["hopping"][index, size:, :] == 0.0)
            assert np.all(data["interaction"][index, size:] == 0.0)
            assert np.all(data["potential"][index, size:] == 0.0)
            digest = hashlib.sha256(b"".join(data[key][index].tobytes()
                for key in ("hopping", "interaction", "potential", "n_sites"))).hexdigest()
            if digest in hashes:
                report["duplicate_hamiltonians"] += 1
            hashes.add(digest)
        with np.load(ROOT / f"evaluator/hidden/{split}_source.npz", allow_pickle=False) as archive:
            energies = archive["energies"]
            reconstructed = np.column_stack([energies[:, 1] + energies[:, 2] - 2.0 * energies[:, 0],
                                               energies[:, 3] - energies[:, 0]])
            assert np.array_equal(reconstructed, data["gaps"])
            assert np.max(archive["residuals"]) < 2e-8
        groups = {}
        for family in range(4):
            assert np.sum(data["family"] == family) == count // 4
            for size in (8, 10):
                selected = np.flatnonzero((data["family"] == family) & (data["n_sites"] == size))
                groups[f"family{family}_n{size}"] = len(selected)
                index = int(selected[0])
                rows.append((split, index, family, size, data["hopping"][index, :size, :size],
                             data["interaction"][index, :size], data["potential"][index, :size],
                             data["gaps"][index]))
        report["splits"][split] = {"count": count, "groups": groups,
            "negative_spin_roundoff_preserved": int(np.sum(data["gaps"][:, 1] < 0.0)),
            "sampling_replayed_exactly": True}
    with ProcessPoolExecutor(max_workers=4) as executor:
        checks = list(executor.map(audit_row, rows))
    report["fresh_start_tighter_tolerance_permuted_checks"] = checks
    report["max_recomputed_gap_error"] = max(row["max_gap_error"] for row in checks)
    report["passed"] = report["duplicate_hamiltonians"] == 0 and report["max_recomputed_gap_error"] < 2e-8
    (ROOT / "evaluator/hidden/data_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
