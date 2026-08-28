#!/usr/bin/env python3
"""Constrained least-squares fitting of compact harmonic and cubic tensors."""

import os
import sys
import itertools
import time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import numpy as np
from scipy import linalg, sparse


def report(*values):
    if os.environ.get("FIT_VERBOSE"):
        print(*values, file=sys.stderr, flush=True)


class TensorBasis:
    def __init__(self, data, cell_number, order):
        started = time.monotonic()
        suffix = str(cell_number)
        self.order = order
        self.atom_count = len(data["numbers" + suffix])
        self.representatives = np.asarray(data["p2s" + suffix])
        self.row_map = np.asarray(data["s2p" + suffix])
        self.compact_map = np.asarray(data["compact_map" + suffix])
        self.inverse_map = np.argsort(self.compact_map, axis=1)
        self.row_count = len(self.representatives)
        self.cart_size = 3 ** order
        self.atom_shape = (self.row_count,) + (self.atom_count,) * (order - 1)
        if order == 3:
            self.clusters = np.argwhere(data["triplet_mask3"])
        else:
            self.clusters = np.indices(self.atom_shape).reshape(order, -1).T
        self.cluster_codes = np.ravel_multi_index(self.clusters.T, self.atom_shape)
        self.basis = self._symmetry_basis(data, suffix)
        report("symmetry", order, self.basis.shape, self.basis.nnz,
               "seconds", time.monotonic() - started)
        self.nullspace = self._acoustic_nullspace()
        report("acoustic", order, self.nullspace.shape,
               "seconds", time.monotonic() - started)
        self.parameter_count = self.nullspace.shape[1]
        self.slices = []
        trailing_size = 3 ** (order - 1)
        for representative in range(self.row_count):
            cluster_indices = np.flatnonzero(self.clusters[:, 0] == representative)
            components = []
            for axis in range(3):
                indices = (cluster_indices[:, None] * self.cart_size +
                           axis * trailing_size + np.arange(trailing_size)).ravel()
                components.append(self.basis[indices].T.tocsr())
            self.slices.append((self.clusters[cluster_indices, 1:], components))

    def _symmetry_basis(self, data, suffix):
        order = self.order
        cart_size = self.cart_size
        rotations = np.asarray(data["cart_rotations" + suffix])
        permutations = np.asarray(data["permutations" + suffix])
        axis_orders = list(itertools.permutations(range(order)))
        cart_operations = []
        for rotation in rotations:
            operation = rotation
            for repeat in range(order - 1):
                operation = np.kron(operation, rotation)
            cart_operations.append(operation)
        cart_operations = np.asarray(cart_operations)
        component_grid = np.arange(cart_size).reshape((3,) * order)
        transforms = np.concatenate([
            cart_operations[:, component_grid.transpose(axes).ravel(), :]
            for axes in axis_orders
        ])
        lookup = np.full(np.prod(self.atom_shape), -1, dtype=np.int64)
        lookup[self.cluster_codes] = np.arange(len(self.clusters))
        visited = np.zeros(len(self.clusters), dtype=bool)
        rows = []
        columns = []
        values = []
        column_count = 0
        for seed_id, seed in enumerate(self.clusters):
            if visited[seed_id]:
                continue
            atoms = seed.copy()
            atoms[0] = self.representatives[seed[0]]
            rotated_atoms = permutations[:, atoms]
            images = np.concatenate([rotated_atoms[:, axes] for axes in axis_orders])
            leading = images[:, 0]
            compact = np.empty_like(images)
            compact[:, 0] = self.row_map[leading]
            for index in range(1, order):
                compact[:, index] = self.compact_map[leading, images[:, index]]
            image_codes = np.ravel_multi_index(compact.T, self.atom_shape)
            image_ids = lookup[image_codes]
            orbit_ids, first = np.unique(image_ids, return_index=True)
            visited[orbit_ids[orbit_ids >= 0]] = True
            if orbit_ids[0] < 0:
                continue
            stabilizer = transforms[image_ids == seed_id].mean(axis=0)
            stabilizer = (stabilizer + stabilizer.T) * 0.5
            eigenvalues, eigenvectors = linalg.eigh(stabilizer, check_finite=False)
            invariant = eigenvectors[:, eigenvalues > 1.0 - 1e-7]
            multiplicity = invariant.shape[1]
            if multiplicity == 0:
                continue
            blocks = (transforms[first] @ invariant) / np.sqrt(len(orbit_ids))
            blocks = blocks.reshape(-1, multiplicity)
            local_rows, local_columns = np.nonzero(np.abs(blocks) > 2e-13)
            tensor_rows = (orbit_ids[:, None] * cart_size + np.arange(cart_size)).ravel()
            rows.append(tensor_rows[local_rows])
            columns.append(local_columns + column_count)
            values.append(blocks[local_rows, local_columns])
            column_count += multiplicity
        shape = (len(self.clusters) * cart_size, column_count)
        if not values:
            return sparse.csr_matrix(shape)
        return sparse.coo_matrix((np.concatenate(values),
                                  (np.concatenate(rows), np.concatenate(columns))),
                                 shape=shape).tocsr()

    def _acoustic_nullspace(self):
        parameter_count = self.basis.shape[1]
        if parameter_count == 0:
            return np.zeros((0, 0))
        prefix_shape = self.atom_shape[:-1]
        prefix = np.ravel_multi_index(self.clusters[:, :-1].T, prefix_shape)
        sum_rows = (prefix[:, None] * self.cart_size + np.arange(self.cart_size)).ravel()
        sum_operator = sparse.coo_matrix(
            (np.ones(len(sum_rows)), (sum_rows, np.arange(len(sum_rows)))),
            shape=(int(np.prod(prefix_shape)) * self.cart_size, self.basis.shape[0])
        ).tocsr()
        constraints = sum_operator @ self.basis
        gram = (constraints.T @ constraints).toarray()
        eigenvalues, eigenvectors = linalg.eigh(gram, check_finite=False)
        tolerance = max(1e-11, float(eigenvalues[-1]) * 2e-11)
        nullspace = eigenvectors[:, eigenvalues < tolerance]
        report("ASR residual", self.order,
               np.max(np.abs(constraints @ nullspace), initial=0.0))
        return nullspace

    def design(self, displacements, symmetry_only=False):
        snapshot_count = len(displacements)
        parameter_count = self.basis.shape[1] if symmetry_only else self.parameter_count
        design = np.empty((snapshot_count * self.atom_count * 3, parameter_count), order="F")
        if parameter_count == 0:
            return design
        for representative in range(self.row_count):
            atoms = np.flatnonzero(self.row_map == representative)
            samples = np.repeat(np.arange(snapshot_count), len(atoms))
            leading = np.tile(atoms, snapshot_count)
            clusters, components = self.slices[representative]
            feature_count = max(1, len(clusters) * 3 ** (self.order - 1))
            block_size = max(16, min(1024, 2000000 // feature_count))
            for begin in range(0, len(samples), block_size):
                end = min(begin + block_size, len(samples))
                sample_indices = samples[begin:end]
                atom_indices = leading[begin:end]
                inverse = self.inverse_map[atom_indices]
                first = displacements[sample_indices[:, None], inverse[:, clusters[:, 0]], :]
                if self.order == 2:
                    features = -first.reshape(end - begin, -1)
                else:
                    second = displacements[sample_indices[:, None], inverse[:, clusters[:, 1]], :]
                    features = (-0.5 * first[..., :, None] * second[..., None, :]).reshape(end - begin, -1)
                base_rows = (sample_indices * self.atom_count + atom_indices) * 3
                for axis, component in enumerate(components):
                    projected = (component @ features.T).T
                    design[base_rows + axis] = projected if symmetry_only else projected @ self.nullspace
        return design

    def tensor(self, coefficients):
        tensor = np.zeros(self.atom_shape + (3,) * self.order, dtype=np.float64)
        reduced = self.basis @ (self.nullspace @ coefficients)
        tensor.reshape(-1, self.cart_size)[self.cluster_codes] = reduced.reshape(-1, self.cart_size)
        return tensor


def least_squares(design, target, nullspace):
    parameter_count = nullspace.shape[1]
    if parameter_count == 0:
        return np.empty(0, dtype=np.float64)
    if design.shape[0] >= max(128, 4 * parameter_count):
        normal = linalg.blas.dsyrk(1.0, design, trans=1, lower=1)
        normal += np.tril(normal, -1).T
        normal = nullspace.T @ normal @ nullspace
        eigenvalues = linalg.eigvalsh(normal, check_finite=False)
        if eigenvalues[0] > eigenvalues[-1] * 2e-9:
            right_hand = nullspace.T @ (design.T @ target.reshape(-1))
            coefficients = linalg.cho_solve(
                linalg.cho_factor(normal, check_finite=False),
                right_hand, check_finite=False
            )
            report("normal least squares", design.shape, "rank", parameter_count)
            return coefficients
    design = design @ nullspace
    coefficients, residuals, rank, singular = linalg.lstsq(
        design, target.reshape(-1), cond=1e-11, check_finite=False,
        overwrite_a=True, lapack_driver="gelsd"
    )
    report("least squares", design.shape, "rank", rank)
    return coefficients


def fold_harmonic(tensor, fold, atom_count):
    folded = np.zeros((len(tensor), atom_count, 3, 3))
    for representative in range(len(tensor)):
        np.add.at(folded[representative], fold[representative], tensor[representative])
    return folded


def harmonic_forces(tensor, displacements, row_map, compact_map):
    expanded = tensor[row_map[:, None], compact_map]
    return -np.einsum("ijab,sjb->sia", expanded, displacements, optimize=True)


def solve(data):
    started = time.monotonic()
    harmonic_basis = TensorBasis(data, 2, 2)
    if int(data["fit_mode"]) == 0:
        cubic_basis = TensorBasis(data, 3, 3)
        harmonic_design = harmonic_basis.design(data["u3"], symmetry_only=True)
        cubic_design = cubic_basis.design(data["u3"], symmetry_only=True)
        report("design seconds", time.monotonic() - started)
        design = np.concatenate((harmonic_design, cubic_design), axis=1)
        del harmonic_design, cubic_design
        nullspace = linalg.block_diag(harmonic_basis.nullspace, cubic_basis.nullspace)
        coefficients = least_squares(design, data["f3"], nullspace)
        split = harmonic_basis.parameter_count
        fc2 = harmonic_basis.tensor(coefficients[:split])
        fc3 = cubic_basis.tensor(coefficients[split:])
    else:
        design = harmonic_basis.design(data["u2"], symmetry_only=True)
        coefficients = least_squares(design, data["f2"], harmonic_basis.nullspace)
        fc2 = harmonic_basis.tensor(coefficients)
        del design
        folded = fold_harmonic(fc2, data["fold2to3"], len(data["numbers3"]))
        residual = data["f3"] - harmonic_forces(
            folded, data["u3"], data["s2p3"], data["compact_map3"]
        )
        cubic_basis = TensorBasis(data, 3, 3)
        design = cubic_basis.design(data["u3"], symmetry_only=True)
        coefficients = least_squares(design, residual, cubic_basis.nullspace)
        fc3 = cubic_basis.tensor(coefficients)
    report("total seconds", time.monotonic() - started)
    return {"fc2": fc2, "fc3": fc3}


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: python solve.py INPUT.npz OUTPUT.npz")
    with np.load(sys.argv[1], allow_pickle=False) as data:
        result = solve(data)
    with open(sys.argv[2], "wb") as output:
        np.savez_compressed(output, **result)


if __name__ == "__main__":
    main()
