"""Private ctypes bindings to the unmodified, pinned official C kernels."""

import ctypes

import numpy as np
import phono3py
import phono3py._phono3py as extension
import phonopy
import spglib


class AtomTriplets(ctypes.Structure):
    _fields_ = [
        ("svecs", ctypes.c_void_p),
        ("multi_dims", ctypes.c_int64 * 2),
        ("multiplicity", ctypes.c_void_p),
        ("p2s_map", ctypes.c_void_p),
        ("s2p_map", ctypes.c_void_p),
        ("make_r0_average", ctypes.c_int64),
        ("all_shortest", ctypes.c_void_p),
        ("nonzero_indices", ctypes.c_void_p),
    ]


def runtime_versions():
    versions = {
        "phono3py": phono3py.__version__,
        "phonopy": phonopy.__version__,
        "spglib": spglib.__version__,
        "numpy": np.__version__,
    }
    expected = {"phono3py": "3.19.2", "phonopy": "2.43.4", "spglib": "2.5.0"}
    for package, version in expected.items():
        if versions[package] != version:
            raise RuntimeError(f"Expected {package}=={version}, found {versions[package]}")
    return versions


class Oracle:
    def __init__(self):
        runtime_versions()
        self.library = ctypes.CDLL(extension.__file__)
        self.transform = self.library.r2r_real_to_reciprocal
        self.transform.restype = None
        self.transform.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64,
            ctypes.POINTER(AtomTriplets), ctypes.c_int64,
        ]
        self.contract = self.library.reciprocal_to_normal_squared
        self.contract.restype = None
        self.contract.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.c_int64, ctypes.c_int64, ctypes.c_double, ctypes.c_int64,
        ]

    def solve(self, data, average=True, all_shortest=None):
        p2s_map = np.ascontiguousarray(data["p2s_map"], dtype=np.int64)
        s2p_map = np.ascontiguousarray(data["s2p_map"], dtype=np.int64)
        primitive_count = len(p2s_map)
        supercell_count = len(s2p_map)
        band_count = primitive_count * 3
        force_constants = np.ascontiguousarray(data["fc3"], dtype=np.float64)
        vectors = np.ascontiguousarray(data["shortest_vectors"], dtype=np.float64)
        multiplicities = np.ascontiguousarray(data["multiplicities"], dtype=np.int64)
        if all_shortest is None:
            all_shortest = np.zeros((primitive_count, supercell_count, supercell_count), dtype=np.int8)
        all_shortest = np.ascontiguousarray(all_shortest, dtype=np.int8)
        nonzero = np.ones(force_constants.shape[:3], dtype=np.int8)
        atoms = AtomTriplets(
            vectors.ctypes.data,
            (ctypes.c_int64 * 2)(supercell_count, primitive_count),
            multiplicities.ctypes.data,
            p2s_map.ctypes.data,
            s2p_map.ctypes.data,
            int(average),
            all_shortest.ctypes.data,
            nonzero.ctypes.data,
        )
        qpoints = np.ascontiguousarray(data["qpoints"], dtype=np.float64)
        frequencies = np.ascontiguousarray(data["frequencies"], dtype=np.float64)
        eigenvectors = np.ascontiguousarray(data["eigenvectors"], dtype=np.complex128)
        masses = np.ascontiguousarray(data["masses"], dtype=np.float64)
        bands = np.arange(band_count, dtype=np.int64)
        band_triples = np.indices((band_count,) * 3).reshape(3, -1).T
        g_positions = np.ascontiguousarray(
            np.column_stack((band_triples, np.arange(band_count**3))), dtype=np.int64
        )
        tensors = []
        strengths = []
        for index, triplet in enumerate(qpoints):
            flattened = np.zeros((band_count,) * 3, dtype=np.complex128)
            strength = np.zeros((band_count,) * 3, dtype=np.float64)
            self.transform(
                flattened.ctypes.data, triplet.ctypes.data, force_constants.ctypes.data,
                int(force_constants.shape[0] == primitive_count), ctypes.byref(atoms), 1,
            )
            self.contract(
                strength.ctypes.data, g_positions.ctypes.data, len(g_positions),
                flattened.ctypes.data,
                *[frequencies[index, leg].ctypes.data for leg in range(3)],
                *[eigenvectors[index, leg].ctypes.data for leg in range(3)],
                masses.ctypes.data, bands.ctypes.data, band_count, band_count,
                float(data["cutoff_frequency"]), 1,
            )
            tensors.append(
                flattened.reshape(primitive_count, 3, primitive_count, 3, primitive_count, 3)
                .transpose(0, 2, 4, 1, 3, 5).copy()
            )
            strengths.append(strength)
        return {"reciprocal_fc3": np.asarray(tensors), "coupling_strength": np.asarray(strengths)}
