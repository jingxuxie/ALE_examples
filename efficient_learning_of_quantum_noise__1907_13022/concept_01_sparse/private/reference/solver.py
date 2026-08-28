import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import sys

import numpy as np
from scipy.linalg import cholesky, solve_triangular
from scipy.optimize import nnls


def walsh(values):
    result = np.array(values, dtype=np.float64, copy=True)
    width = 1
    while width < result.shape[-1]:
        blocks = result.reshape(*result.shape[:-1], -1, 2 * width)
        left = blocks[..., :width].copy()
        right = blocks[..., width:].copy()
        blocks[..., :width] = left + right
        blocks[..., width:] = left - right
        width *= 2
    return result


def signatures(bits, hashes, offsets):
    signs = 1.0 - 2.0 * ((offsets @ bits.T) & 1)
    powers = 1 << np.arange(hashes.shape[1])
    keys = ((bits[None, :, :] @ hashes.transpose(0, 2, 1)) & 1) @ powers
    return signs, keys


def refine(original, bits, hashes, offsets):
    signs, keys = signatures(bits, hashes, offsets)
    count = len(bits)
    gram = np.zeros((count, count))
    target = np.zeros(count)
    correlation = signs.T @ signs
    for group in range(len(hashes)):
        gram += correlation * (keys[group, :, None] == keys[group, None, :])
        target += np.sum(signs * original[group][:, keys[group]], axis=0)
    divisor = len(hashes) * len(offsets)
    gram /= divisor
    target /= divisor
    factor = cholesky(gram + np.eye(count) * 1e-12, lower=True)
    amplitudes = nnls(factor.T, solve_triangular(factor, target, lower=True))[0]
    if amplitudes.sum() > 1:
        amplitudes /= amplitudes.sum()
    residual = original.copy()
    rows = np.arange(len(offsets))[:, None]
    for group in range(len(hashes)):
        np.add.at(residual[group], (rows, keys[group][None, :]), -signs * amplitudes)
    return amplitudes, residual


def reconstruct(data, rounds=30, joint=True):
    hashes = data["hashes"]
    offsets = data["offsets"]
    dimensions = hashes.shape[-1]
    bin_count = data["eigenvalues"].shape[-1]
    original = walsh(data["eigenvalues"]) / bin_count
    floor = float(data["recovery_floor"])
    noise = np.sqrt(np.mean(data["noise_std"] ** 2, axis=1) / bin_count)
    powers = 1 << np.arange(hashes.shape[1])
    support = [np.zeros(dimensions, dtype=np.uint8)]
    known = {support[0].tobytes()}
    amplitudes, residual = refine(original, np.array(support), hashes, offsets)
    limit = int(data["max_terms"])
    for iteration in range(rounds):
        discovered = {}
        for group in range(len(hashes)):
            values = residual[group]
            bits = (values[1 : dimensions + 1].T < 0).astype(np.uint8)
            signs = 1.0 - 2.0 * ((offsets @ bits.T) & 1)
            estimates = np.mean(values * signs, axis=0)
            mismatch = np.sqrt(np.mean((values - signs * estimates) ** 2, axis=0))
            keys = ((bits @ hashes[group].T) & 1) @ powers
            valid = (keys == np.arange(bin_count)) & (estimates > 0.55 * floor)
            valid &= mismatch < np.maximum(2.8 * noise[group], 0.22 * estimates)
            for location in np.flatnonzero(valid):
                key = bits[location].tobytes()
                if key not in known:
                    quality = mismatch[location] / max(estimates[location], floor)
                    if key not in discovered or quality < discovered[key][0]:
                        discovered[key] = (quality, estimates[location], bits[location].copy())
        if not discovered:
            break
        ordered = sorted(discovered.items(), key=lambda item: -item[1][1])
        selected = ordered[: limit + 1 - len(support)]
        if not selected:
            break
        for key, (_, estimate, bits) in selected:
            known.add(key)
            support.append(bits)
            if not joint:
                amplitudes = np.append(amplitudes, estimate)
                signs, keys = signatures(bits[None, :], hashes, offsets)
                for group in range(len(hashes)):
                    residual[group, :, keys[group, 0]] -= signs[:, 0] * estimate
        if joint:
            amplitudes, residual = refine(original, np.array(support), hashes, offsets)
    bits = np.array(support, dtype=np.uint8)
    if joint:
        amplitudes, residual = refine(original, bits, hashes, offsets)
    if amplitudes.sum() > 1:
        amplitudes /= amplitudes.sum()
    lookup = np.array([0, 3, 1, 2], dtype=np.uint8)
    paulis = lookup[2 * bits[1:, 0::2] + bits[1:, 1::2]]
    keep = amplitudes[1:] > 0.25 * floor
    return {
        "paulis": paulis[keep],
        "probabilities": amplitudes[1:][keep].astype(np.float64),
        "p_identity": np.array(amplitudes[0], dtype=np.float64),
    }


def main():
    with np.load(sys.argv[1], allow_pickle=False) as archive:
        data = {key: archive[key] for key in archive.files}
    np.savez(sys.argv[2], **reconstruct(data))


if __name__ == "__main__":
    main()
