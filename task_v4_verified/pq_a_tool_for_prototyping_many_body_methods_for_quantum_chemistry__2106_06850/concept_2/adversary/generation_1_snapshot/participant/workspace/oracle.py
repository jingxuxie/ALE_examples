"""Small fixed-particle determinant-space CCSD, lambda, RDM and EOM oracle."""

import itertools
import math
from dataclasses import dataclass

import numpy as np
from scipy.linalg import eigh, eigvals, solve
from scipy.optimize import root


def act(bits, annihilate, create):
    phase = 1
    for orbital in annihilate:
        if not bits & (1 << orbital):
            return None
        phase *= (-1) ** ((bits & ((1 << orbital) - 1)).bit_count())
        bits ^= 1 << orbital
    for orbital in create:
        if bits & (1 << orbital):
            return None
        phase *= (-1) ** ((bits & ((1 << orbital) - 1)).bit_count())
        bits ^= 1 << orbital
    return bits, phase


@dataclass
class CCResult:
    amplitudes: np.ndarray
    energy: float
    residual: float
    jacobian: np.ndarray
    hbar: np.ndarray
    right: np.ndarray
    inverse: np.ndarray
    converged: bool


class DeterminantCC:
    def __init__(self, orbitals=6, electrons=3):
        self.orbitals = orbitals
        self.electrons = electrons
        self.bits = sorted(sum(1 << orbital for orbital in occupied)
                           for occupied in itertools.combinations(range(orbitals), electrons))
        self.index = {bits: index for index, bits in enumerate(self.bits)}
        self.size = len(self.bits)
        self.reference = self.index[(1 << electrons) - 1]
        self.pairs = list(itertools.combinations(range(orbitals), 2))
        self.identity = np.eye(self.size)
        self.ref = self.identity[:, self.reference]
        self.one = np.array([[self.operator((right,), (left,))
                              for right in range(orbitals)] for left in range(orbitals)])
        self.two = np.array([[self.operator(annihilators, creators[::-1])
                              for annihilators in self.pairs] for creators in self.pairs])
        self.labels = []
        generators = []
        targets = []
        self.ranks = []
        for rank in (1, 2):
            for holes in itertools.combinations(range(electrons), rank):
                for particles in itertools.combinations(range(electrons, orbitals), rank):
                    generator = self.operator(holes, particles[::-1])
                    target = int(np.argmax(np.abs(generator[:, self.reference])))
                    generator *= generator[target, self.reference]
                    generators.append(generator)
                    targets.append(target)
                    self.labels.append({"holes": list(holes), "particles": list(particles)})
                    self.ranks.append(rank)
        self.generators = np.array(generators)
        self.targets = np.array(targets)
        self.count = len(targets)
        self.single_targets = self.targets[np.array(self.ranks) == 1]
        self.singles = self.generators[np.array(self.ranks) == 1]
        self.two_flat = self.two.reshape(-1, self.size * self.size)
        self.one_flat = self.one.reshape(-1, self.size * self.size)
        self.generator_flat = self.generators.reshape(self.count, -1)

    def operator(self, annihilators, creators):
        matrix = np.zeros((self.size, self.size))
        for column, bits in enumerate(self.bits):
            result = act(bits, annihilators, creators)
            if result is not None:
                output, phase = result
                matrix[self.index[output], column] = phase
        return matrix

    def integrals(self, orbital_energies, pair_matrix):
        pair_matrix = np.asarray(pair_matrix, dtype=float)
        tensor = np.zeros((self.orbitals,) * 4)
        for row, (first, second) in enumerate(self.pairs):
            for column, (third, fourth) in enumerate(self.pairs):
                value = pair_matrix[row, column]
                tensor[first, second, third, fourth] = value
                tensor[second, first, third, fourth] = -value
                tensor[first, second, fourth, third] = -value
                tensor[second, first, fourth, third] = value
        contraction = sum(tensor[:, occupied, :, occupied]
                          for occupied in range(self.electrons))
        one_body = np.diag(orbital_energies) - contraction
        return one_body, tensor

    def hamiltonian(self, orbital_energies, pair_matrix):
        one_body, tensor = self.integrals(orbital_energies, pair_matrix)
        matrix = (one_body.ravel() @ self.one_flat
                  + np.asarray(pair_matrix).ravel() @ self.two_flat).reshape(self.size, self.size)
        return matrix, one_body, tensor

    def exponentials(self, amplitudes):
        cluster = (np.asarray(amplitudes) @ self.generator_flat).reshape(self.size, self.size)
        positive = self.identity.copy()
        negative = self.identity.copy()
        term = self.identity.copy()
        for degree in range(1, self.electrons + 1):
            term = term @ cluster / degree
            positive += term
            negative += (-1) ** degree * term
        return positive, negative

    def equations(self, hamiltonian, amplitudes):
        positive, negative = self.exponentials(amplitudes)
        transformed = negative @ hamiltonian @ positive
        column = transformed[:, self.reference]
        residual = column[self.targets]
        commutator_column = np.einsum("kij,j->ik", self.generators, column)
        jacobian = transformed[np.ix_(self.targets, self.targets)] - commutator_column[self.targets]
        return residual, jacobian, transformed, positive, negative

    def solve(self, hamiltonian, initial=None, tolerance=1e-10, max_evaluations=180):
        initial = np.zeros(self.count) if initial is None else np.asarray(initial, dtype=float)

        def combined(amplitudes):
            residual, jacobian, _, _, _ = self.equations(hamiltonian, amplitudes)
            return residual, jacobian

        answer = root(combined, initial, jac=True, method="hybr",
                      options={"xtol": tolerance, "maxfev": max_evaluations})
        residual, jacobian, transformed, positive, negative = self.equations(hamiltonian, answer.x)
        norm = float(np.max(np.abs(residual)))
        return CCResult(answer.x, float(transformed[self.reference, self.reference]), norm,
                        jacobian, transformed, positive[:, self.reference], negative,
                        bool(np.isfinite(norm) and norm < 1e-8))

    def continuation(self, orbital_energies, pair_matrix, steps=12):
        amplitudes = np.zeros(self.count)
        history = []
        result = None
        for coupling in np.linspace(0, 1, steps + 1):
            hamiltonian, _, _ = self.hamiltonian(orbital_energies, coupling * np.asarray(pair_matrix))
            result = self.solve(hamiltonian, amplitudes)
            if not result.converged:
                raise ValueError("CCSD continuation failed")
            amplitudes = result.amplitudes
            exact_energy, exact_vectors = eigh(hamiltonian)
            overlap = float((exact_vectors[:, 0] @ result.right) ** 2 / (result.right @ result.right))
            history.append({"coupling": float(coupling), "residual": result.residual,
                            "overlap": overlap, "gap": float(exact_energy[1] - exact_energy[0])})
        return result, history

    def lambda_state(self, result):
        gradient = result.hbar[self.reference, self.targets]
        multipliers = solve(result.jacobian.T, -gradient, assume_a="gen")
        left_row = self.ref.copy()
        left_row[self.targets] = multipliers
        left = left_row @ result.inverse
        stationarity = float(np.max(np.abs(gradient + result.jacobian.T @ multipliers)))
        return multipliers, left, stationarity

    def rdm(self, left, right):
        return np.einsum("i,pqij,j->pq", left, self.one, right)

    def hf_stability(self, hamiltonian):
        reference_energy = float(hamiltonian[self.reference, self.reference])
        single_block = hamiltonian[np.ix_(self.single_targets, self.single_targets)]
        tangent = single_block - reference_energy * np.eye(len(self.single_targets))
        double_tangent = np.empty_like(tangent)
        reference_column = hamiltonian[:, self.reference]
        for row, left_generator in enumerate(self.singles):
            for column, right_generator in enumerate(self.singles):
                double_tangent[row, column] = reference_column @ (left_generator @ right_generator @ self.ref)
        real_hessian = 2 * (tangent + double_tangent)
        imaginary_hessian = 2 * (tangent - double_tangent)
        return real_hessian, imaginary_hessian

    def diagnostics(self, hamiltonian, result, include_rdm=True):
        exact_energies, exact_vectors = eigh(hamiltonian)
        norm = result.right @ result.right
        exact_overlap = float((exact_vectors[:, 0] @ result.right) ** 2 / norm)
        eom_values = eigvals(result.jacobian)
        ordering = np.lexsort((eom_values.imag, eom_values.real))
        eom_values = eom_values[ordering]
        real_hessian, imaginary_hessian = self.hf_stability(hamiltonian)
        diagnostics = {
            "cc_energy": result.energy,
            "fci_energy": float(exact_energies[0]),
            "energy_error": float(abs(result.energy - exact_energies[0])),
            "fci_gap": float(exact_energies[1] - exact_energies[0]),
            "ground_overlap": exact_overlap,
            "reference_weight": float(exact_vectors[self.reference, 0] ** 2),
            "cc_reference_weight": float(1 / norm),
            "cc_residual": result.residual,
            "amplitude_norm": float(np.linalg.norm(result.amplitudes)),
            "jacobian_condition": float(np.linalg.cond(result.jacobian)),
            "hf_real_min": float(eigh(real_hessian, eigvals_only=True)[0]),
            "hf_imaginary_min": float(eigh(imaginary_hessian, eigvals_only=True)[0]),
            "eom_real": eom_values.real.tolist(),
            "eom_imag": eom_values.imag.tolist(),
            "low_pair_imag": float(max(abs(eom_values[:2].imag))),
            "max_eom_imag": float(max(abs(eom_values.imag))),
            "fci_excitations": (exact_energies[1:] - exact_energies[0]).tolist(),
        }
        if include_rdm:
            multipliers, left, stationarity = self.lambda_state(result)
            density = self.rdm(left, result.right)
            occupations = eigh((density + density.T) / 2, eigvals_only=True)
            exact_density = self.rdm(exact_vectors[:, 0], exact_vectors[:, 0])
            diagnostics.update({"lambda_residual": stationarity,
                                "lambda_norm": float(np.linalg.norm(multipliers)),
                                "biorthogonal_norm": float(left @ result.right),
                                "rdm_trace": float(np.trace(density)),
                                "rdm_antisymmetry": float(np.max(np.abs(density - density.T))),
                                "occupations": occupations.tolist(),
                                "occupation_violation": float(max(0, -occupations[0], occupations[-1] - 1)),
                                "exact_occupations": eigh(exact_density, eigvals_only=True).tolist()})
        return diagnostics


def random_pair_matrix(rng, scale=0.25, orbitals=6):
    size = math.comb(orbitals, 2)
    matrix = rng.normal(size=(size, size))
    return scale * (matrix + matrix.T) / np.sqrt(2)
