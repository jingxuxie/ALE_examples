import argparse
import hashlib
import json
import os
import threading
import time
from pathlib import Path
import sys

import numpy as np
from scipy.linalg import eig_banded

from reference import ROOT, TASK, energy_gradient, write_json

sys.path.insert(0, str(TASK / "authoring"))
from isolated import run_submission


SUBMISSION = TASK / "pilots/activation/attempt"
PARTICIPANT = TASK / "pilots/activation/participant"
EXPECTED_HASH = "252500c16f8aa286173b42139f0cc1686627788dcde93ad46f081b89771e4656"


def full_spectrum(case, spins):
    count = len(spins)
    axes = np.eye(3)[np.argmin(np.abs(spins), axis=1)]
    first = np.cross(spins, axes)
    first /= np.linalg.norm(first, axis=1)[:, None]
    basis = np.stack((first, np.cross(spins, first)), axis=2)
    _, gradient = energy_gradient(case, spins)
    diagonal = -2 * np.einsum("nca,ncd,ndb->nab", basis, np.asarray(case["anisotropy_meV"]), basis)
    diagonal -= np.sum(gradient * spins, axis=1)[:, None, None] * np.eye(2)
    offdiagonal = -np.asarray(case["exchange_meV"])[:, None, None] * np.einsum("nca,ncb->nab", basis[:-1], basis[1:])
    band = np.zeros((4, 2 * count))
    for site in range(count):
        for row in range(2):
            for column in range(row, 2):
                band[3 + row - column, 2 * site + column] = diagonal[site, row, column]
    for bond in range(count - 1):
        for row in range(2):
            for column in range(2):
                band[1 + row - column, 2 * bond + 2 + column] = offdiagonal[bond, row, column]
    return eig_banded(band, lower=False, eigvals_only=True, check_finite=False)


def monitor_descendants(stop, samples, case_path):
    while not stop.wait(0.05):
        pending = [os.getpid()]
        visited = set()
        while pending:
            process = pending.pop()
            if process in visited:
                continue
            visited.add(process)
            try:
                pending.extend(int(value) for value in Path(f"/proc/{process}/task/{process}/children").read_text().split())
                command = Path(f"/proc/{process}/cmdline").read_bytes().split(b"\0")
                if not any(str(case_path).encode() == argument for argument in command) or not any(argument.endswith(b"/solve.py") for argument in command):
                    continue
                if not command or b"python" not in command[0]:
                    continue
                fields = {}
                for line in Path(f"/proc/{process}/status").read_text().splitlines():
                    if line.startswith(("VmHWM:", "VmPeak:")):
                        name, value, units = line.split()
                        fields[name[:-1]] = int(value)
                samples["peak_solver_rss_kib_sampled"] = max(samples.get("peak_solver_rss_kib_sampled", 0), fields.get("VmHWM", 0))
                samples["peak_solver_virtual_kib_sampled"] = max(samples.get("peak_solver_virtual_kib_sampled", 0), fields.get("VmPeak", 0))
                samples["sample_count"] = samples.get("sample_count", 0) + 1
            except (FileNotFoundError, ProcessLookupError, PermissionError):
                pass


def assess(case, output, reference_path):
    with np.load(output, allow_pickle=False) as archive:
        result = {name: np.asarray(archive[name], dtype=float) for name in archive.files}
    with np.load(reference_path, allow_pickle=False) as archive:
        reference = {name: np.asarray(archive[name], dtype=float) for name in archive.files}
    spins = result["saddle"]
    if spins.shape != (case["n_spins"], 3) or not all(np.all(np.isfinite(value)) for value in result.values()):
        raise ValueError("invalid shape/nonfinite output")
    minimum = np.asarray(case["minimum_a"])
    terms, gradient = energy_gradient(case, spins)
    projected = gradient - np.sum(gradient * spins, axis=1)[:, None] * spins
    true_barrier = float(np.sum(terms - energy_gradient(case, minimum)[0]))
    actual = full_spectrum(case, spins)
    minimum_values = full_spectrum(case, minimum)
    log_factor = None
    if actual[0] < 0 and actual[1] > 0 and minimum_values[0] > 0:
        log_factor = float(0.5 * (np.log(minimum_values).sum() - np.log(actual[1:]).sum()))
    return {"unit_norm_max_error": float(np.max(np.abs(np.linalg.norm(spins, axis=1) - 1))),
            "residual_meV": float(np.max(np.linalg.norm(projected, axis=1))),
            "negative_modes": int(np.sum(actual < -1e-6)), "zero_modes": int(np.sum(np.abs(actual) <= 1e-6)),
            "true_barrier_meV": true_barrier, "reference_barrier_meV": float(reference["barrier_meV"]),
            "barrier_absolute_error_meV": abs(true_barrier - float(reference["barrier_meV"])),
            "reported_barrier_error_meV": abs(float(result["barrier_meV"]) - true_barrier),
            "reported_minimum_spectrum_max_error_meV": float(np.max(np.abs(result["eigenvalues_min_meV"] - minimum_values))),
            "reported_saddle_spectrum_max_error_meV": float(np.max(np.abs(result["eigenvalues_saddle_meV"] - actual))),
            "true_saddle_spectrum_vs_reference_max_error_meV": float(np.max(np.abs(actual - reference["eigenvalues_saddle_meV"]))),
            "true_log_omega0": log_factor, "reference_log_omega0": float(reference["log_omega0"]),
            "reported_log_omega0_error": None if log_factor is None else abs(float(result["log_omega0"]) - log_factor)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", type=int, nargs="+", default=[512, 2048])
    arguments = parser.parse_args()
    digest = hashlib.sha256((SUBMISSION / "solve.py").read_bytes()).hexdigest()
    if digest != EXPECTED_HASH:
        raise RuntimeError("immutable submission hash changed")
    for count in arguments.sizes:
        directory = ROOT / f"N{count}"
        validation = json.loads((directory / "validation.json").read_text())
        if not validation["validated"]:
            raise RuntimeError("reference must be validated first")
        case_path = (directory / "case.json").resolve()
        output = directory / "submission_run/output.npz"
        output.parent.mkdir(exist_ok=True)
        if output.exists():
            raise RuntimeError(f"refusing to overwrite an existing submission output: {output}")
        samples = {}
        stop = threading.Event()
        monitor = threading.Thread(target=monitor_descendants, args=(stop, samples, case_path), daemon=True)
        monitor.start()
        print(f"RUN immutable submission N={count}, timeout=90s, address-space=2GiB", flush=True)
        try:
            metrics = run_submission(SUBMISSION, case_path, output, PARTICIPANT, timeout=90, memory_gib=2.0)
        finally:
            stop.set()
            monitor.join(timeout=2)
        metrics.update(samples)
        report = {"n_spins": count, "immutable_submission_sha256": digest, "resources": metrics,
                  "reference_wall_seconds": validation["reference_wall_seconds"], "reference_sparse_htst_seconds": validation["stage_seconds"]["native_sparse_htst"],
                  "core_accuracy": None, "core_accuracy_status": "unavailable: no completed output"}
        if output.exists():
            try:
                report["core_accuracy"] = assess(json.loads(case_path.read_text()), output, directory / "reference.npz")
                report["core_accuracy_status"] = "independently measured from completed output"
            except Exception as error:
                report["core_accuracy_status"] = f"invalid or incomplete output: {error}"
        write_json(directory / "submission_result.json", report)
        print(json.dumps(report, indent=2), flush=True)
        if hashlib.sha256((SUBMISSION / "solve.py").read_bytes()).hexdigest() != digest:
            raise RuntimeError("submission changed during probe")


if __name__ == "__main__":
    main()
