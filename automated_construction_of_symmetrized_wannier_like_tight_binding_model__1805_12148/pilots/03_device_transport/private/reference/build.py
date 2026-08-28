"""Prepare real-material cases and stored official transport references."""

import argparse
import hashlib
import itertools
import json
import shutil
import subprocess
from pathlib import Path

from transport import OfficialModes, build_system, lead_blocks, np, read_case, solve

import h5py
import tbmodels

PILOT = Path(__file__).resolve().parents[2]
ROOT = PILOT.parents[1]
UPSTREAM = ROOT / "authoring/sources/TBmodels"
POOL = PILOT / "private/challenge_pool"
MODELS = Path(__file__).resolve().parent / "models"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def extract_models():
    MODELS.mkdir(parents=True, exist_ok=True)
    pin = subprocess.check_output(["git", "-C", str(UPSTREAM), "rev-parse", "HEAD"], text=True).strip()
    paths = {
        "inas": "tests/samples/InAs_sym_reference.hdf5",
        "si": "tests/samples/cli_eigenvals/silicon_model.hdf5",
    }
    provenance = {"tbmodels_data_pin": pin, "models": {}}
    for name, relative in paths.items():
        source = UPSTREAM / relative
        with h5py.File(source) as handle:
            hoppings = {}
            for group in handle["hop"].values():
                vector = tuple(int(value) for value in group["R"][()])
                matrix = group["mat"][()]
                hoppings[vector] = hoppings.get(vector, np.zeros_like(matrix)) + matrix
                negative = tuple(-value for value in vector)
                hoppings[negative] = hoppings.get(negative, np.zeros_like(matrix)) + matrix.conj().T
            vectors = sorted(hoppings)
            model = {
                "h_R": np.asarray(vectors, dtype=np.int64),
                "h_matrices": np.asarray([hoppings[vector] for vector in vectors]),
                "cell": handle["uc"][()],
                "orbital_positions": handle["pos"][()],
            }
        np.savez_compressed(MODELS / f"{name}.npz", **model)
        shutil.copyfile(source, MODELS / f"{name}.hdf5")
        provenance["models"][name] = {
            "source_path": relative,
            "source_sha256": digest(source),
            "converted_sha256": digest(MODELS / f"{name}.npz"),
            "orbitals": model["h_matrices"].shape[1],
            "directed_hopping_vectors": len(vectors),
            "maximum_translation": np.max(np.abs(model["h_R"]), axis=0).tolist(),
            "conversion": "Stored half-Hamiltonian plus Hermitian conjugate; no hopping cutoff or rescaling.",
        }
    provenance["bulk_start_pin"] = subprocess.check_output(
        ["git", "-C", str(UPSTREAM), "rev-parse", "a613d8e^"], text=True
    ).strip()
    source = subprocess.check_output(
        ["git", "-C", str(UPSTREAM), "show", provenance["bulk_start_pin"] + ":tbmodels/_tb_model.py"]
    )
    (MODELS / "historical_tb_model.py.txt").write_bytes(source)
    (MODELS / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    return provenance


def make_case(material, terminal_count, seed, small=False):
    generator = np.random.default_rng(seed)
    case = read_case(MODELS / f"{material}.npz")
    orbitals = case["h_matrices"].shape[1]
    basis = np.eye(3, dtype=np.int64)
    if material == "inas" and terminal_count == 3:
        basis = np.asarray([[1, 1, 0], [0, 1, 0], [0, 0, 1]], dtype=np.int64)
    inverse = np.rint(np.linalg.inv(basis)).astype(np.int64)
    ranges = np.max(np.abs(case["h_R"] @ inverse), axis=0)
    periods = ranges + 1
    width = 2
    length = 22 if small else int(generator.integers(360, 411))
    if material == "si" and not small:
        length += 100
    arm_width = 2
    arm_start = length // 2
    arm_height = int(width + periods[1] + 3)
    grid_cells = set(itertools.product(range(length), range(width), [0]))
    if terminal_count == 3:
        grid_cells.update(itertools.product(range(arm_start, arm_start + arm_width), range(width, arm_height), [0]))
    cells = sorted(tuple(np.asarray(cell) @ basis) for cell in grid_cells)
    case["schema_version"] = np.asarray(1, dtype=np.int64)
    case["cells"] = np.asarray(cells, dtype=np.int64)
    case["lead_count"] = np.asarray(terminal_count, dtype=np.int64)
    interface_grids = [
        list(itertools.product(range(int(periods[0])), range(width), [0])),
        list(itertools.product(range(length - int(periods[0]), length), range(width), [0])),
    ]
    shifts = [-periods[0] * basis[0], periods[0] * basis[0]]
    if terminal_count == 3:
        interface_grids.append(list(itertools.product(
            range(arm_start, arm_start + arm_width), range(arm_height - int(periods[1]), arm_height), [0]
        )))
        shifts.append(periods[1] * basis[1])
    for lead_index, (interface, period) in enumerate(zip(interface_grids, shifts)):
        case[f"lead_cells_{lead_index}"] = np.asarray(interface, dtype=np.int64) @ basis
        case[f"lead_period_{lead_index}"] = np.asarray(period, dtype=np.int64)
        case[f"lead_shift_{lead_index}"] = np.asarray(0.0)
    physical_positions = (case["cells"][:, None, :] + case["orbital_positions"][None, :, :]) @ case["cell"]
    direction = basis[0] @ case["cell"]
    direction /= np.linalg.norm(direction)
    longitudinal = physical_positions @ direction
    center = float(np.median(longitudinal))
    gate_width = 6 * np.linalg.norm(basis[0] @ case["cell"])
    gate = float(generator.uniform(0.25, 0.65)) * np.exp(-((longitudinal - center) / gate_width) ** 2)
    gate += 0.16 * np.exp(-((longitudinal - center - 2.1 * gate_width) / (0.6 * gate_width)) ** 2)
    case["potential"] = gate
    lookup = {tuple(cell): index for index, cell in enumerate(case["cells"])}
    for lead_index in range(terminal_count):
        for cell in case[f"lead_cells_{lead_index}"]:
            case["potential"][lookup[tuple(cell)]] = float(case[f"lead_shift_{lead_index}"])
    assert case["potential"].shape == (len(cells), orbitals)
    assert len(cells) * orbitals > 7000 or small
    check_geometry_contract(case)
    return case


def check_geometry_contract(case):
    support = {tuple(vector) for vector in case["h_R"]}
    device = {tuple(cell) for cell in case["cells"]}
    occupied_interfaces = set()
    for lead_index in range(int(case["lead_count"])):
        interface = case[f"lead_cells_{lead_index}"]
        interface_set = {tuple(cell) for cell in interface}
        assert interface_set <= device
        assert not occupied_interfaces.intersection(interface_set)
        occupied_interfaces.update(interface_set)
        period = case[f"lead_period_{lead_index}"]
        exterior = interface + period
        assert not device.intersection(map(tuple, exterior))
        for exterior_cell in exterior:
            for vector in support:
                connected = tuple(exterior_cell + vector)
                assert connected not in device or connected in interface_set
        for row_cell in interface:
            for column_cell in interface:
                assert tuple(column_cell - row_cell - 2 * period) not in support
    return True


def choose_energies(case, seed, count):
    generator = np.random.default_rng(seed)
    blocks = [lead_blocks(case, index) for index in range(int(case["lead_count"]))]
    functions = [OfficialModes(*block) for block in blocks]
    first_cell, first_hop = blocks[0]
    spectrum = np.concatenate([
        np.linalg.eigvalsh(first_cell + first_hop * np.exp(1j * phase) + first_hop.conj().T * np.exp(-1j * phase))
        for phase in np.linspace(-np.pi, np.pi, 31, endpoint=False)
    ])
    lower, upper = np.quantile(spectrum, [0.25, 0.70])
    candidates = np.linspace(lower, upper, 61) + generator.uniform(-0.017, 0.017, 61)
    generator.shuffle(candidates)
    selected = []
    for energy in candidates:
        try:
            counts = [len(function(energy)[0].velocities) // 2 for function in functions]
        except (RuntimeError, ValueError, np.linalg.LinAlgError):
            continue
        if min(counts) >= 2 and max(counts) <= 18:
            selected.append(float(energy))
        if len(selected) == count:
            return np.sort(selected)
    raise RuntimeError("Could not find enough propagating real-material lead energies")


def validate_tbmodels_geometry():
    reports = {}
    for material in ("inas", "si"):
        model_data = read_case(MODELS / f"{material}.npz")
        original = tbmodels.Model.from_hdf5_file(MODELS / f"{material}.hdf5")
        converted = tbmodels.Model(
            hop={tuple(vector): matrix for vector, matrix in zip(model_data["h_R"], model_data["h_matrices"])},
            pos=model_data["orbital_positions"], uc=model_data["cell"], contains_cc=True
        )
        bulk_error = max(float(np.max(np.abs(original.hamilton(wavevector, convention=2) - converted.hamilton(wavevector, convention=2))))
                         for wavevector in ([0.13, -0.27, 0.09], [0, 0, 0], [-0.32, 0.17, 0.41]))
        dimensions = [5, 3, 2]
        supercell = original.supercell(dimensions)
        expected = supercell.hop[(0, 0, 0)] + supercell.hop[(0, 0, 0)].conj().T
        case = dict(model_data)
        case["cells"] = np.asarray(list(itertools.product(*(range(value) for value in dimensions))), dtype=np.int64)
        case["potential"] = np.zeros((len(case["cells"]), original.size))
        case["lead_count"] = np.asarray(0)
        system, _, _ = build_system(case)
        actual = system.hamiltonian_submatrix()
        finite_error = float(np.max(np.abs(actual - expected)))
        assert bulk_error < 1e-10 and finite_error < 1e-10
        reports[material] = {"bulk_max_abs_error": bulk_error, "finite_supercell_max_abs_error": finite_error,
                             "reference": "official TBmodels 1.4.3 Model.supercell and Model.hamilton"}
    (MODELS / "geometry_validation.json").write_text(json.dumps(reports, indent=2) + "\n")
    return reports


def build_split(split):
    seeds = {"test": 38017, "challenge": 59039, "confirmation": 87083}
    destination = POOL / split
    destination.mkdir(parents=True, exist_ok=True)
    manifest = []
    for index, (material, terminals) in enumerate(itertools.product(("inas", "si"), (2, 3))):
        seed = seeds[split] + 103 * index
        identifier = hashlib.sha256(f"{split}-{seed}".encode()).hexdigest()[:12]
        case = make_case(material, terminals, seed)
        case["energies"] = choose_energies(case, seed + 23, 2)
        input_path = destination / f"{identifier}.npz"
        np.savez_compressed(input_path, **case)
        result, diagnostics = solve(case)
        output_path = destination / f"{identifier}.reference.npz"
        np.savez_compressed(output_path, **result)
        assert all(rank < size for rank, size in zip(diagnostics["lead_hopping_ranks"], diagnostics["lead_dimensions"]))
        assert np.min(result["partition_noise"]) > -1e-7
        diagnostics["maximum_partition_noise"] = float(np.max(result["partition_noise"]))
        diagnostics["input_sha256"] = digest(input_path)
        diagnostics["reference_sha256"] = digest(output_path)
        manifest.append({"id": identifier, "family": f"{material}_{terminals}terminal", "input": input_path.name,
                         "reference": output_path.name, "seed": seed, "timeout_seconds": 90,
                         "memory_mb": 1024, "diagnostics": diagnostics})
        print(json.dumps({"split": split, **manifest[-1]}), flush=True)
        (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["smoke", "test", "challenge", "confirmation", "all"], default="smoke")
    parser.add_argument("--prepare", action="store_true")
    arguments = parser.parse_args()
    if arguments.prepare or not (MODELS / "provenance.json").exists():
        print(json.dumps(extract_models()), flush=True)
        print(json.dumps(validate_tbmodels_geometry()), flush=True)
    if arguments.split in ("smoke", "all"):
        case = make_case("si", 2, 17101, small=True)
        case["energies"] = choose_energies(case, 17119, 1)
        directory = PILOT / "participant/input"
        directory.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(directory / "example.npz", **case)
        result, diagnostics = solve(case)
        np.savez_compressed(MODELS / "smoke.reference.npz", **result)
        alternative, alternative_diagnostics = solve(case, backend="greens")
        errors = {key: float(np.max(np.abs(result[key] - alternative[key]))) for key in result}
        assert max(errors.values()) < 2e-5, errors
        print(json.dumps({"smoke": diagnostics, "independent": alternative_diagnostics, "errors": errors}), flush=True)
        (MODELS / "smoke_validation.json").write_text(json.dumps({"smatrix": diagnostics, "greens": alternative_diagnostics,
                                                                 "max_abs_errors": errors}, indent=2) + "\n")
    for split in ("test", "challenge", "confirmation"):
        if arguments.split in (split, "all"):
            build_split(split)


if __name__ == "__main__":
    main()
