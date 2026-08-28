import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import importlib.util
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
REFERENCE = ROOT / "concept_01_sparse/private/reference"
sys.path.insert(0, str(REFERENCE))
sys.path.insert(0, str(ROOT / "private/sources/python-bchlib"))

import bchlib
from build import observations, sampling_hash
from metrics import grade, measure
from physical import masks_to_observables, spectrum
from solver import refine, walsh


def coding_rows(dimensions, degree, strength):
    decoder = bchlib.BCH(strength, m=degree)
    encoded = []
    for index in range(dimensions):
        message = np.zeros(dimensions, dtype=np.uint8)
        message[index] = 1
        packet = decoder.encode(np.packbits(message).tobytes())
        encoded.append(np.unpackbits(np.frombuffer(packet, dtype=np.uint8)))
    matrix = np.array(encoded, dtype=np.uint8).T
    active = np.flatnonzero(np.any(matrix, axis=1))
    if len(active) != decoder.ecc_bits:
        raise AssertionError("Unexpected BCH padding layout")
    rows = np.vstack((np.zeros((1, dimensions), dtype=np.uint8),
                      np.eye(dimensions, dtype=np.uint8), matrix[active]))
    return decoder, rows, active


def reconstruct(data, degree, strength):
    hashes, offsets = data["hashes"], data["offsets"]
    dimensions = hashes.shape[-1]
    decoder, expected_rows, active = coding_rows(dimensions, degree, strength)
    if not np.array_equal(offsets, expected_rows):
        raise ValueError("Input offsets do not match the declared code")
    original = walsh(data["eigenvalues"]) / data["eigenvalues"].shape[-1]
    noise = np.sqrt(np.mean(data["noise_std"] ** 2, axis=1) / original.shape[-1])
    floor = float(data["recovery_floor"])
    powers = 1 << np.arange(hashes.shape[1])
    support = [np.zeros(dimensions, dtype=np.uint8)]
    known = {support[0].tobytes()}
    amplitudes, residual = refine(original, np.array(support), hashes, offsets)
    diagnostics = []
    for iteration in range(35):
        discovered = {}
        calls, decoded = 0, 0
        for group in range(len(hashes)):
            for location in range(original.shape[-1]):
                values = residual[group, :, location]
                if np.mean(values[1:] ** 2) < noise[group] ** 2 + (floor * 0.4) ** 2:
                    continue
                hard = (values[1:] < 0).astype(np.uint8)
                message = bytearray(np.packbits(hard[:dimensions]).tobytes())
                parity = np.zeros(decoder.ecc_bytes * 8, dtype=np.uint8)
                parity[active] = hard[dimensions:]
                parity = bytearray(np.packbits(parity).tobytes())
                calls += 1
                errors = decoder.decode(message, parity)
                if errors < 0:
                    continue
                decoded += 1
                decoder.correct(message, parity)
                bits = np.unpackbits(np.frombuffer(message, dtype=np.uint8))
                key = bits.tobytes()
                if key in known or int(((hashes[group] @ bits) & 1) @ powers) != location:
                    continue
                signs = 1.0 - 2.0 * ((offsets @ bits) & 1)
                estimate = float(np.mean(values * signs))
                mismatch = float(np.sqrt(np.mean((values - estimate * signs) ** 2)))
                if estimate < 0.55 * floor or mismatch > max(2.8 * noise[group], 0.22 * estimate):
                    continue
                if key not in discovered or estimate > discovered[key][0]:
                    discovered[key] = (estimate, bits)
        ordered = sorted(discovered.items(), key=lambda item: -item[1][0])
        selected = ordered[:int(data["max_terms"]) + 1 - len(support)]
        diagnostics.append(dict(iteration=iteration, calls=calls, decoded=decoded, added=len(selected)))
        if not selected:
            break
        for key, (_, bits) in selected:
            support.append(bits)
            known.add(key)
        amplitudes, residual = refine(original, np.array(support), hashes, offsets)
    bits = np.array(support, dtype=np.uint8)
    lookup = np.array([0, 3, 1, 2], dtype=np.uint8)
    labels = lookup[2 * bits[1:, 0::2] + bits[1:, 1::2]]
    keep = amplitudes[1:] > 0.25 * floor
    return dict(paulis=labels[keep], probabilities=amplitudes[1:][keep],
                p_identity=np.array(amplitudes[0])), diagnostics


def make_case(seed, degree, strength, snr):
    generator = np.random.default_rng(seed)
    qubits, count, groups, hash_bits = 100, 192, 4, 7
    probabilities = generator.uniform(0.98, 1.02, count)
    probabilities *= 0.12 / probabilities.sum()
    paulis = generator.integers(0, 4, (count, qubits), dtype=np.uint8)
    lookup = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=np.uint8)
    bits = lookup[paulis].reshape(count, 2 * qubits)
    hashes = np.array([sampling_hash(generator, qubits, hash_bits) for group in range(groups)])
    decoder, offsets, active = coding_rows(2 * qubits, degree, strength)
    clean = observations(bits, probabilities, 0.88, hashes, offsets)
    noise_std = np.full((groups, len(offsets)), float(probabilities.min()) / snr * np.sqrt(2**hash_bits))
    values = clean + generator.normal(size=clean.shape) * noise_std[:, :, None]
    probes = generator.integers(0, 4, (384, qubits), dtype=np.uint8)
    error = 0.0
    for group in range(groups):
        times = generator.integers(0, len(offsets), 32)
        locations = generator.integers(0, 2**hash_bits, 32)
        binary = ((locations[:, None] >> np.arange(hash_bits)) & 1).astype(np.uint8)
        masks = offsets[times] ^ ((binary @ hashes[group]) & 1)
        independent = spectrum(paulis, probabilities, 0.88, masks_to_observables(masks))
        error = max(error, float(np.max(np.abs(independent - clean[group, times, locations]))))
    if error >= 2e-12:
        raise AssertionError(error)
    data = dict(n_qubits=np.array(qubits, dtype=np.int64), hashes=hashes, offsets=offsets,
                eigenvalues=values, noise_std=noise_std, recovery_floor=np.array(probabilities.min() * 0.8),
                max_terms=np.array(512, dtype=np.int64))
    truth = dict(paulis=paulis, probabilities=probabilities, p_identity=np.array(0.88),
                 probe_paulis=probes, probe_spectrum=spectrum(paulis, probabilities, 0.88, probes))
    metadata = dict(seed=seed, qubits=qubits, heavy_terms=count, degree=degree, strength=strength,
                    primitive_polynomial=decoder.prim_poly, ecc_bits=decoder.ecc_bits,
                    minimum_bin_snr=snr, offset_rows=len(offsets), independent_forward_error=error)
    return data, truth, metadata


def load_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def audit():
    evaluator = load_module("sparse_evaluator", ROOT / "concept_01_sparse/private/evaluator.py")
    frozen = ROOT / "private/runs/pilot/submissions/concept_01_sparse.py"
    specifications = [(7628301, 8, 6, 2.1), (7628302, 9, 20, 1.7), (7628303, 9, 30, 1.6)]
    results = []
    for index, (seed, degree, strength, snr) in enumerate(specifications):
        directory = HERE / f"case_{index:02d}"
        directory.mkdir(exist_ok=True)
        data, truth, metadata = make_case(seed, degree, strength, snr)
        np.savez_compressed(directory / "input.npz", **data)
        np.savez_compressed(directory / "truth.npz", **truth)
        (directory / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
        start = time.monotonic()
        command = [sys.executable, str(Path(__file__).resolve()), "--reference", str(directory / "input.npz"),
                   str(directory / "reference.npz"), "--degree", str(degree), "--strength", str(strength)]
        process = subprocess.run(command, capture_output=True, text=True, timeout=120)
        if process.returncode:
            raise RuntimeError(process.stderr)
        reference = dict(np.load(directory / "reference.npz", allow_pickle=False))
        reference_time = time.monotonic() - start
        weak, weak_runtime = evaluator.run_solver(REFERENCE / "weak_solver.py", directory / "input.npz", directory / "weak.npz")
        prediction, runtime = evaluator.run_solver(frozen, directory / "input.npz", directory / "frozen.npz")
        calibration = dict(reference=measure(reference, truth, float(data["recovery_floor"])),
                           weak=measure(weak, truth, float(data["recovery_floor"])))
        result = dict(**metadata, reference=dict(**grade(calibration["reference"], calibration), runtime_seconds=reference_time),
                      weak=dict(**grade(calibration["weak"], calibration), **weak_runtime))
        result["frozen"] = dict(**grade(measure(prediction, truth, float(data["recovery_floor"])), calibration), **runtime) if prediction else dict(score=0.0, **runtime)
        result["reference_eligible"] = (result["reference"]["score"] > 0.9 and result["reference"]["loss"] < 0.1
                                          and result["reference"]["recovery_score"] >= 0.98)
        results.append(result)
        (HERE / "results.json").write_text(json.dumps(results, indent=2) + "\n")
        print(json.dumps(dict(case=index, reference=result["reference"], frozen=result["frozen"], eligible=result["reference_eligible"])), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", nargs=2)
    parser.add_argument("--degree", type=int)
    parser.add_argument("--strength", type=int)
    arguments = parser.parse_args()
    if arguments.reference:
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
        resource.setrlimit(resource.RLIMIT_CPU, (120, 125))
        data = dict(np.load(arguments.reference[0], allow_pickle=False))
        prediction, diagnostics = reconstruct(data, arguments.degree, arguments.strength)
        np.savez_compressed(arguments.reference[1], **prediction)
        Path(arguments.reference[1]).with_suffix(".diagnostics.json").write_text(json.dumps(diagnostics, indent=2) + "\n")
    else:
        audit()


if __name__ == "__main__":
    main()
