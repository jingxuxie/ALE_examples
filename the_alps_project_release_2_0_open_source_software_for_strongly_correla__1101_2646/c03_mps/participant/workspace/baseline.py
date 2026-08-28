import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh


def local_operators(case):
    if case["family"] == "bose_hubbard":
        charges = np.arange(case["nmax"] + 1, dtype=float)
        annihilation = np.diag(np.sqrt(charges[1:]), 1)
        number = np.diag(charges)
        return {
            "N": number,
            "B": annihilation,
            "Bd": annihilation.T,
            "NNm1": number @ (number - np.eye(len(charges))),
        }, charges
    spin = case["spin"]
    charges = np.arange(-spin, spin + 1)
    raising = np.diag(np.sqrt(spin * (spin + 1) - charges[:-1] * (charges[:-1] + 1)), -1)
    return {
        "Sz": np.diag(charges),
        "Sp": raising,
        "Sm": raising.T,
        "Sx": (raising + raising.T) / 2,
        "Sz2": np.diag(charges ** 2),
        "StringZ": np.diag(np.cos(np.pi * charges)),
    }, charges


def embed(length, dimension, factors):
    result = sparse.csr_matrix([[1.0]])
    identity = sparse.eye(dimension, format="csr")
    for site in range(length):
        result = sparse.kron(result, factors.get(site, identity), format="csr")
    return result


def product_configuration(case, sector):
    length = case["length"]
    if case["family"] == "bose_hubbard":
        values = np.ones(length)
        delta = int(sector - length)
        if delta > 0:
            ordering = np.argsort(np.asarray(case["interaction"]) + case["potential"])
            for site in ordering[:delta]:
                values[site] += 1
        elif delta < 0:
            for site in np.argsort(case["potential"])[::-1][:(-delta)]:
                values[site] -= 1
        return values
    spin = case["spin"]
    if case["family"] == "spinhalf_ladder":
        values = np.array([spin * (-1) ** (site // 2 + site % 2) for site in range(length)])
    else:
        values = np.array([spin * (-1) ** site for site in range(length)])
    remaining = float(sector - values.sum())
    for site in range(length):
        change = min(spin - values[site], remaining) if remaining > 0 else max(-spin - values[site], remaining)
        values[site] += change
        remaining -= change
        if abs(remaining) < 1e-12:
            break
    if abs(remaining) > 1e-12:
        raise ValueError("unreachable sector")
    return values


def product_energy(case, values):
    if case["family"] == "bose_hubbard":
        return float(np.dot(np.asarray(case["interaction"]) / 2, values * (values - 1)) + np.dot(case["potential"], values))
    energy = np.dot(case["single_ion"], values ** 2) - np.dot(case["field"], values)
    for bond in case["bonds"]:
        left, right = bond["sites"]
        energy += bond["jz"] * values[left] * values[right]
    return float(energy)


def product_result(case):
    bosons = case["family"] == "bose_hubbard"
    sector = case["particles"] if bosons else case["ground_sector"]
    values = product_configuration(case, sector)
    energy = product_energy(case, values)
    if bosons:
        gap = sum(product_energy(case, product_configuration(case, sector + shift)) for shift in [-1, 1]) - 2 * energy
    else:
        gap = product_energy(case, product_configuration(case, case["excited_sector"])) - energy
    correlations = []
    for observable in case["observables"]:
        left, right = observable["sites"]
        kind = observable["kind"]
        if kind == "zz":
            value = values[left] * values[right]
        elif kind == "string":
            value = -values[left] * values[right] * np.prod(np.cos(np.pi * values[left + 1:right]))
        else:
            value = 0.0
        correlations.append(float(value))
    return {"energy": energy, "gap": float(gap), "correlations": correlations, "method": "product"}


def exact_result(case, maximum_dimension=80000):
    operators, charges = local_operators(case)
    dimension = len(charges)
    length = case["length"]
    full_dimension = dimension ** length
    if full_dimension > maximum_dimension:
        raise ValueError("full product Hilbert space exceeds the exact baseline limit")
    hamiltonian = sparse.csr_matrix((full_dimension, full_dimension))
    bosons = case["family"] == "bose_hubbard"
    for site in range(length):
        if bosons:
            local = case["interaction"][site] / 2 * operators["NNm1"] + case["potential"][site] * operators["N"]
        else:
            local = case["single_ion"][site] * operators["Sz2"] - case["field"][site] * operators["Sz"]
        if np.any(local):
            hamiltonian += embed(length, dimension, {site: local})
    for bond in case["bonds"]:
        left, right = bond["sites"]
        terms = [("Bd", "B", -bond["hopping"]), ("B", "Bd", -bond["hopping"])] if bosons else [
            ("Sp", "Sm", bond["jxy"] / 2),
            ("Sm", "Sp", bond["jxy"] / 2),
            ("Sz", "Sz", bond["jz"]),
        ]
        for left_op, right_op, coefficient in terms:
            hamiltonian += coefficient * embed(length, dimension, {left: operators[left_op], right: operators[right_op]})
    basis_digits = np.indices([dimension] * length).reshape(length, -1)
    total_charge = charges[basis_digits].sum(axis=0)

    def ground_in_sector(sector):
        indices = np.flatnonzero(np.isclose(total_charge, sector, atol=1e-12, rtol=0))
        block = hamiltonian[indices][:, indices]
        if len(indices) <= 48:
            energies, states = np.linalg.eigh(block.toarray())
            energy, state = energies[0], states[:, 0]
        else:
            initial = np.random.default_rng(9281).normal(size=len(indices))
            energies, states = eigsh(block, k=1, which="SA", tol=1e-12, maxiter=10000, v0=initial)
            energy, state = energies[0], states[:, 0]
        residual = float(np.linalg.norm(block @ state - energy * state))
        full_state = np.zeros(full_dimension)
        full_state[indices] = state
        return float(energy), full_state, residual

    sector = case["particles"] if bosons else case["ground_sector"]
    energy, state, residual = ground_in_sector(sector)
    sector_residuals = [residual]
    if bosons:
        nearby = [ground_in_sector(sector + shift) for shift in [-1, 1]]
        gap = sum(result[0] for result in nearby) - 2 * energy
        sector_residuals.extend(result[2] for result in nearby)
    else:
        excited_energy, _, excited_residual = ground_in_sector(case["excited_sector"])
        gap = excited_energy - energy
        sector_residuals.append(excited_residual)

    def expectation(factors):
        return float(np.real(np.vdot(state, embed(length, dimension, factors) @ state)))

    correlations = []
    for observable in case["observables"]:
        left, right = observable["sites"]
        kind = observable["kind"]
        if kind in ["zz", "xx"]:
            operator = operators["Sz" if kind == "zz" else "Sx"]
            value = expectation({left: operator, right: operator})
        elif kind == "string":
            factors = {left: operators["Sz"], right: operators["Sz"]}
            factors.update({site: operators["StringZ"] for site in range(left + 1, right)})
            value = -expectation(factors)
        elif kind == "one_body":
            value = expectation({left: operators["Bd"], right: operators["B"]})
        elif kind == "density_connected":
            value = expectation({left: operators["N"], right: operators["N"]})
            value -= expectation({left: operators["N"]}) * expectation({right: operators["N"]})
        else:
            raise ValueError(kind)
        correlations.append(value)
    return {"energy": energy, "gap": float(gap), "correlations": correlations, "method": "exact", "max_residual": max(sector_residuals)}


def solve(case):
    dimension = case["nmax"] + 1 if case["family"] == "bose_hubbard" else int(2 * case["spin"] + 1)
    return exact_result(case) if dimension ** case["length"] <= 80000 else product_result(case)
