"""Author-only transport oracle using official Kwant, not a custom solver."""

import os
import sys
from pathlib import Path
from time import perf_counter

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))

import kwant
import numpy as np
import scipy.linalg


def read_case(path):
    with np.load(path, allow_pickle=False) as archive:
        return {name: archive[name] for name in archive.files}


def hopping_dictionary(case):
    return {tuple(vector): matrix for vector, matrix in zip(case["h_R"], case["h_matrices"])}


def lead_blocks(case, lead_index):
    orbitals = case["h_matrices"].shape[1]
    cells = case[f"lead_cells_{lead_index}"]
    period = case[f"lead_period_{lead_index}"]
    hoppings = hopping_dictionary(case)
    dimension = len(cells) * orbitals
    cell_hamiltonian = np.zeros((dimension, dimension), dtype=complex)
    inward_hopping = np.zeros_like(cell_hamiltonian)
    for row_index, row_cell in enumerate(cells):
        row_slice = slice(row_index * orbitals, (row_index + 1) * orbitals)
        for column_index, column_cell in enumerate(cells):
            column_slice = slice(column_index * orbitals, (column_index + 1) * orbitals)
            matrix = hoppings.get(tuple(column_cell - row_cell))
            if matrix is not None:
                cell_hamiltonian[row_slice, column_slice] = matrix
            matrix = hoppings.get(tuple(column_cell - row_cell - period))
            if matrix is not None:
                inward_hopping[row_slice, column_slice] = matrix
    cell_hamiltonian += float(case[f"lead_shift_{lead_index}"]) * np.eye(dimension)
    return cell_hamiltonian, inward_hopping


class OfficialModes:
    def __init__(self, cell_hamiltonian, inward_hopping):
        self.cell_hamiltonian = cell_hamiltonian
        self.inward_hopping = inward_hopping
        self.cache = {}

    def __call__(self, energy, args=(), *, params=None):
        energy = float(energy)
        if energy not in self.cache:
            shifted = self.cell_hamiltonian - energy * np.eye(len(self.cell_hamiltonian))
            self.cache[energy] = kwant.physics.modes(
                shifted, self.inward_hopping
            )
        return self.cache[energy]


def build_system(case):
    orbitals = case["h_matrices"].shape[1]
    lattice = kwant.lattice.general(case["cell"], norbs=orbitals)
    builder = kwant.Builder()
    hoppings = hopping_dictionary(case)
    cells = {tuple(cell) for cell in case["cells"]}
    for cell, potential in zip(case["cells"], case["potential"]):
        builder[lattice(*cell)] = hoppings[(0, 0, 0)] + np.diag(potential)
    forward = [(np.asarray(vector), matrix) for vector, matrix in hoppings.items() if vector > (0, 0, 0)]
    for cell in case["cells"]:
        for vector, matrix in forward:
            target = tuple(cell + vector)
            if target in cells:
                builder[lattice(*cell), lattice(*target)] = matrix
    modes = []
    blocks = []
    for lead_index in range(int(case["lead_count"])):
        cell_hamiltonian, inward_hopping = lead_blocks(case, lead_index)
        mode_function = OfficialModes(cell_hamiltonian, inward_hopping)
        interface = [lattice(*cell) for cell in case[f"lead_cells_{lead_index}"]]
        builder.leads.append(kwant.builder.ModesLead(mode_function, interface, parameters=[]))
        modes.append(mode_function)
        blocks.append((cell_hamiltonian, inward_hopping))
    return builder.finalized(), modes, blocks


def gamma_square_root(selfenergy):
    broadening = 1j * (selfenergy - selfenergy.conj().T)
    eigenvalues, eigenvectors = scipy.linalg.eigh(broadening)
    if eigenvalues.min() < -1e-7:
        raise ValueError("Noncausal official lead selfenergy")
    return (eigenvectors * np.sqrt(np.maximum(eigenvalues, 0))) @ eigenvectors.conj().T


def solve(case, backend="smatrix"):
    started = perf_counter()
    system, mode_functions, blocks = build_system(case)
    lead_count = len(mode_functions)
    dimensions = [len(block[0]) for block in blocks]
    energy_count = len(case["energies"])
    result = {
        "mode_counts": np.zeros((energy_count, lead_count), dtype=np.int64),
        "transmission": np.zeros((energy_count, lead_count, lead_count)),
        "channels": np.zeros((energy_count, lead_count, lead_count, max(dimensions))),
        "partition_noise": np.zeros((energy_count, lead_count, lead_count)),
        "lb_conductance": np.zeros((energy_count, lead_count, lead_count)),
    }
    for lead_index, dimension in enumerate(dimensions):
        result[f"sigma_{lead_index}"] = np.zeros((energy_count, dimension, dimension), dtype=complex)
    unitarity_error = 0.0
    noise_check_error = 0.0
    surface_residual = 0.0
    for energy_index, energy in enumerate(case["energies"]):
        selfenergies = []
        for lead_index, mode_function in enumerate(mode_functions):
            propagating, stabilized = mode_function(energy)
            result["mode_counts"][energy_index, lead_index] = len(propagating.velocities) // 2
            selfenergy = stabilized.selfenergy()
            gamma_square_root(selfenergy)
            cell_hamiltonian, inward_hopping = blocks[lead_index]
            surface_action = scipy.linalg.solve(
                energy * np.eye(len(cell_hamiltonian)) - cell_hamiltonian - selfenergy,
                inward_hopping, assume_a="gen"
            )
            residual = inward_hopping.conj().T @ surface_action - selfenergy
            surface_residual = max(surface_residual, float(np.linalg.norm(residual) / (1 + np.linalg.norm(selfenergy))))
            selfenergies.append(selfenergy)
            result[f"sigma_{lead_index}"][energy_index] = selfenergy
        if backend == "smatrix":
            response = kwant.smatrix(system, float(energy))
            if response.data.size:
                unitarity_error = max(unitarity_error, float(np.linalg.norm(
                    response.data.conj().T @ response.data - np.eye(response.data.shape[1]), ord=np.inf
                )))
        elif backend == "greens":
            response = kwant.greens_function(system, float(energy))
            roots = [gamma_square_root(selfenergy) for selfenergy in selfenergies]
        else:
            raise ValueError(backend)
        for outgoing in range(lead_count):
            for incoming in range(lead_count):
                result["transmission"][energy_index, outgoing, incoming] = response.transmission(outgoing, incoming)
                if outgoing == incoming:
                    continue
                if backend == "smatrix":
                    amplitude = response.submatrix(outgoing, incoming)
                else:
                    amplitude = roots[outgoing] @ response.submatrix(outgoing, incoming) @ roots[incoming]
                eigenvalues = scipy.linalg.svdvals(amplitude) ** 2
                retained = min(result["mode_counts"][energy_index, outgoing], result["mode_counts"][energy_index, incoming])
                eigenvalues = eigenvalues[:retained]
                result["channels"][energy_index, outgoing, incoming, :retained] = eigenvalues
                result["partition_noise"][energy_index, outgoing, incoming] = np.sum(eigenvalues * (1 - eigenvalues))
        result["lb_conductance"][energy_index] = response.conductance_matrix()
        if backend == "smatrix" and lead_count == 2:
            noise_check_error = max(noise_check_error, abs(float(
                kwant.physics.two_terminal_shotnoise(response) - result["partition_noise"][energy_index, 1, 0]
            )))
    residual = result["transmission"].sum(axis=1) - result["mode_counts"]
    ranks = [int(np.linalg.matrix_rank(block[1], tol=1e-10)) for block in blocks]
    diagnostics = {
        "backend": backend,
        "runtime_seconds": perf_counter() - started,
        "device_orbitals": len(case["cells"]) * case["h_matrices"].shape[1],
        "lead_dimensions": dimensions,
        "lead_hopping_ranks": ranks,
        "unitarity_error": unitarity_error,
        "current_conservation_error": float(np.max(np.abs(residual))),
        "official_shotnoise_error": noise_check_error,
        "surface_dyson_relative_residual": surface_residual,
        "mode_algorithm": "official Kwant default stabilization selection",
        "mode_counts": result["mode_counts"].tolist(),
    }
    if diagnostics["current_conservation_error"] > 2e-5 or unitarity_error > 2e-5 or surface_residual > 2e-5:
        raise ValueError(f"Official scattering consistency failure: {diagnostics}")
    return result, diagnostics
