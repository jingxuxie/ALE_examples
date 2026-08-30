"""Private verifier using full-Fock operators and scipy matrix exponentials."""

import itertools

import numpy as np
from scipy.linalg import eigh, eigvals, expm, solve
from scipy.optimize import root


class IndependentSystem:
    def __init__(self, electrons=3):
        self.electrons = electrons
        self.orbitals = 6
        self.pairs = list(itertools.combinations(range(6), 2))
        self.sector = [state for state in range(64) if bin(state).count("1") == electrons]
        self.reference = self.sector.index(2 ** electrons - 1)
        self.size = len(self.sector)
        self.ref = np.eye(self.size)[:, self.reference]
        annihilators = []
        for orbital in range(6):
            operator = np.zeros((64, 64))
            for state in range(64):
                if (state // 2 ** orbital) % 2:
                    operator[state - 2 ** orbital, state] = (-1) ** bin(state % 2 ** orbital).count("1")
            annihilators.append(operator)
        self.full_annihilators = annihilators
        self.one = np.array([[self.restrict(annihilators[left].T @ annihilators[right])
                              for right in range(6)] for left in range(6)])
        pair_annihilators = [annihilators[second] @ annihilators[first] for first, second in self.pairs]
        self.two = np.array([[self.restrict(left.T @ right) for right in pair_annihilators]
                             for left in pair_annihilators])
        self.generators = []
        self.targets = []
        for rank in (1, 2):
            for holes in itertools.combinations(range(electrons), rank):
                for particles in itertools.combinations(range(electrons, 6), rank):
                    operator = np.eye(64)
                    for orbital in holes:
                        operator = annihilators[orbital] @ operator
                    for orbital in particles[::-1]:
                        operator = annihilators[orbital].T @ operator
                    operator = self.restrict(operator)
                    target = int(np.flatnonzero(operator[:, self.reference])[0])
                    operator /= operator[target, self.reference]
                    self.generators.append(operator)
                    self.targets.append(target)
        self.generators = np.array(self.generators)
        self.targets = np.array(self.targets)
        self.count = len(self.targets)
        self.single_count = electrons * (6 - electrons)

    def restrict(self, matrix):
        return matrix[np.ix_(self.sector, self.sector)]

    def integral_element(self, interaction, first, second, third, fourth):
        if first == second or third == fourth:
            return 0.0
        left = tuple(sorted((first, second)))
        right = tuple(sorted((third, fourth)))
        sign = (1 if first < second else -1) * (1 if third < fourth else -1)
        return sign * interaction[self.pairs.index(left), self.pairs.index(right)]

    def build(self, energies, interaction):
        contraction = np.array([[sum(self.integral_element(interaction, left, occupied, right, occupied)
                                    for occupied in range(self.electrons))
                                 for right in range(6)] for left in range(6)])
        one_body = np.diag(energies) - contraction
        hamiltonian = np.einsum("pq,pqij->ij", one_body, self.one)
        hamiltonian += np.einsum("pq,pqij->ij", interaction, self.two)
        return hamiltonian, one_body, one_body + contraction

    def equations(self, hamiltonian, amplitudes):
        cluster = np.einsum("k,kij->ij", amplitudes, self.generators)
        positive = expm(cluster)
        negative = expm(-cluster)
        hbar = negative @ hamiltonian @ positive
        commutators = np.array([hbar @ operator - operator @ hbar for operator in self.generators])
        jacobian = commutators[:, self.targets, self.reference].T
        residual = hbar[self.targets, self.reference]
        return residual, jacobian, hbar, positive, negative

    def solve(self, hamiltonian, initial):
        def function(amplitudes):
            values = self.equations(hamiltonian, amplitudes)
            return values[0], values[1]

        answer = root(function, initial, jac=True, method="hybr", options={"xtol": 2e-11, "maxfev": 250})
        residual = self.equations(hamiltonian, answer.x)[0]
        if not np.all(np.isfinite(answer.x)) or np.max(np.abs(residual)) > 2e-9:
            raise ValueError("independent continuation did not converge")
        return answer.x

    def stability(self, hamiltonian):
        hessians = []
        for imaginary in (False, True):
            if imaginary:
                rotations = [1j * (operator + operator.T) for operator in self.generators[:self.single_count]]
            else:
                rotations = [operator - operator.T for operator in self.generators[:self.single_count]]
            tangent = [operator @ self.ref for operator in rotations]
            hessian = np.empty((self.single_count, self.single_count))
            for row, left in enumerate(rotations):
                for column, right in enumerate(rotations):
                    second = (left @ right + right @ left) @ self.ref / 2
                    hessian[row, column] = 2 * np.real(tangent[row].conj() @ hamiltonian @ tangent[column]
                                                      + self.ref @ hamiltonian @ second)
            hessians.append(hessian)
        return hessians

    def diagnose(self, energies, interaction, amplitudes):
        hamiltonian, one_body, fock = self.build(energies, interaction)
        residual, jacobian, hbar, positive, negative = self.equations(hamiltonian, amplitudes)
        energy = float(hbar[self.reference, self.reference])
        gradient = np.array([(hbar @ operator - operator @ hbar)[self.reference, self.reference]
                             for operator in self.generators])
        multipliers = solve(jacobian.T, -gradient)
        bra = self.ref.copy()
        bra[self.targets] = multipliers
        left = bra @ negative
        right = positive @ self.ref
        density = np.einsum("i,pqij,j->pq", left, self.one, right)
        occupations = eigh((density + density.T) / 2, eigvals_only=True)
        exact_energies, exact_vectors = eigh(hamiltonian)
        exact_density = np.einsum("i,pqij,j->pq", exact_vectors[:, 0], self.one, exact_vectors[:, 0])
        exact_occupations = eigh(exact_density, eigvals_only=True)
        exact_gap = float(exact_energies[1] - exact_energies[0])
        right_norm = right @ right
        normalized_density = np.einsum("i,pqij,j->pq", right, self.one, right) / right_norm
        normalized_occupations = eigh(normalized_density, eigvals_only=True)
        populations, real_orbitals = eigh((density + density.T) / 2)
        worst_index = 0 if -populations[0] >= populations[-1] - 1 else -1
        eom = eigvals(jacobian)
        ordering = np.lexsort((eom.imag, eom.real))
        eom = eom[ordering]
        hessians = self.stability(hamiltonian)
        return {
            "cc_energy": energy,
            "fci_energy": float(exact_energies[0]),
            "energy_error": float(abs(energy - exact_energies[0])),
            "fci_gap": exact_gap,
            "ground_overlap": float((exact_vectors[:, 0] @ right) ** 2 / right_norm),
            "reference_weight": float(exact_vectors[self.reference, 0] ** 2),
            "cc_reference_weight": float(1 / right_norm),
            "cc_residual": float(np.max(np.abs(residual))),
            "lambda_residual": float(np.max(np.abs(gradient + jacobian.T @ multipliers))),
            "amplitude_norm": float(np.linalg.norm(amplitudes)),
            "lambda_norm": float(np.linalg.norm(multipliers)),
            "jacobian_condition": float(np.linalg.cond(jacobian)),
            "hf_real_min": float(eigh(hessians[0], eigvals_only=True)[0]),
            "hf_imaginary_min": float(eigh(hessians[1], eigvals_only=True)[0]),
            "hf_gradient": float(np.max(np.abs(2 * hamiltonian[self.targets[:self.single_count], self.reference]))),
            "fock_error": float(np.max(np.abs(fock - np.diag(energies)))),
            "hermiticity_error": float(np.max(np.abs(hamiltonian - hamiltonian.T))),
            "eom_real": eom.real.tolist(),
            "eom_imag": eom.imag.tolist(),
            "low_pair_imag": float(max(abs(eom[:2].imag))),
            "max_eom_imag": float(max(abs(eom.imag))),
            "fci_excitations": (exact_energies[1:] - exact_energies[0]).tolist(),
            "biorthogonal_norm": float(left @ right),
            "rdm_trace": float(np.trace(density)),
            "rdm_antisymmetry": float(np.max(np.abs(density - density.T))),
            "rdm_dad": float(np.linalg.norm(density - density.T, ord="fro") / np.sqrt(self.electrons)),
            "occupations": occupations.tolist(),
            "occupation_violation": float(max(0, -occupations[0], occupations[-1] - 1)),
            "worst_orbital": real_orbitals[:, worst_index].tolist(),
            "worst_orbital_population": float(populations[worst_index]),
            "right_state_occupations": normalized_occupations.tolist(),
            "right_state_rdm_positivity_violation": float(max(0, -normalized_occupations[0], normalized_occupations[-1] - 1)),
            "exact_occupations": exact_occupations.tolist(),
            "exact_rdm_trace_error": float(abs(np.trace(exact_density) - self.electrons)),
            "exact_rdm_hermiticity_error": float(np.max(np.abs(exact_density - exact_density.T))),
            "exact_rdm_positivity_violation": float(max(0, -exact_occupations[0], exact_occupations[-1] - 1)),
        }

    def continuation(self, energies, interaction, steps=64):
        amplitudes = np.zeros(self.count)
        history = []
        base_hamiltonian, _, _ = self.build(energies, np.zeros_like(interaction))
        final_hamiltonian, _, _ = self.build(energies, interaction)
        for coupling in np.linspace(0, 1, steps + 1):
            hamiltonian = base_hamiltonian + coupling * (final_hamiltonian - base_hamiltonian)
            previous = amplitudes
            amplitudes = self.solve(hamiltonian, amplitudes)
            residual, jacobian, _, positive, _ = self.equations(hamiltonian, amplitudes)
            exact_energies, exact_vectors = eigh(hamiltonian)
            right = positive @ self.ref
            history.append({"coupling": float(coupling), "residual": float(max(abs(residual))),
                            "gap": float(exact_energies[1] - exact_energies[0]),
                            "overlap": float((exact_vectors[:, 0] @ right) ** 2 / (right @ right)),
                            "amplitude_step": float(np.linalg.norm(amplitudes - previous)),
                            "jacobian_singular_min": float(np.linalg.svd(jacobian, compute_uv=False)[-1])})
        return amplitudes, history
