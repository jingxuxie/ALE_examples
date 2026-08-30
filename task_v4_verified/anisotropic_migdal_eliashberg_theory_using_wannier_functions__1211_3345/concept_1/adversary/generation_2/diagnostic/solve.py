"""Private subprocess-only diagnostic of the actual archived v3 discretizations."""

import argparse

import numpy as np
from scipy.sparse.linalg import LinearOperator, eigs
from v3 import Model, ReducedModel


def spectrum(model):
    def product(vector):
        delta = vector.reshape(model.shape)
        ratio = delta / model.frequencies
        pairing = model.convolve(ratio, 1)
        pairing -= 2 * (model.weighted_coulomb @ model.sum_ratio(ratio))[:, None]
        return (np.pi * model.temperature * pairing / model.normal_z).ravel()

    size = int(np.prod(model.shape))
    operator = LinearOperator((size, size), matvec=product, dtype=float)
    values = eigs(operator, k=3, which="LR", ncv=20, tol=2e-12, maxiter=300,
                  v0=np.ones(size), return_eigenvectors=False)
    assert np.max(np.abs(values.imag)) < 1e-8
    return np.sort(values.real)[::-1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    with np.load(arguments.input, allow_pickle=False) as archive:
        instance = {name: archive[name] for name in archive.files}
    full = Model(instance)
    reduced = ReducedModel(full)
    output = np.zeros(full.shape)
    output[0, :3] = spectrum(full)
    output[1, :3] = spectrum(reduced)
    output[2, 0] = reduced.n_freq
    np.savez(arguments.output, delta=output, z=np.ones(full.shape))


if __name__ == "__main__":
    main()
