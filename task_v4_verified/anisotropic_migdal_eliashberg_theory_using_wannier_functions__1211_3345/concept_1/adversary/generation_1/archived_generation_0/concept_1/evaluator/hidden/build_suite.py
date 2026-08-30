"""Privileged randomized material-family construction, not shipped to contestants."""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.sparse.linalg import LinearOperator, eigs


ROOT = Path(__file__).resolve().parents[2]
from reference_operator import ReferenceModel as Model


FAMILIES = ("multiband", "retardation", "critical", "weak_interband", "combined")


def leading(instance):
    model = Model(instance)
    normal_z = model.map(np.zeros(model.shape))[0]

    def action(vector):
        ratio = vector.reshape(model.shape) / model.frequencies[None, :]
        pairing = model.convolve(ratio, 1)
        pairing -= 2 * (model.weighted_coulomb @ ratio.sum(axis=1))[:, None]
        return (np.pi * model.temperature * pairing / normal_z).ravel()

    operator = LinearOperator((np.prod(model.shape), np.prod(model.shape)), matvec=action, dtype=np.float64)
    values, vectors = eigs(operator, k=1, which="LR", v0=np.ones(np.prod(model.shape)), tol=2e-10)
    vector = vectors[:, 0].real.reshape(model.shape)
    vector *= np.sign(np.sum(vector[:, 0]))
    vector /= np.max(np.abs(vector))
    return float(values[0].real), vector


def make_instance(family, seed, index, public=False):
    random = np.random.default_rng(seed)
    n_bands = int(random.integers(3, 6))
    patches_per_band = int(random.integers(3, 6))
    patches = n_bands * patches_per_band
    band = np.repeat(np.arange(n_bands), patches_per_band)
    weights = np.exp(random.uniform(-1.7, 1.0, patches))
    weights /= weights.sum()
    mass = np.bincount(band, weights=weights)
    base_energy = np.exp(random.uniform(np.log(3.0), np.log(70.0)))
    if family in ("retardation", "combined"):
        omega = base_energy * np.array([0.018, 0.11, 0.55, 1.0])
        n_freq = (768, 1024, 1536, 2048)[index % 4]
        temperature = base_energy / random.uniform(160, 280)
    else:
        omega = base_energy * np.array([0.24, 0.57, 1.0])
        n_freq = (192, 256, 384, 512)[index % 4]
        temperature = base_energy / random.uniform(32, 65)
    if public:
        n_freq = min(n_freq, 768)
    intraband = random.uniform(0.75, 1.8, n_bands)
    interband = random.uniform(0.035, 0.14)
    if family in ("weak_interband", "combined"):
        interband = 10 ** random.uniform(-7.5, -4.5)
        intraband = np.linspace(0.45, 1.3, n_bands) * random.uniform(0.85, 1.15, n_bands)
    block = np.sqrt(intraband[:, None] * intraband[None, :]) * interband
    np.fill_diagonal(block, intraband)
    block /= np.sqrt(mass[:, None] * mass[None, :])
    angular = np.exp(random.uniform(-0.32, 0.32, patches))
    raw = block[band[:, None], band[None, :]] * angular[:, None] * angular[None, :]
    perturbation = random.uniform(0.8, 1.2, (patches, patches))
    raw *= (perturbation + perturbation.T) / 2
    fractions = random.uniform(0.15, 1.0, (len(omega), patches, patches))
    fractions = (fractions + fractions.transpose(0, 2, 1)) / 2
    if family in ("retardation", "combined"):
        fractions[0] *= 3.5
    fractions /= fractions.sum(axis=0)
    coupling = fractions * raw[None, :, :]
    coulomb = np.zeros((patches, patches))
    if family not in ("weak_interband", "combined"):
        coulomb = random.uniform(0.02, 0.07) * raw / np.max(raw @ weights)
    instance = {"temperature": np.array(temperature), "n_freq": np.array(n_freq),
                "weights": weights, "omega": omega, "coupling": coupling, "coulomb": coulomb}
    target = None
    if family in ("critical", "combined"):
        target = 1 + (2e-5, 1e-4, 6e-4, 3e-3)[index % 4]
        lower, upper = 0.02, 8.0
        original = coupling.copy()
        for iteration in range(36):
            scale = np.sqrt(lower * upper)
            instance["coupling"] = original * scale
            eigenvalue, vector = leading(instance)
            if eigenvalue < target:
                lower = scale
            else:
                upper = scale
        instance["coupling"] = original * np.sqrt(lower * upper)
    eigenvalue, vector = leading(instance)
    if eigenvalue <= 1.01 and target is None:
        instance["coupling"] *= 1.6
        eigenvalue, vector = leading(instance)
    frequency = np.pi * temperature * (2 * np.arange(n_freq) + 1)
    initial = 0.4 * base_energy / (1 + (frequency / base_energy) ** 2)
    instance["initial_delta"] = np.broadcast_to(initial, (patches, n_freq)).copy()
    permutation = random.permutation(patches)
    instance["weights"] = instance["weights"][permutation]
    instance["coupling"] = instance["coupling"][:, permutation][:, :, permutation]
    instance["coulomb"] = instance["coulomb"][permutation][:, permutation]
    instance["initial_delta"] = instance["initial_delta"][permutation]
    metadata = {"family": family, "seed": seed, "index": index, "linear_eigenvalue": eigenvalue,
                "n_bands": n_bands, "patches": patches, "n_freq": n_freq,
                "band": band[permutation].tolist(), "interband_factor": interband,
                "phonon_ratio": float(omega.max() / omega.min()), "temperature": temperature,
                "max_frequency_over_max_phonon": float(frequency[-1] / omega.max())}
    return instance, metadata


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-only", action="store_true")
    parser.add_argument("--family", choices=FAMILIES)
    args = parser.parse_args()
    records = []
    for family_index, family in enumerate(FAMILIES):
        if args.family and family != args.family:
            continue
        public_dir = ROOT / "participant" / "input" / "examples"
        public_dir.mkdir(parents=True, exist_ok=True)
        instance, metadata = make_instance(family, 53119 + family_index * 117, 1, True)
        np.savez_compressed(public_dir / (family + ".npz"), **instance)
        if args.public_only:
            continue
        for index in range(4):
            seed = 71392021 + family_index * 10237 + index * 1931
            instance, metadata = make_instance(family, seed, index)
            case_id = "case_%02d" % (family_index * 4 + index)
            directory = Path(__file__).resolve().parent / "cases"
            directory.mkdir(exist_ok=True)
            np.savez_compressed(directory / (case_id + ".npz"), **instance)
            records.append(dict(metadata, case_id=case_id))
            print(json.dumps(records[-1]), flush=True)
    if not args.public_only:
        destination = Path(__file__).resolve().parent / ("manifest" + ("_" + args.family if args.family else "") + ".json")
        destination.write_text(json.dumps({"version": 1, "cases": records}, indent=2) + "\n")


if __name__ == "__main__":
    main()
