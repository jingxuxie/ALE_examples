"""Author-written restricted single-origin baseline; NumPy-only implementation."""

import argparse

import numpy as np


def single_origin(data, triplet):
    p2s_map = data["p2s_map"]
    s2p_map = data["s2p_map"]
    primitive_count = len(p2s_map)
    supercell_count = len(s2p_map)
    force_constants = data["fc3"]
    vectors = data["shortest_vectors"]
    multiplicities = data["multiplicities"]
    positions = data["primitive_positions"]
    result = np.zeros((primitive_count,) * 3 + (3,) * 3, dtype=np.complex128)
    groups = [np.flatnonzero(s2p_map == representative) for representative in p2s_map]
    for anchor in range(primitive_count):
        phases = np.empty((2, supercell_count), dtype=np.complex128)
        for superatom in range(supercell_count):
            count, offset = multiplicities[superatom, anchor]
            selected_vectors = vectors[offset : offset + count]
            phases[:, superatom] = np.exp(
                2j * np.pi * (triplet[1:] @ selected_vectors.T)
            ).mean(axis=1)
        row = anchor if force_constants.shape[0] == primitive_count else p2s_map[anchor]
        prephase = np.exp(2j * np.pi * (triplet.sum(axis=0) @ (positions[anchor] - positions[0])))
        for second, second_group in enumerate(groups):
            for third, third_group in enumerate(groups):
                blocks = force_constants[row][second_group[:, None], third_group[None, :]]
                result[anchor, second, third] = prephase * np.einsum(
                    "u,v,uvabc->abc",
                    phases[0, second_group],
                    phases[1, third_group],
                    blocks,
                    optimize=True,
                )
    return result


def contract_modes(tensor, eigenvectors, frequencies, masses, cutoff):
    primitive_count = len(masses)
    band_count = 3 * primitive_count
    weighted = eigenvectors.reshape(3, primitive_count, 3, band_count)
    weighted = weighted / np.sqrt(masses)[None, :, None, None]
    amplitude = np.einsum(
        "ijkabc,iau,jbv,kcw->uvw", tensor, *weighted, optimize=True
    )
    products = (
        frequencies[0, :, None, None]
        * frequencies[1, None, :, None]
        * frequencies[2, None, None, :]
    )
    valid = (
        (frequencies[0, :, None, None] > cutoff)
        & (frequencies[1, None, :, None] > cutoff)
        & (frequencies[2, None, None, :] > cutoff)
    )
    strengths = np.zeros((band_count,) * 3, dtype=np.float64)
    np.divide(np.abs(amplitude) ** 2, products, out=strengths, where=valid)
    return strengths


def solve(data):
    tensors = []
    strengths = []
    for index, triplet in enumerate(data["qpoints"]):
        tensor = single_origin(data, triplet)
        tensors.append(tensor)
        strengths.append(
            contract_modes(
                tensor,
                data["eigenvectors"][index],
                data["frequencies"][index],
                data["masses"],
                float(data["cutoff_frequency"]),
            )
        )
    return {"reciprocal_fc3": np.asarray(tensors), "coupling_strength": np.asarray(strengths)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("output")
    arguments = parser.parse_args()
    with np.load(arguments.input, allow_pickle=False) as archive:
        result = solve(archive)
    np.savez_compressed(arguments.output, **result)


if __name__ == "__main__":
    main()
