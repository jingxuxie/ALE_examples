import os
import sys

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import hashlib
import json
import resource
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
CONCEPT = ROOT.parents[2]
TARGETS = ("odd_gap", "even_gap", "odd_spacing")


def digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024**2), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def target_values(record):
    return np.array([record["prediction"]["targets"][target] for target in TARGETS])


def main():
    resource.setrlimit(resource.RLIMIT_AS, (8 * 1024**3, 8 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (120, 121))
    wall_start, cpu_start = time.monotonic(), time.process_time()
    report = json.loads((ROOT / "FINAL_REPORT.json").read_text())
    plan = json.loads((ROOT / "plan.json").read_text())
    assert report["accepted"] and not report["ratchet_admitted"]
    protected = plan["protected_files"]
    changed = [name for name, checksum in protected.items()
               if not (CONCEPT / name).is_file() or digest(CONCEPT / name) != checksum]
    assert not changed, changed
    stages = report["new_stages"]
    assert [(stage["diagnostic"]["count"], stage["diagnostic"]["fock"],
             stage["diagnostic"]["frequency"]) for stage in stages] == [
                 (14, 80, 2.0), (14, 160, 2.0), (14, 160, 2.34)]
    state_hashes = {stage["eigenvectors"]: digest(ROOT / stage["eigenvectors"])
                    for stage in stages}
    assert all(state_hashes[stage["eigenvectors"]] == stage["eigenvectors_sha256"]
               for stage in stages)
    history = report["inherited_history"][-2:] + stages[:1]
    cutoff_changes = [np.abs(np.log(target_values(later) / target_values(earlier)))
                      for earlier, later in zip(history, history[1:])]
    basis_changes = [np.abs(np.log(target_values(later) / target_values(earlier)))
                     for earlier, later in zip(stages, stages[1:])]
    assert max(np.max(change) for change in cutoff_changes + basis_changes) <= 2e-5
    for stage in history + stages[1:]:
        assert np.min(target_values(stage)) >= 1e-6
        assert np.max(stage["diagnostic"]["residuals_dimensionless"]) <= 1e-10
        assert max(stage["residual_roundoff_gap_ratio"]) <= 2e-6
    case = report["case"]
    scale = (case["lambda"] / 6) ** (1 / 3)
    assert scale == 1.0
    stage = stages[1]
    with np.load(ROOT / stage["eigenvectors"], allow_pickle=False) as saved:
        count = int(saved["retained_count"])
        levels = saved["onsite_levels"]
        positions = saved["onsite_positions"]
        vectors_by_sector = [saved["even_vectors"], saved["odd_vectors"]]
    sites = case["sites"]
    shape = (count,) * sites
    dimension = count**sites
    diagonal = np.zeros(shape)
    for site in range(sites):
        local_shape = [1] * sites
        local_shape[site] = count
        diagonal += (levels[site] - levels[site, 0]).reshape(local_shape)
    integers = np.arange(dimension)
    working = integers.copy()
    parity = np.zeros(dimension, dtype=np.int8)
    for site in range(sites):
        parity ^= (working % count % 2).astype(np.int8)
        working //= count
    del working
    energies, residuals, orthogonality = [], [], []
    for sector, vectors in enumerate(vectors_by_sector):
        assert vectors.shape == (dimension // 2, 2) and np.all(np.isfinite(vectors))
        orthogonality.append(float(np.max(np.abs(vectors.T @ vectors - np.eye(2)))))
        indices = integers[parity == sector]
        sector_energies, sector_residuals = [], []
        for state in range(2):
            vector = vectors[:, state]
            tensor = np.zeros(dimension)
            tensor[indices] = vector
            tensor = tensor.reshape(shape)
            output = diagonal * tensor
            for bond, coupling in enumerate(case["kappa_by_bond"]):
                product = np.moveaxis(np.tensordot(positions[bond], tensor, axes=(1, bond)), 0, bond)
                product = np.moveaxis(np.tensordot(positions[bond + 1], product,
                                                 axes=(1, bond + 1)), 0, bond + 1)
                output -= coupling * product
            applied = output.ravel()[indices]
            energy = np.sum(applied.astype(np.longdouble) * vector.astype(np.longdouble))
            sector_energies.append(energy)
            sector_residuals.append(float(np.linalg.norm(applied - float(energy) * vector)))
        energies.append(sector_energies)
        residuals.append(sector_residuals)
    even, odd = energies
    recomputed = np.array([odd[0] - even[0], even[1] - even[0], odd[1] - odd[0]], dtype=float)
    gap_errors = np.abs(np.log(recomputed / target_values(stage)))
    assert max(orthogonality) <= 1e-10
    assert np.max(residuals) <= 1e-10 and np.max(gap_errors) <= 2e-5
    summary = {
        "passed": True,
        "scope": "Post-run saved-artifact and residual audit; no new eigensolve or hardness search.",
        "unchanged_protected_files": len(protected),
        "prior_budgeted_run_preserved": True,
        "state_hashes": state_hashes,
        "cutoff_log_changes": [change.tolist() for change in cutoff_changes],
        "basis_log_changes": [change.tolist() for change in basis_changes],
        "saved_label_eigenvector_orthogonality_errors": orthogonality,
        "recomputed_label_residuals": residuals,
        "recomputed_label_targets": dict(zip(TARGETS, recomputed.tolist())),
        "recomputed_target_log_errors": gap_errors.tolist(),
        "cpu_seconds": time.process_time() - cpu_start,
        "wall_seconds": time.monotonic() - wall_start,
        "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
        "official_batch_score": False,
        "ratchet_admitted": False,
    }
    (ROOT / "evidence_audit.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
