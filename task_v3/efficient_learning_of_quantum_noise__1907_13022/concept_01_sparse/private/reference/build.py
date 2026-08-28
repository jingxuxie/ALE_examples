import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from physical import masks_to_observables, spectrum


ROOT = Path(__file__).resolve().parents[2]
FAMILIES = ("collisions", "dynamic_range", "approximate")


def transform(values):
    result = values.copy()
    for exponent in range(result.shape[-1].bit_length() - 1):
        width = 2**exponent
        blocks = result.reshape(result.shape[0], -1, 2, width)
        saved = blocks.copy()
        blocks[:, :, 0] = saved[:, :, 0] + saved[:, :, 1]
        blocks[:, :, 1] = saved[:, :, 0] - saved[:, :, 1]
    return result


def sampling_hash(generator, qubits, hash_bits):
    result = np.zeros((hash_bits, 2 * qubits), dtype=np.uint8)
    result[np.arange(hash_bits), 2 * generator.choice(qubits, hash_bits, replace=False)] = 1
    for layer in range(24):
        for qubit in generator.choice(qubits, qubits // 2, replace=False):
            result[:, [2 * qubit, 2 * qubit + 1]] = result[:, [2 * qubit + 1, 2 * qubit]]
        for qubit in generator.choice(qubits, qubits // 2, replace=False):
            result[:, 2 * qubit + 1] ^= result[:, 2 * qubit]
        ordering = generator.permutation(qubits)
        for control, target in zip(ordering[0::2], ordering[1::2]):
            result[:, 2 * target] ^= result[:, 2 * control]
            result[:, 2 * control + 1] ^= result[:, 2 * target + 1]
    return result


def observations(bits, probabilities, p_identity, hashes, offsets):
    bin_count = 2 ** hashes.shape[1]
    signs = 1.0 - 2.0 * ((offsets @ bits.T) & 1)
    result = np.empty((len(hashes), len(offsets), bin_count))
    for group, matrix in enumerate(hashes):
        keys = ((bits @ matrix.T) & 1) @ (1 << np.arange(matrix.shape[0]))
        bins = np.zeros((len(offsets), bin_count))
        for offset in range(len(offsets)):
            bins[offset] = np.bincount(keys, weights=probabilities * signs[offset], minlength=bin_count)
        bins[:, 0] += p_identity
        result[group] = transform(bins)
    return result


def case_parameters(family, index, pool, region):
    position = index // 3
    qubits = (40, 64, 88)[position % 3] + 4 * FAMILIES.index(family)
    count = (220, 250, 280)[position % 3]
    span = 10.0
    if family == "dynamic_range":
        span = (300.0, 1000.0, 3000.0)[position % 3]
        count -= 30
    if family == "approximate":
        span = (24.0, 40.0, 64.0)[position % 3]
    groups = 4
    noise_ratio = 0.13
    if pool == "challenge":
        qubits = min(100, qubits + 12)
        count += 80
        groups = 5
        noise_ratio = 0.17
        if family == "dynamic_range":
            span *= 3
    if region != "standard":
        qubits = min(100, qubits + 2)
        count += 17
        span *= 1.15
        noise_ratio *= 1.05
    return qubits, count, span, groups, noise_ratio


def generate_case(seed, family, index, pool="core", region="standard", example=False):
    digest = hashlib.sha256(f"{seed}:{region}:{pool}:{family}:{index}".encode()).digest()
    generator = np.random.default_rng(int.from_bytes(digest[:16], "little"))
    qubits, count, span, groups, noise_ratio = case_parameters(family, index, pool, region)
    hash_bits = 7
    if example:
        qubits, count, span, groups, hash_bits = 40, 72, 24.0, 3, 6
    tail_count = (4096 + 2048 * (index // 3)) if family == "approximate" else 0
    if example:
        tail_count = 0
    error_mass = 0.12 + 0.035 * (index % 3) + generator.uniform(-0.01, 0.01)
    tail_mass = error_mass * (0.04 if tail_count else 0.0)
    heavy = np.geomspace(1.0, span, count) * generator.uniform(0.95, 1.05, count)
    generator.shuffle(heavy)
    heavy *= (error_mass - tail_mass) / heavy.sum()
    background = generator.uniform(0.6, 1.4, tail_count)
    if tail_count:
        background *= tail_mass / background.sum()
    probabilities = np.concatenate([heavy, background])
    paulis = generator.integers(0, 4, (len(probabilities), qubits), dtype=np.uint8)
    assert np.all(np.any(paulis, axis=1)) and len(np.unique(paulis, axis=0)) == len(paulis)
    lookup = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=np.uint8)
    bits = lookup[paulis].reshape(len(paulis), 2 * qubits)
    hashes = np.array([sampling_hash(generator, qubits, hash_bits) for group in range(groups)])
    offsets = np.vstack([np.zeros((1, 2 * qubits), dtype=np.uint8), np.eye(2 * qubits, dtype=np.uint8), generator.integers(0, 2, (48 if pool == "challenge" else 32, 2 * qubits), dtype=np.uint8)])
    clean = observations(bits, probabilities, 1 - error_mass, hashes, offsets)
    bin_sigma = float(heavy.min() * noise_ratio)
    noise_std = bin_sigma * np.sqrt(2**hash_bits) * generator.uniform(0.9, 1.1, (groups, len(offsets)))
    values = clean + generator.normal(size=clean.shape) * noise_std[:, :, None]
    probes = generator.integers(0, 4, (384, qubits), dtype=np.uint8)
    expected = spectrum(paulis, probabilities, 1 - error_mass, probes)
    verification_error = 0.0
    for group in range(groups):
        times = generator.integers(0, len(offsets), 24)
        indexes = generator.integers(0, 2**hash_bits, 24)
        binary = ((indexes[:, None] >> np.arange(hash_bits)) & 1).astype(np.uint8)
        masks = offsets[times] ^ ((binary @ hashes[group]) & 1)
        independent = spectrum(paulis, probabilities, 1 - error_mass, masks_to_observables(masks))
        verification_error = max(verification_error, float(np.max(np.abs(independent - clean[group, times, indexes]))))
    assert verification_error < 2e-12
    floor = float(heavy.min() * 0.8)
    assert not tail_count or background.max() < floor / 3
    data = dict(n_qubits=np.array(qubits, dtype=np.int64), hashes=hashes, offsets=offsets, eigenvalues=values, noise_std=noise_std, recovery_floor=np.array(floor), max_terms=np.array(512, dtype=np.int64))
    truth = dict(paulis=paulis, probabilities=probabilities, p_identity=np.array(1 - error_mass), probe_paulis=probes, probe_spectrum=expected)
    occupancies = []
    has_singleton = np.zeros(count, dtype=bool)
    for matrix in hashes:
        keys = ((bits[:count] @ matrix.T) & 1) @ (1 << np.arange(hash_bits))
        occupancy = np.bincount(keys, minlength=2**hash_bits)
        has_singleton |= occupancy[keys] == 1
        occupancies.append(float(np.mean(occupancy >= 2)))
    metadata = dict(family=family, qubits=qubits, heavy_terms=count, tail_terms=tail_count, tail_mass=float(tail_mass), nonidentity_mass=float(error_mass), dynamic_range=float(heavy.max() / heavy.min()), bin_noise_to_minimum=bin_sigma / float(heavy.min()), mean_weight=float(np.count_nonzero(paulis[:count], axis=1).mean()), initially_no_singleton_fraction=float(np.mean(~has_singleton)), collision_bin_fraction=float(np.mean(occupancies)), independent_observation_max_error=verification_error)
    return data, truth, metadata


def build(destination, seed, pool, region, count):
    destination = Path(destination).resolve()
    destination.relative_to(ROOT / "private")
    destination.mkdir(parents=True, exist_ok=True)
    manifest = dict(schema_version=1, seed=seed, pool=pool, region=region, calibrated=False, cases=[])
    for index in range(count):
        family = FAMILIES[index % len(FAMILIES)]
        data, truth, metadata = generate_case(seed, family, index, pool, region)
        case_id = f"case_{index:02d}"
        directory = destination / case_id
        directory.mkdir(exist_ok=True)
        np.savez_compressed(directory / "input.npz", **data)
        np.savez_compressed(directory / "truth.npz", **truth)
        manifest["cases"].append(dict(id=case_id, input=f"{case_id}/input.npz", truth=f"{case_id}/truth.npz", **metadata))
        print(f"built {pool}/{case_id}: {family}, n={metadata['qubits']}", flush=True)
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=190713022)
    parser.add_argument("--pool", choices=("core", "challenge"), default="core")
    parser.add_argument("--region", default="standard")
    parser.add_argument("--count", type=int)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--public-example", action="store_true")
    args = parser.parse_args()
    if args.public_example:
        data, truth, metadata = generate_case(817263, "dynamic_range", 0, example=True)
        directory = ROOT / "participant" / "input"
        directory.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(directory / "example.npz", **data)
    else:
        destination = args.destination or (ROOT / "private" / ("reference/core" if args.pool == "core" else "challenge_pool"))
        build(destination, args.seed, args.pool, args.region, args.count or (9 if args.pool == "core" else 6))


if __name__ == "__main__":
    main()
