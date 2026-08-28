import argparse
import hashlib
import json
import os
from pathlib import Path
import pickle
import shutil
import subprocess
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
sys.dont_write_bytecode = True
PILOT = Path(__file__).resolve().parents[1]
SOURCE = PILOT.parents[1] / "source"
sys.path.insert(0, str(SOURCE / "runtime"))
sys.path.insert(0, str(SOURCE / "zigzag-majoranas"))

import numpy as np
import scipy.constants
import scipy.linalg
import scipy.sparse as sparse
import scipy.sparse.linalg as sparse_linalg
import zigzag
from kwant.continuum import discretizer


class CompatibleNumericPrinter(discretizer._NumericPrinter):
    def __init__(self):
        super().__init__()
        self.known_functions.update(sin="sin", cos="cos", exp="exp")


discretizer._NumericPrinter = CompatibleNumericPrinter


def save_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def defaults():
    params = dict(zigzag.constants)
    params.update(
        m_eff=0.02 * scipy.constants.m_e / (scipy.constants.eV * 1e-3) / 1e18,
        g_factor_middle=26, g_factor_left=0, g_factor_right=0,
        mu=10, alpha_middle=20, alpha_left=0, alpha_right=0,
        Delta_left=1, Delta_right=1, B_x=1, B_y=0, B_z=0,
        phase=np.pi, V=0, V_breaking=lambda coordinate: 0,
    )
    geometry = dict(
        W=200, L_x=4550, L_sc_up=300, L_sc_down=300,
        z_x=1300, z_y=0, a=10, shape="parallel_curve",
        transverse_soi=True, mu_from_bottom_of_spin_orbit_bands=True,
        k_x_in_sc=True, wraparound=False, infinite=False,
        phs_breaking_potential=True,
    )
    return params, geometry


def end_observables(basis, energy_matrix, x_orbital, x_grid):
    energies, rotation = scipy.linalg.eigh(energy_matrix)
    pair = np.argsort(np.abs(energies))[:2]
    states = basis @ rotation[:, pair]
    positions, ends = scipy.linalg.eigh(states.conj().T @ (x_orbital[:, None] * states))
    left = states @ ends[:, 0]
    profile = np.bincount(
        np.searchsorted(x_grid, x_orbital), weights=np.abs(left) ** 2,
        minlength=len(x_grid),
    )
    profile /= profile.sum()
    quarter = len(x_grid) // 4
    slope = np.polyfit(x_grid[quarter:2 * quarter], np.log(profile[quarter:2 * quarter]), 1)[0]
    return dict(rho_left=profile.tolist(), xi_window_nm=float(-2 / slope)), positions


def bulk_reference(onsite, hopping, cell_length):
    eigenvalues = zigzag.translation_ev(onsite, hopping)
    magnitudes = np.abs(eigenvalues)
    stable = magnitudes[(magnitudes > 1e-14) & (magnitudes < 1 - 1e-9)]
    xi = float(-cell_length / np.log(stable.max()))
    return xi, eigenvalues


def grouped_cell(onsite, hopping, count):
    dimension = len(onsite)
    cell = np.kron(np.eye(count), onsite)
    link = np.zeros_like(cell)
    for index in range(count - 1):
        first = slice(index * dimension, (index + 1) * dimension)
        second = slice((index + 1) * dimension, (index + 2) * dimension)
        cell[first, second] = hopping
        cell[second, first] = hopping.conj().T
    link[-dimension:, :dimension] = hopping
    return cell, link


def straight_witness(onsite, hopping, mu, field, reference, raw_entry):
    cache = reference / f"straight_mu_{mu:g}_field_{field:g}.npz"
    if cache.exists():
        with np.load(cache, allow_pickle=False) as arrays:
            return arrays["x_nm"], arrays["density"]
    started = time.monotonic()
    cell_count = 455
    diagonal = sparse.kron(sparse.eye(cell_count), sparse.csc_matrix(onsite), format="csc")
    forward = sparse.kron(sparse.diags(np.ones(cell_count - 1), 1), sparse.csc_matrix(hopping), format="csc")
    matrix = diagonal + forward + forward.conj().T
    generator = np.random.default_rng(2537)
    values, states = sparse_linalg.eigsh(matrix, k=2, sigma=0, which="LM", tol=1e-10,
                                       v0=generator.normal(size=matrix.shape[0]))
    positive = np.flatnonzero(values > 0)
    selected = positive[np.argmin(values[positive])]
    density = (np.abs(states[:, selected]) ** 2).reshape(cell_count, -1).sum(axis=1)
    density /= density.sum()
    audit = dict(mu_meV=mu, B_x_code=field, dimension=matrix.shape[0],
                 finite_energy_meV=float(values[selected]), seconds=time.monotonic() - started,
                 residual_meV=float(np.linalg.norm(matrix @ states[:, selected] - values[selected] * states[:, selected])))
    assert audit["residual_meV"] < 1e-7
    if mu == 10 and field == 1:
        raw_profile = np.asarray(raw_entry[1]).reshape(cell_count, -1).sum(axis=1)
        audit["archived_profile_total_variation"] = float(np.abs(density - raw_profile).sum() / 2)
        audit["archived_energy_absolute_error_meV"] = float(abs(values[selected] - raw_entry[0]))
        assert audit["archived_profile_total_variation"] < 1e-5, audit
        assert audit["archived_energy_absolute_error_meV"] < 1e-7, audit
        density = raw_profile
    coordinates = np.arange(cell_count) * 10.
    np.savez_compressed(cache, x_nm=coordinates, density=density)
    save_json(cache.with_suffix(".json"), audit)
    print("straight witness", json.dumps(audit), flush=True)
    return coordinates, density


def finite_archive(geometry, params, raw_entry, shape_index, reference):
    cache = reference / f"finite_{shape_index}.npz"
    if cache.exists():
        return dict(np.load(cache, allow_pickle=False))
    started = time.monotonic()
    system = zigzag.system(**geometry)
    positions = np.array([site.pos for site in system.sites])
    matrix = system.hamiltonian_submatrix(params=params, sparse=True).tocsc()
    print("finite", shape_index, matrix.shape, matrix.nnz, "start eigsh", flush=True)
    generator = np.random.default_rng(491 + shape_index)
    energies, states = sparse_linalg.eigsh(
        matrix, k=6, sigma=0, which="LM", tol=2e-10,
        v0=generator.normal(size=matrix.shape[0]),
    )
    ordering = np.argsort(energies)
    energies, states = energies[ordering], states[:, ordering]
    states, _ = np.linalg.qr(states)
    energy_matrix = states.conj().T @ (matrix @ states)
    actual_energies, rotation = scipy.linalg.eigh(energy_matrix)
    states = states @ rotation
    energy_matrix = np.diag(actual_energies).astype(complex)
    positive = np.flatnonzero(actual_energies > 0)
    selected = positive[np.argmin(actual_energies[positive])]
    density = (np.abs(states[:, selected]) ** 2).reshape(-1, 4).sum(axis=1)
    raw_density = raw_entry[1]
    residual = np.linalg.norm(matrix @ states - states @ energy_matrix) / np.linalg.norm(states)
    audit = dict(
        shape_index=shape_index, dimension=matrix.shape[0], nnz=matrix.nnz,
        seconds=time.monotonic() - started, eigenvalues_meV=actual_energies.tolist(),
        absolute_residual_meV=float(residual),
        archived_energy_meV=float(raw_entry[0]),
        energy_relative_error=float(abs(actual_energies[selected] / raw_entry[0] - 1)),
        archived_density_total_variation=float(np.abs(density - raw_density).sum() / 2),
        archived_xi_label_nm=float(raw_entry[3] * 1000),
    )
    assert len(raw_density) == len(positions)
    assert audit["energy_relative_error"] < 5e-4, audit
    assert abs(actual_energies[selected] - raw_entry[0]) < 1e-8, audit
    assert audit["archived_density_total_variation"] < 2e-4, audit
    assert residual < 1e-7, audit
    result = dict(basis=states, energy_matrix=energy_matrix, positions_nm=positions)
    np.savez_compressed(cache, **result)
    save_json(reference / f"finite_{shape_index}_audit.json", audit)
    print(json.dumps(audit), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--finite-shapes", type=int, default=3)
    args = parser.parse_args()
    reference = PILOT / "private/reference"
    pool = PILOT / "private/challenge_pool"
    public = PILOT / "participant/input"
    for path in (reference, pool, public, PILOT / "participant/workspace", PILOT / "attempt"):
        path.mkdir(parents=True, exist_ok=True)
    repository = SOURCE / "zigzag-majoranas"
    raw_path = repository / "data/wave_functions.pickle"
    shutil.copy2(raw_path, reference / raw_path.name)
    shutil.copy2(repository / "zigzag.py", reference / "official_zigzag.py")
    shutil.copy2(repository / "LICENSE.txt", reference / "upstream_LICENSE.txt")
    for filename, command in (
        ("full_history.txt", ["log", "--all", "--date=iso-strict", "--format=%H %ad %s"]),
        ("b0c4aa5.patch", ["show", "b0c4aa5"]),
        ("historical_spectrum_before_fix.py", ["show", "b0c4aa5^:spectrum.py"]),
    ):
        (reference / filename).write_bytes(subprocess.check_output(["git", "-C", str(repository), *command]))
    raw = pickle.loads(raw_path.read_bytes())
    params, geometry = defaults()
    cases, targets, audits = [], {}, []
    straight_system = zigzag.system(**dict(geometry, L_x=10, z_x=10, infinite=True))
    for index, (mu, field, count) in enumerate([
        (10., 1., 1), (9.6, 1., 1), (10.4, 1., 1),
        (10., 0.85, 1), (10., 1.15, 1), (10., 1., 2),
        (9.6, 1., 2), (10.4, 1., 2),
        (4., 1., 1), (20., 1., 1), (10., 0.2, 1),
        (10., 2., 1), (10., 3., 1), (14., 3., 2),
    ]):
        case_id = f"b{index:02d}"
        varied = dict(params, mu=mu, B_x=field)
        onsite, hopping = zigzag.cell_mats(straight_system, varied)
        xi, eigenvalues = bulk_reference(onsite, hopping, 10.)
        official_xi = float(zigzag.majorana_size_from_modes(straight_system, varied))
        assert abs(xi / official_xi - 1) < 2e-7
        if index == 0:
            assert abs(xi / (raw[0][3] * 1000) - 1) < 2e-5
        witness_x, witness_density = straight_witness(onsite, hopping, mu, field, reference, raw[0])
        onsite, hopping = grouped_cell(onsite, hopping, count)
        grouped_xi, grouped_ev = bulk_reference(onsite, hopping, 10. * count)
        assert abs(grouped_xi / xi - 1) < 3e-7
        rng = np.random.default_rng(8200 + index)
        phases = np.exp(1j * rng.uniform(-np.pi, np.pi, len(onsite)))
        onsite = phases[:, None].conj() * onsite * phases[None, :]
        hopping = phases[:, None].conj() * hopping * phases[None, :]
        np.savez_compressed(
            pool / f"{case_id}.npz", onsite=onsite, hopping=hopping,
            cell_length_nm=np.array(10. * count), witness_x_nm=witness_x,
            witness_density=witness_density,
        )
        case = dict(id=case_id, family="bulk_tail", file=f"{case_id}.npz",
                    mu_meV=mu, B_x_code=field, device_length_nm=4550,
                    witness="finite eigenstate density at the same physical parameters",
                    witness_origin="author archive" if mu == 10 and field == 1 else "regenerated numerical simulation")
        cases.append(case)
        targets[case_id] = dict(xi_amplitude_nm=xi)
        audits.append(dict(id=case_id, xi_amplitude_nm=xi, official_xi_nm=official_xi,
                           cell_length_nm=10. * count, dimension=len(onsite),
                           hopping_rank=int(np.linalg.matrix_rank(hopping))))
        np.savez_compressed(reference / f"{case_id}_modes.npz", eigenvalues=grouped_ev)
        print(case_id, "xi", xi, "dimension", len(onsite), flush=True)
    shapes = [("sawtooth", None), ("parallel_curve", None), ("parallel_curve", (60, 30, 1))]
    for shape_index, (shape, roughness) in enumerate(shapes[:args.finite_shapes], start=1):
        finite = finite_archive(
            dict(geometry, z_y=100, shape=shape, rough_edge=roughness),
            params, raw[shape_index], shape_index, reference,
        )
        x_orbital = np.repeat(finite["positions_nm"][:, 0], 4)
        x_grid = np.unique(x_orbital)
        target, end_centers = end_observables(finite["basis"], finite["energy_matrix"], x_orbital, x_grid)
        for variant in range(2):
            case_id = f"e{shape_index}{variant}"
            rng = np.random.default_rng(9751 + shape_index * 13 + variant)
            mixing, _ = np.linalg.qr(rng.normal(size=(6, 6)) + 1j * rng.normal(size=(6, 6)))
            basis = finite["basis"] @ mixing
            energy_matrix = mixing.conj().T @ finite["energy_matrix"] @ mixing
            if variant:
                site_phase = np.exp(1j * rng.uniform(-np.pi, np.pi, len(basis) // 4))
                basis *= np.repeat(site_phase, 4)[:, None]
            np.savez_compressed(pool / f"{case_id}.npz", basis=basis,
                                energy_matrix=energy_matrix,
                                x_orbital_nm=x_orbital, x_grid_nm=x_grid)
            cases.append(dict(id=case_id, family="finite_end", file=f"{case_id}.npz",
                              device_length_nm=4550, geometry=shape,
                              rough_edge=roughness, norbs_per_site=4))
            targets[case_id] = target
            check, centers = end_observables(basis, energy_matrix, x_orbital, x_grid)
            assert np.max(np.abs(np.array(check["rho_left"]) - target["rho_left"])) < 1e-10
            assert abs(check["xi_window_nm"] / target["xi_window_nm"] - 1) < 1e-7
        audits.append(dict(shape_index=shape_index, end_centers_nm=end_centers.tolist(),
                           xi_window_amplitude_nm=target["xi_window_nm"],
                           raw_xi_density_label_nm=float(raw[shape_index][3] * 1000)))
    manifest = dict(schema_version=1, cases=cases)
    save_json(pool / "manifest.json", manifest)
    public_cases = [case for case in cases if case["id"] in ("b01", "e10")]
    for case in public_cases:
        shutil.copy2(pool / case["file"], public / case["file"])
    save_json(public / "manifest.json", dict(schema_version=1, cases=public_cases))
    save_json(reference / "targets.json", targets)
    provenance = dict(
        git_head=subprocess.check_output(["git", "-C", str(repository), "rev-parse", "HEAD"], text=True).strip(),
        commit_count=int(subprocess.check_output(["git", "-C", str(repository), "rev-list", "--all", "--count"])),
        shallow=subprocess.check_output(["git", "-C", str(repository), "rev-parse", "--is-shallow-repository"], text=True).strip(),
        raw_sha256=digest(raw_path), raw_git_blob=subprocess.check_output(
            ["git", "-C", str(repository), "rev-parse", "HEAD:data/wave_functions.pickle"], text=True).strip(),
        audits=audits,
        inputs_sha256={case["file"]: digest(pool / case["file"]) for case in cases},
    )
    save_json(reference / "provenance.json", provenance)
    print("BUILD COMPLETE", len(cases), flush=True)


if __name__ == "__main__":
    main()
