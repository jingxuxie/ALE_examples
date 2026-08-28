import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from numerics import diagnostics, energy_gradient, finite_difference_hessian, log_omega0, tangent_basis, tangent_hessian


ROOT = Path(__file__).resolve().parents[1]
SPIRIT = ROOT.parents[1] / "authoring" / "spirit"
REVISION = "e82250d3b14411c2c2fa292d143f13e3e111ad8c"
sys.path.insert(0, str(SPIRIT / "core" / "python"))
from spirit import chain, constants, geometry, hamiltonian, htst, simulation, state, system
from spirit.parameters import gneb, llg, mmf


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def case_parameters(family, variant, seed, split):
    random = np.random.default_rng(seed)
    scale = float(random.uniform(0.94, 1.06))
    if family == "coherent":
        count = [6, 10][variant % 2]
        exchange = np.full(count - 1, 12.0 * scale)
        easy = np.full(count, 0.35 * scale)
        angles = np.zeros(count)
        field = np.array([0.035, 0.0, 0.09]) * scale
    elif family == "domain_wall":
        count = [28, 40][variant % 2]
        exchange = np.full(count - 1, 2.0 * scale)
        easy = np.full(count, 0.4 * scale)
        easy[0] *= 0.90
        angles = np.zeros(count)
        field = np.array([0.05, 0.0, 0.10]) * scale
    else:
        count = [20, 28][variant % 2]
        position = np.linspace(0, 1, count)
        exchange = 1.8 * scale * (1 - 0.15 * np.exp(-((position[:-1] - 0.35) / 0.15)**2))
        easy = 0.38 * scale * (1 + 0.12 * np.sin(2 * np.pi * position + random.uniform(-0.2, 0.2)))
        easy[0] *= 0.85
        angles = np.zeros(count)
        field = np.array([0.045, 0.0, 0.10]) * scale
    axes = np.column_stack((np.sin(angles), np.zeros(count), np.cos(angles)))
    if family == "exchange_spring":
        axes[:count // 3] = [1.0, 0.0, 0.0]
    tensors = easy[:, None, None] * np.einsum("ni,nj->nij", axes, axes)
    tensors[:, 1, 1] -= 0.18 * scale
    return {
        "schema_version": 1,
        "case_id": f"{split}_{family}_{variant:02d}_{seed}",
        "family": family,
        "seed": seed,
        "n_spins": count,
        "boundary": "open",
        "exchange_meV": exchange.tolist(),
        "anisotropy_meV": tensors.tolist(),
        "field_meV": field.tolist(),
        "mu_s_muB": 2.0,
        "temperature_K": 5.0,
        "time_limit_seconds": 90.0,
    }


def spirit_config(case):
    count = case["n_spins"]
    field = np.array(case["field_meV"])
    magnitude = np.linalg.norm(field)
    direction = field / magnitude
    lines = [
        "output_file_tag activation_reference",
        "log_to_console 0", "log_to_file 0",
        "log_input_save_initial 0", "log_input_save_final 0",
        "bravais_lattice sc", f"lattice_constant {count}", "n_basis_cells 1 1 1",
        "basis", str(count),
    ]
    lines.extend(f"{index / count:.17g} 0 0" for index in range(count))
    lines.extend([
        "hamiltonian heisenberg_pairs", "boundary_conditions 0 0 0",
        f"mu_s {case['mu_s_muB']:.17g}",
        f"external_field_magnitude {magnitude / (constants.mu_B * case['mu_s_muB']):.17g}",
        "external_field_normal " + " ".join(f"{value:.17g}" for value in direction),
        "anisotropy_magnitude 0", "ddi_method none",
        f"n_interaction_pairs {count - 1}", "i j da db dc Jij",
    ])
    lines.extend(f"{index} {index + 1} 0 0 0 {coupling:.17g}" for index, coupling in enumerate(case["exchange_meV"]))
    records = []
    for index, tensor in enumerate(case["anisotropy_meV"]):
        values, vectors = np.linalg.eigh(tensor)
        for component in range(3):
            if abs(values[component]) > 1e-12:
                records.append(f"{index} {values[component]:.17g} " + " ".join(f"{value:.17g}" for value in vectors[:, component]))
    lines.extend([f"n_anisotropy {len(records)}", "i K Kx Ky Kz", *records])
    for method in ["llg", "gneb", "mmf"]:
        lines.extend([f"{method}_output_any 0", f"{method}_force_convergence 1e-9", f"{method}_n_iterations 50000", f"{method}_n_iterations_log 50000", f"{method}_max_walltime 0:1:0"])
    lines.extend(["llg_dt 0.01", "llg_damping 1", "gneb_spring_constant 1.0", "mmf_n_modes 2"])
    return "\n".join(lines) + "\n"


def set_spins(pointer, spins, image=0):
    system.get_spin_directions(pointer, idx_image=image)[:] = spins
    system.update_data(pointer, idx_image=image)


def relax_official(pointer, spins, image=0):
    set_spins(pointer, spins, image)
    llg.set_convergence(pointer, 1e-10, idx_image=image)
    simulation.start(pointer, simulation.METHOD_LLG, simulation.SOLVER_LBFGS_OSO, n_iterations=15000, idx_image=image)
    return system.get_spin_directions(pointer, idx_image=image).copy()


def build_reference(case, directory):
    directory.mkdir(parents=True, exist_ok=True)
    config = directory / "spirit.cfg"
    config.write_text(spirit_config(case))
    begin = time.perf_counter()
    with state.State(str(config), quiet=True) as pointer:
        count = system.get_nos(pointer)
        if count != case["n_spins"]:
            raise RuntimeError(f"geometry mismatch: {count}")
        random = np.random.default_rng(case["seed"] + 123)
        energy_errors = []
        for repeat in range(3):
            spins = random.normal(size=(count, 3))
            spins /= np.linalg.norm(spins, axis=1)[:, None]
            set_spins(pointer, spins)
            energy_errors.append(abs(system.get_energy(pointer) - energy_gradient(case, spins)[0]))
        if max(energy_errors) > 2e-5:
            raise RuntimeError(f"Hamiltonian mismatch: {energy_errors}")
        initial = np.tile([0.10, 0.0, -1.0], (count, 1))
        initial /= np.linalg.norm(initial, axis=1)[:, None]
        minimum_a = relax_official(pointer, initial)
        initial[:, 2] *= -1
        minimum_b = relax_official(pointer, initial)
        case["minimum_a"] = minimum_a.tolist()
        case["minimum_b"] = minimum_b.tolist()
        chain.image_to_clipboard(pointer)
        images = 15 if case["family"] != "coherent" else 9
        chain.set_length(pointer, images)
        theta_a = np.arctan2(minimum_a[:, 0], minimum_a[:, 2])
        theta_b = np.arctan2(minimum_b[:, 0], minimum_b[:, 2])
        theta_a = np.where(theta_a < 0, theta_a + 2 * np.pi, theta_a)
        position = np.arange(count)
        for image in range(images):
            fraction = image / (images - 1)
            if case["family"] == "coherent":
                weight = fraction
            else:
                width = 2.5
                center = -5 * width + fraction * (count - 1 + 10 * width)
                weight = 0.5 * (1 + np.tanh((center - position) / width))
            angle = (1 - weight) * theta_a + weight * theta_b
            spins = np.column_stack((np.sin(angle), np.zeros(count), np.cos(angle)))
            set_spins(pointer, spins, image)
        set_spins(pointer, minimum_a, 0)
        set_spins(pointer, minimum_b, images - 1)
        gneb.set_convergence(pointer, 1e-8)
        simulation.start(pointer, simulation.METHOD_GNEB, simulation.SOLVER_LBFGS_OSO, n_iterations=5000)
        gneb.set_image_type_automatically(pointer)
        simulation.start(pointer, simulation.METHOD_GNEB, simulation.SOLVER_LBFGS_OSO, n_iterations=40000)
        energies = [float(system.get_energy(pointer, idx_image=image)) for image in range(images)]
        saddle_index = int(np.argmax(energies))
        if saddle_index in (0, images - 1):
            raise RuntimeError("GNEB has no interior maximum")
        saddle = system.get_spin_directions(pointer, idx_image=saddle_index).copy()
        saddle_diagnostic = diagnostics(case, saddle)
        if saddle_diagnostic["residual_meV"] > 2e-7:
            simulation.start(pointer, simulation.METHOD_MMF, simulation.SOLVER_LBFGS_OSO, n_iterations=5000, idx_image=saddle_index)
            saddle = system.get_spin_directions(pointer, idx_image=saddle_index).copy()
            saddle_diagnostic = diagnostics(case, saddle)
        minimum_diagnostic = diagnostics(case, minimum_a)
        native_minimum_energy = float(system.get_energy(pointer, idx_image=0))
        native_saddle_energy = float(system.get_energy(pointer, idx_image=saddle_index))
        if saddle_diagnostic["negative_modes"] != 1 or saddle_diagnostic["zero_modes"] != 0:
            raise RuntimeError(f"invalid saddle inertia: {saddle_diagnostic}")
        if saddle_diagnostic["residual_meV"] > 2e-6 or minimum_diagnostic["residual_meV"] > 2e-6:
            raise RuntimeError(f"stationarity: {saddle_diagnostic['residual_meV']}, {minimum_diagnostic['residual_meV']}")
        if minimum_diagnostic["negative_modes"] or minimum_diagnostic["zero_modes"]:
            raise RuntimeError("minimum is not positive definite")
        htst.calculate(pointer, 0, saddle_index, n_eigenmodes_keep=2, sparse=False)
        official_info = htst.get_info_dict(pointer)
        eigenvalues_minimum = np.asarray(htst.get_eigenvalues_min(pointer), dtype=float)
        eigenvalues_saddle = np.asarray(htst.get_eigenvalues_sp(pointer), dtype=float)
        spectral_error = float(max(np.max(np.abs(eigenvalues_minimum - minimum_diagnostic["eigenvalues"])), np.max(np.abs(eigenvalues_saddle - saddle_diagnostic["eigenvalues"]))))
        official_log_omega = float(np.log(official_info["Omega_0"]))
        independent_log_omega = log_omega0(minimum_diagnostic["eigenvalues"], saddle_diagnostic["eigenvalues"])
        fd_error = float(np.max(np.abs(tangent_hessian(case, saddle) - finite_difference_hessian(case, saddle))))
        if spectral_error > 1e-4 or abs(official_log_omega - independent_log_omega) > 2e-5 or fd_error > 1e-6:
            raise RuntimeError(f"independent Hessian/HTST validation failed: {spectral_error}, {official_log_omega}, {independent_log_omega}, {fd_error}")
        values, vectors = np.linalg.eigh(tangent_hessian(case, saddle))
        direction = np.einsum("nca,na->nc", tangent_basis(saddle), vectors[:, 0].reshape(count, 2))
        branch_distances = []
        for sign in [-1, 1]:
            perturbed = saddle + sign * 0.025 * direction
            perturbed /= np.linalg.norm(perturbed, axis=1)[:, None]
            relaxed = relax_official(pointer, perturbed, images - 1)
            branch_distances.append([float(np.max(np.linalg.norm(relaxed - endpoint, axis=1))) for endpoint in [minimum_a, minimum_b]])
        destinations = np.argmin(branch_distances, axis=1)
        if destinations[0] == destinations[1] or max(np.min(branch_distances, axis=1)) > 2e-4:
            raise RuntimeError(f"saddle does not connect A and B: {branch_distances}")
        barrier = saddle_diagnostic["energy_meV"] - minimum_diagnostic["energy_meV"]
        native_barrier = native_saddle_energy - native_minimum_energy
        if abs(barrier - native_barrier) > 2e-5:
            raise RuntimeError("native Spirit barrier disagrees with independent Hamiltonian")
        result = {
            "saddle": saddle.tolist(), "barrier_meV": barrier,
            "eigenvalues_min_meV": eigenvalues_minimum.tolist(),
            "eigenvalues_saddle_meV": eigenvalues_saddle.tolist(),
            "log_omega0": official_log_omega,
        }
        validation = {
            "case_id": case["case_id"], "source_revision": REVISION,
            "reference_runtime_seconds": time.perf_counter() - begin,
            "n_images": images, "path_energies_meV": energies,
            "minimum_residual_meV": minimum_diagnostic["residual_meV"],
            "saddle_residual_meV": saddle_diagnostic["residual_meV"],
            "saddle_negative_modes": saddle_diagnostic["negative_modes"],
            "saddle_zero_modes": saddle_diagnostic["zero_modes"],
            "random_energy_max_error_meV": max(energy_errors),
            "native_spirit_minimum_energy_meV": native_minimum_energy,
            "native_spirit_saddle_energy_meV": native_saddle_energy,
            "native_spirit_barrier_meV": native_barrier,
            "independent_native_barrier_error_meV": abs(barrier - native_barrier),
            "independent_spectrum_max_error_meV": spectral_error,
            "finite_difference_hessian_max_error_meV": fd_error,
            "independent_log_omega0_error": abs(official_log_omega - independent_log_omega),
            "downhill_branch_endpoint_max_distances": branch_distances,
            "official_htst": official_info,
            "nonuniformity_A": float(np.max(np.linalg.norm(minimum_a - np.mean(minimum_a, axis=0), axis=1))),
            "nonuniformity_saddle": float(np.max(np.linalg.norm(saddle - np.mean(saddle, axis=0), axis=1))),
        }
        write_json(directory / "case.json", case)
        write_json(directory / "solution.json", result)
        write_json(directory / "validation.json", validation)
        np.savez(directory / "solution.npz", **result)
        return validation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["initial", "challenge", "confirmation"], default="initial")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--only", choices=["coherent", "domain_wall", "exchange_spring"])
    args = parser.parse_args()
    if args.split == "confirmation" and args.seed is None:
        parser.error("confirmation requires a fresh explicit --seed; no confirmation cases are pre-generated")
    revision = subprocess.check_output(["git", "-C", str(SPIRIT), "rev-parse", "HEAD"], text=True).strip()
    if revision != REVISION:
        raise RuntimeError(f"unapproved source revision {revision}")
    seed_base = args.seed if args.seed is not None else {"initial": 731000, "challenge": 947000}[args.split]
    destination = ROOT / "private" / ("reference" if args.split == "initial" else "challenge_pool") / args.split
    validations = []
    for family_index, family in enumerate(["coherent", "domain_wall", "exchange_spring"]):
        if args.only and args.only != family:
            continue
        for variant in range(2 if args.split == "initial" else 1):
            case = case_parameters(family, variant, seed_base + family_index * 100 + variant, args.split)
            directory = destination / case["case_id"]
            print(f"BUILD {case['case_id']} N={case['n_spins']}", flush=True)
            validation = build_reference(case, directory)
            validations.append(validation)
            if args.split == "initial":
                write_json(ROOT / "participant" / "input" / f"{case['case_id']}.json", json.loads((directory / "case.json").read_text()))
            print(f"VALIDATED {case['case_id']} {validation['reference_runtime_seconds']:.3f}s residual={validation['saddle_residual_meV']:.3g}", flush=True)
    hashes = {}
    for path in sorted(destination.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_json(destination / "manifest.json", {"source_revision": REVISION, "split": args.split, "seed_base": seed_base, "sha256": hashes, "validations": validations})


if __name__ == "__main__":
    main()
