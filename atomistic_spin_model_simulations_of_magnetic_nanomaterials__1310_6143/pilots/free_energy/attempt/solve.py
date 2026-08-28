import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
sys.dont_write_bytecode = True

import numpy as np
from reweight import reweight


def write_model(case, angles, path):
    with open(path, "w") as stream:
        stream.write(f"{case['n_spins']} {len(case['bonds'])} {case['temperature']:.17g} "
                     f"{case['seed']} {len(angles)}\n")
        stream.write(" ".join(format(float(value), ".17g") for value in angles) + "\n")
        for row in case["onsite"]:
            stream.write(" ".join(format(value, ".17g") for value in row) + "\n")
        for first, second, exchange, axial in case["bonds"]:
            stream.write(f"{first} {second} {exchange:.17g} {axial:.17g}\n")


def summarize(raw):
    node_count = int(raw[:, 0].max()) + 1
    means, errors, angles = [], [], []
    for node in range(node_count):
        records = raw[raw[:, 0] == node]
        blocks = records[:, 4]
        means.append(np.average(blocks, weights=records[:, 3]))
        angles.append(records[0, 1])
        estimates = []
        for grouping in (1, 2, 4, 8):
            grouped = blocks.reshape(-1, grouping).mean(axis=1)
            estimates.append(np.std(grouped, ddof=1) / math.sqrt(len(grouped)))
        errors.append(max(estimates))
    return np.asarray(angles), np.asarray(means), np.maximum(errors, 1e-10)


def integrate(angles, torque, error, requested):
    harmonic_count = min(7, len(angles) - 1)
    harmonics = np.arange(1, harmonic_count + 1, dtype=float)
    design = np.sin(2 * angles[:, None] * harmonics)
    weighted = design / error[:, None]
    covariance = np.linalg.inv(weighted.T @ weighted)
    coefficients = covariance @ (weighted.T @ (torque / error))
    coefficient_error = np.sqrt(np.diag(covariance))
    retained = 2
    for index in range(2, harmonic_count):
        if abs(coefficients[index]) > 2.5 * coefficient_error[index]:
            retained = index + 1
    harmonics = harmonics[:retained]
    design = design[:, :retained]
    weighted = design / error[:, None]
    covariance = np.linalg.inv(weighted.T @ weighted)
    coefficients = covariance @ (weighted.T @ (torque / error))
    requested = np.asarray(requested)
    torque_design = np.sin(2 * requested[:, None] * harmonics)
    free_design = (np.cos(2 * requested[:, None] * harmonics) - 1) / (2 * harmonics)
    predicted_torque = torque_design @ coefficients
    predicted_free = free_design @ coefficients
    predicted_torque[np.abs(np.sin(2 * requested)) < 1e-14] = 0.0
    predicted_free[0] = 0.0
    torque_sem = np.sqrt(np.maximum(0, np.einsum("ij,jk,ik->i", torque_design, covariance, torque_design)))
    free_sem = np.sqrt(np.maximum(0, np.einsum("ij,jk,ik->i", free_design, covariance, free_design)))
    return {"torque": predicted_torque.tolist(), "free_energy": predicted_free.tolist(),
            "torque_sem": torque_sem.tolist(), "free_energy_sem": free_sem.tolist(),
            "method": "directional-exchange-MC/torque-integration",
            "harmonics": retained, "coefficients": coefficients.tolist(),
            "sample_angles": angles.tolist(), "sample_torque": torque.tolist(),
            "sample_sem": error.tolist()}


def main():
    start = time.monotonic()
    with open(sys.argv[1]) as stream:
        case = json.load(stream)
    output = Path(sys.argv[2]).resolve()
    isotropic = all(row[0] == row[1] == row[2] and not any(row[3:]) for row in case["onsite"])
    if isotropic and all(row[3] == 0 for row in case["bonds"]):
        zeros = [0.0] * len(case["angles"])
        with open(output, "w") as stream:
            json.dump({"version": 1, "case_id": case["case_id"], "torque": zeros,
                       "free_energy": zeros, "torque_sem": zeros, "free_energy_sem": zeros}, stream)
        return
    budget = float(os.environ.get("SPIN_SECONDS", "550"))
    nodes = int(os.environ.get("SPIN_NODES", "15"))
    angles = np.arange(1, nodes + 1) * (math.pi / (2 * (nodes + 1)))
    with tempfile.TemporaryDirectory(prefix="spin-build-", dir=output.parent) as scratch:
        scratch = Path(scratch)
        executable = scratch / "sampler"
        compilation_environment = dict(os.environ, TMPDIR=str(scratch))
        subprocess.run(["g++", "-O3", "-std=c++17", "-march=native",
                        str(Path(__file__).with_name("sampler.cpp")), "-o", str(executable)],
                       check=True, env=compilation_environment)
        model_path = scratch / "model.txt"
        raw_path = scratch / "blocks.txt"
        samples_path = scratch / "samples.bin"
        write_model(case, angles, model_path)
        runtime = max(1.0, budget - (time.monotonic() - start) - 15)
        subprocess.run([str(executable), str(model_path), str(raw_path), str(runtime),
                        os.environ.get("SPIN_KERNEL", "cluster5"), str(samples_path)], check=True, timeout=runtime + 15)
        raw = np.loadtxt(raw_path)
        samples = np.fromfile(samples_path, dtype=np.float64).reshape(-1, 8)
        if os.environ.get("SPIN_SAVE_BLOCKS"):
            np.savetxt(output.with_suffix(".blocks.txt"), raw)
            np.save(output.with_suffix(".samples.npy"), samples)
        result = integrate(*summarize(raw), case["angles"])
        diagonal = np.max(np.abs(np.asarray(case["onsite"])[:, 3:6])) < 1e-15
        if diagonal and len(samples) >= 10 * nodes and not os.environ.get("SPIN_NO_MBAR"):
            try:
                result.update(reweight(samples, angles, case["angles"], case["temperature"], case["n_spins"]))
            except (ArithmeticError, ValueError, np.linalg.LinAlgError) as error:
                print(f"Reweighting unavailable; using torque integration: {error}", file=sys.stderr)
    result.update(version=1, case_id=case["case_id"], runtime_seconds=time.monotonic() - start)
    with open(output, "w") as stream:
        json.dump(result, stream, allow_nan=False)


if __name__ == "__main__":
    main()
