#!/usr/bin/env python3
"""Three-origin reciprocal cubic force constants and phonon mode strengths."""

import argparse

import numpy as np


class CubicInterpolator:
    def __init__(self, data):
        representatives = data["p2s_map"]
        supercell_map = data["s2p_map"]
        self.primitive_count = len(representatives)
        self.supercell_count = len(supercell_map)
        self.groups = [
            np.flatnonzero(supercell_map == representative)
            for representative in representatives
        ]
        force_constants = data["fc3"]
        if force_constants.shape[0] != self.primitive_count:
            force_constants = force_constants[representatives]
        self.force_constants = force_constants
        self.vectors = data["shortest_vectors"]
        positions = data["primitive_positions"]
        self.relative_positions = positions - positions[0]
        multiplicities = data["multiplicities"]
        counts = multiplicities[..., 0].ravel()
        offsets = multiplicities[..., 1].ravel()
        self.vector_slices = []
        for count in np.unique(counts):
            locations = np.flatnonzero(counts == count)
            indices = offsets[locations, None] + np.arange(count)[None, :]
            self.vector_slices.append((locations, indices))

    def phases(self, triplet):
        exponentials = np.exp(2j * np.pi * (self.vectors @ triplet.T))
        phases = np.empty(
            (self.supercell_count * self.primitive_count, 3),
            dtype=np.complex128,
        )
        for locations, indices in self.vector_slices:
            phases[locations] = exponentials[indices].mean(axis=1)
        return phases.reshape(
            self.supercell_count, self.primitive_count, 3
        ).transpose(2, 1, 0)

    def interpolate(self, triplet):
        phases = self.phases(triplet)
        prephases = np.exp(
            2j * np.pi * (self.relative_positions @ triplet.sum(axis=0))
        )
        origins = np.empty(
            (3,) + (self.primitive_count,) * 3 + (3,) * 3,
            dtype=np.complex128,
        )
        for anchor in range(self.primitive_count):
            left_phases = phases[[1, 0, 1], anchor]
            right_phases = phases[[2, 2, 0], anchor]
            row = self.force_constants[anchor]
            for second, second_group in enumerate(self.groups):
                for third, third_group in enumerate(self.groups):
                    blocks = row[second_group[:, None], third_group[None, :]]
                    origins[:, anchor, second, third] = prephases[anchor] * np.einsum(
                        "rs,ru,suijk->rijk",
                        left_phases[:, second_group],
                        right_phases[:, third_group],
                        blocks,
                        optimize=True,
                    )
        tensor = origins[0].copy()
        tensor += origins[1].transpose(1, 0, 2, 4, 3, 5)
        tensor += origins[2].transpose(2, 1, 0, 5, 4, 3)
        tensor /= 3.0
        return tensor


def contract_modes(tensor, eigenvectors, frequencies, masses, cutoff):
    primitive_count = len(masses)
    band_count = 3 * primitive_count
    weighted = eigenvectors.reshape(3, primitive_count, 3, band_count)
    weighted = weighted / np.sqrt(masses)[None, :, None, None]
    amplitude = np.einsum(
        "ijkabc,iau,jbv,kcw->uvw", tensor, *weighted, optimize=True
    )
    valid = (
        (frequencies[0, :, None, None] > cutoff)
        & (frequencies[1, None, :, None] > cutoff)
        & (frequencies[2, None, None, :] > cutoff)
    )
    products = (
        frequencies[0, :, None, None]
        * frequencies[1, None, :, None]
        * frequencies[2, None, None, :]
    )
    strengths = np.zeros((band_count,) * 3, dtype=np.float64)
    np.divide(np.abs(amplitude) ** 2, products, out=strengths, where=valid)
    return strengths


def solve(data):
    interpolator = CubicInterpolator(data)
    qpoints = data["qpoints"]
    eigenvectors = data["eigenvectors"]
    frequencies = data["frequencies"]
    masses = data["masses"]
    cutoff = float(data["cutoff_frequency"])
    primitive_count = interpolator.primitive_count
    tensors = np.empty(
        (len(qpoints),) + (primitive_count,) * 3 + (3,) * 3,
        dtype=np.complex128,
    )
    strengths = np.empty(
        (len(qpoints),) + (3 * primitive_count,) * 3,
        dtype=np.float64,
    )
    for index, triplet in enumerate(qpoints):
        tensors[index] = interpolator.interpolate(triplet)
        strengths[index] = contract_modes(
            tensors[index], eigenvectors[index], frequencies[index], masses, cutoff
        )
    return {"reciprocal_fc3": tensors, "coupling_strength": strengths}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("output")
    arguments = parser.parse_args()
    with np.load(arguments.input, allow_pickle=False) as data:
        result = solve(data)
    np.savez_compressed(arguments.output, **result)


if __name__ == "__main__":
    main()
