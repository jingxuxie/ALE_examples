"""Forward-only finite-difference BdG model; energies are meV and lengths nm."""

import hashlib
import json
import math

import numpy as np
from scipy import linalg, ndimage, sparse
from scipy.sparse import linalg as sparse_linalg
from threadpoolctl import threadpool_limits


IDENTITY = np.eye(2)
SPIN_X = np.array([[0, 1], [1, 0]])
SPIN_Y = np.array([[0, -1j], [1j, 0]])
SPIN_Z = np.diag([1, -1])
CHARGE = np.kron(IDENTITY, SPIN_Z)
ZEEMAN = np.kron(SPIN_X, IDENTITY)
PAIR_REAL = np.kron(IDENTITY, SPIN_X)
PAIR_IMAG = np.kron(IDENTITY, SPIN_Y)
PARTICLE_HOLE = np.kron(SPIN_Y, SPIN_Y)


def geometry_arrays(request, geometry):
    expected = {"sc_top", "sc_bottom"}
    if not isinstance(geometry, dict) or set(geometry) != expected:
        raise ValueError("geometry must have exactly sc_top and sc_bottom")
    shape = (request["grid"]["ny"], request["grid"]["nx"])
    result = {}
    for name in sorted(expected):
        array = np.asarray(geometry[name])
        if array.shape != shape or array.dtype.kind not in "biu":
            raise ValueError(f"{name} must be a {shape[0]} by {shape[1]} integer/bool array")
        if not np.all((array == 0) | (array == 1)):
            raise ValueError(f"{name} entries must be 0 or 1")
        result[name] = array.astype(bool)
    return result


def geometry_json(masks):
    return {name: mask.astype(int).tolist() for name, mask in masks.items()}


def geometry_digest(masks):
    digest = hashlib.sha256()
    for name in ("sc_top", "sc_bottom"):
        digest.update(np.asarray(masks[name].shape, dtype="<i8").tobytes())
        digest.update(np.packbits(masks[name]).tobytes())
    return digest.hexdigest()


def original_zigzag(request):
    grid = request["grid"]
    spacing = grid["spacing_nm"]
    columns = np.arange(grid["nx"])
    positions = (np.arange(grid["ny"]) - (grid["ny"] - 1) / 2) * spacing
    amplitude = 100.0
    period = grid["nx"] * spacing
    center = -amplitude + 4 * amplitude * np.minimum(columns, grid["nx"] - columns) / grid["nx"]
    vertical_width = 200.0 * math.sqrt(1 + (4 * amplitude / period) ** 2)
    return {
        "sc_top": positions[:, None] >= center[None, :] + vertical_width / 2,
        "sc_bottom": positions[:, None] <= center[None, :] - vertical_width / 2,
    }


def feasibility(request, masks):
    constraints = request["manufacturing"]
    top, bottom = masks["sc_top"], masks["sc_bottom"]
    violations = []
    if np.any(top & bottom):
        violations.append("overlapping electrodes")
    rows = constraints["minimum_contact_rows"]
    if not np.all(top[-rows:]) or not np.all(bottom[:rows]):
        violations.append("missing full-width superconducting contact layers")
    if np.any(top[:rows]) or np.any(bottom[-rows:]):
        violations.append("electrode enters opposite contact")
    for name, mask in masks.items():
        if not np.array_equal(mask, np.roll(mask[:, ::-1], 1, axis=1)):
            violations.append(f"{name}: missing required longitudinal reflection symmetry")
        tiled = np.tile(mask, (1, 3))
        labels, _ = ndimage.label(tiled)
        contact_row = -1 if name == "sc_top" else 0
        contact_label = labels[contact_row, mask.shape[1]]
        central_labels = labels[:, mask.shape[1]:2 * mask.shape[1]]
        if contact_label == 0 or np.any(central_labels[mask] != contact_label):
            violations.append(f"{name}: disconnected superconducting island")
        filled = ndimage.binary_fill_holes(tiled)
        if np.any(filled[:, mask.shape[1]:2 * mask.shape[1]] != mask):
            violations.append(f"{name}: enclosed normal-region hole")
    flips = sum(int(np.count_nonzero(ndimage.median_filter(mask, size=3, mode="wrap") != mask)) for mask in masks.values())
    if flips > constraints["maximum_median_flips"]:
        violations.append("too many sub-resolution boundary features")
    tiled_bottom = np.tile(bottom, (1, 3))
    distances = ndimage.distance_transform_edt(~tiled_bottom)[:, top.shape[1]:2 * top.shape[1]]
    separation = float(distances[top].min() * request["grid"]["spacing_nm"]) if np.any(top) and np.any(bottom) else 0.0
    if separation + 1e-9 < constraints["minimum_separation_nm"]:
        violations.append("inter-electrode separation below fabrication limit")
    return {"valid": not violations, "violations": violations, "median_flips": flips, "minimum_separation_nm": separation}


def nominal_scenario(request):
    region = request["operating_region"]
    return {"mu_normal_mev": float(np.mean(region["mu_normal_mev"])), "zeeman_mev": float(np.mean(region["zeeman_mev"]))}


class ForwardModel:
    def __init__(self, request, masks, scenario):
        self.request = request
        self.nx = request["grid"]["nx"]
        self.ny = request["grid"]["ny"]
        self.block_size = 4 * self.ny
        self.dimension = 4 * self.nx * self.ny
        spacing = request["grid"]["spacing_nm"]
        fixed = request["fixed_physics"]
        hopping = fixed["kinetic_mev_nm2"] / spacing ** 2
        spin_orbit = fixed["rashba_mev_nm"] / (2 * spacing)
        self.hop_x = -hopping * CHARGE + 1j * spin_orbit * np.kron(SPIN_Y, SPIN_Z)
        self.hop_y = -hopping * CHARGE + 1j * spin_orbit * np.kron(SPIN_X, SPIN_Z)
        top, bottom = masks["sc_top"].ravel(order="F"), masks["sc_bottom"].ravel(order="F")
        superconducting = top | bottom
        mu_normal = scenario["mu_normal_mev"]
        region = request["operating_region"]
        mu_sc = mu_normal if region["mu_sc_rule"] == "matched" else region["mu_sc_mev"]
        chemical = np.where(superconducting, mu_sc, mu_normal)
        phase = fixed["phase_rad"] / 2
        self.onsite = (
            (4 * hopping - chemical)[:, None, None] * CHARGE
            + (~superconducting)[:, None, None] * scenario["zeeman_mev"] * ZEEMAN
            + superconducting[:, None, None] * fixed["delta_mev"] * math.cos(phase) * PAIR_REAL
            + (bottom.astype(int) - top.astype(int))[:, None, None] * fixed["delta_mev"] * math.sin(phase) * PAIR_IMAG
        )
        sites = self.nx * self.ny
        diagonal = sparse.bsr_matrix((self.onsite, np.arange(sites), np.arange(sites + 1)), shape=(self.dimension, self.dimension)).tocsc()
        site_ids = np.arange(sites).reshape((self.nx, self.ny))
        longitudinal = sparse.coo_matrix((np.ones((self.nx - 1) * self.ny), (site_ids[:-1].ravel(), site_ids[1:].ravel())), shape=(sites, sites))
        transverse = sparse.coo_matrix((np.ones(self.nx * (self.ny - 1)), (site_ids[:, :-1].ravel(), site_ids[:, 1:].ravel())), shape=(sites, sites))
        links = sparse.kron(longitudinal, self.hop_x, format="csc") + sparse.kron(transverse, self.hop_y, format="csc")
        self.base = diagonal + links + links.getH()
        closing_sites = sparse.coo_matrix((np.ones(self.ny), (site_ids[-1], site_ids[0])), shape=(sites, sites))
        self.closing = sparse.kron(closing_sites, self.hop_x, format="csc")

    def hamiltonian(self, momentum):
        closing = self.closing * np.exp(1j * momentum)
        return (self.base + closing + closing.getH()).tocsc()

    def low_energy(self, momentum, num_bands=8, tolerance=2e-8):
        matrix = self.hamiltonian(momentum)
        initial = np.random.RandomState(17).normal(size=self.dimension)
        with threadpool_limits(limits=1):
            energies, states = sparse_linalg.eigsh(matrix, k=num_bands, sigma=0.0, which="LM", tol=tolerance, maxiter=2000, v0=initial)
        order = np.argsort(energies)
        energies, states = energies[order], states[:, order]
        residual = np.max(np.linalg.norm(matrix @ states - states * energies, axis=0))
        if not np.all(np.isfinite(energies)) or residual > 2e-5:
            raise RuntimeError(f"unreliable low-energy solve: residual={residual}")
        return energies, states

    def spectral_gap(self, momenta):
        gaps = [float(np.min(np.abs(self.low_energy(float(momentum))[0]))) for momentum in momenta]
        minimum = int(np.argmin(gaps))
        return {"gap_mev": gaps[minimum], "momentum_rad": float(momenta[minimum]), "gaps_mev": gaps, "momenta_rad": list(map(float, momenta))}

    def column_blocks(self):
        transverse = np.kron(np.diag(np.ones(self.ny - 1), 1), self.hop_y)
        transverse = transverse + transverse.conj().T
        columns = []
        for column in range(self.nx):
            diagonal = linalg.block_diag(*self.onsite[column * self.ny:(column + 1) * self.ny])
            columns.append(diagonal + transverse)
        return columns

    def topological_invariant(self):
        with threadpool_limits(limits=1):
            conjugation = np.kron(np.eye(self.ny), PARTICLE_HOLE)
            diagonal = [block @ conjugation for block in self.column_blocks()]
            forward = np.kron(np.eye(self.ny), self.hop_x) @ conjugation
            phases = []
            for momentum in (0.0, math.pi):
                first = diagonal[0].copy()
                current = diagonal[1].copy()
                to_first = -forward.T
                wrap = np.kron(np.eye(self.ny), self.hop_x * np.exp(1j * momentum)) @ conjugation
                total_phase = 1.0 + 0.0j
                for column in range(1, self.nx - 1):
                    total_phase *= pfaffian_phase(current)
                    bridge = np.concatenate((to_first, forward), axis=1)
                    solved = linalg.solve(current, bridge, check_finite=False)
                    correction = bridge.T @ solved
                    width = self.block_size
                    first += correction[:width, :width]
                    current = diagonal[column + 1] + correction[width:, width:]
                    to_first = correction[width:, :width]
                    if column + 1 == self.nx - 1:
                        to_first = to_first + wrap
                    first = (first - first.T) / 2
                    current = (current - current.T) / 2
                final = np.block([[first, -to_first.T], [to_first, current]])
                total_phase *= pfaffian_phase(final)
                phases.append(total_phase / abs(total_phase))
        product = phases[0] * phases[1]
        if abs(product.imag) > 1e-5 or abs(product.real) < 0.99:
            raise RuntimeError("Pfaffian invariant is numerically unresolved")
        return -1 if product.real < 0 else 1


def pfaffian_phase(matrix):
    working = np.array(matrix, dtype=complex, copy=True)
    if working.shape[0] % 2 or not np.allclose(working, -working.T, atol=2e-7):
        raise ValueError("Pfaffian requires an even-dimensional skew-symmetric matrix")
    phase = 1.0 + 0.0j
    for offset in range(0, len(working) - 1, 2):
        pivot_column = offset + 1 + int(np.argmax(np.abs(working[offset, offset + 1:])))
        if pivot_column != offset + 1:
            working[[offset + 1, pivot_column], :] = working[[pivot_column, offset + 1], :]
            working[:, [offset + 1, pivot_column]] = working[:, [pivot_column, offset + 1]]
            phase = -phase
        pivot = working[offset, offset + 1]
        if abs(pivot) < 1e-13:
            raise RuntimeError("singular Pfaffian pivot")
        phase *= pivot / abs(pivot)
        upper = working[offset, offset + 2:].copy()
        lower = working[offset + 1, offset + 2:].copy()
        working[offset + 2:, offset + 2:] += (np.outer(lower, upper) - np.outer(upper, lower)) / pivot
    return phase / abs(phase)


def load_result(request, filename):
    with open(filename, encoding="utf-8") as handle:
        result = json.load(handle)
    if not isinstance(result, dict) or set(result) != {"schema_version", "request_id", "geometry"}:
        raise ValueError("result must contain exactly schema_version, request_id, geometry")
    if result["schema_version"] != 1 or result["request_id"] != request["request_id"]:
        raise ValueError("result schema_version/request_id mismatch")
    return geometry_arrays(request, result["geometry"])
