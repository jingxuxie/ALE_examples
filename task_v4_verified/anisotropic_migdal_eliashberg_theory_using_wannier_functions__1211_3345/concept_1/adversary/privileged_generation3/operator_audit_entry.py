"""Non-solving operator regression entry, executed only in the sandbox."""

import argparse
import numpy as np
import v4
from operator_core import FusedModel, PrefixCoarse


def relative_error(actual, expected):
    return np.max(np.abs(actual - expected)) / max(np.max(np.abs(expected)), 1e-100)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    with np.load(arguments.input, allow_pickle=False) as archive:
        instance = {key: archive[key] for key in archive.files}
    original = v4.Model(instance)
    fused = FusedModel(instance)
    random = np.random.default_rng(1384907)
    values = random.standard_normal(original.shape)
    measurements = []
    for parity in (1, -1):
        measurements.append(relative_error(fused.convolve(values, parity), original.convolve(values, parity)))
    coarse = PrefixCoarse(fused)
    small_values = random.standard_normal(coarse.shape)
    expanded = coarse.expand(small_values)
    for parity in (1, -1):
        measurements.append(relative_error(coarse.convolve(small_values, parity),
                                           original.convolve(expanded, parity)[:, coarse.indices]))
    measurements.append(relative_error(small_values @ coarse.quadrature, expanded.sum(axis=1)))
    measurements.append(relative_error(coarse.expand(small_values)[:, coarse.indices], small_values))
    original_z, original_gap = original.map(instance["initial_delta"])
    fused_z, fused_gap = fused.map(instance["initial_delta"])
    measurements.append(relative_error(fused_z, original_z))
    measurements.append(relative_error(fused_gap, original_gap))
    measurements.extend((coarse.rank, coarse.n_freq, fused.symbol.nbytes))
    encoded = np.zeros(original.shape)
    encoded[0, :len(measurements)] = measurements
    np.savez(arguments.output, delta=encoded, z=np.ones(original.shape))


if __name__ == "__main__":
    main()
