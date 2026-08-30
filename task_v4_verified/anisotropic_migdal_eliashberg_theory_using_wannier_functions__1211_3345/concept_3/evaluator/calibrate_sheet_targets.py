"""Prelaunch comparison of sheet-resolved, rather than probe-averaged, mass."""

import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "adversary" / "prelaunch_v1"
sys.path.insert(0, str(ROOT / "adversary" / "prelaunch_v1" / "participant" / "input"))
sys.path.insert(0, str(ROOT / "adversary" / "prelaunch_v1" / "participant" / "baseline"))
import generator
import solve as baseline
from identifiability import jacobian


def sheet_mass(parameters, family):
    energy, width, coherence, weights = generator.components(parameters, family)
    total_width = width + generator.RESOLUTION
    edges = generator.EDGES[:-1, None]
    cumulative = (np.arctan((edges - energy) / total_width) + np.arctan((edges + energy) / total_width)) / np.pi
    cumulative = np.concatenate((cumulative, np.ones((1, len(energy)))), axis=0)
    kernel = np.diff(cumulative, axis=0)
    bands = 3 if family == 3 else 2
    count = len(energy) // bands
    result = np.zeros((3, kernel.shape[0]), dtype=parameters.dtype)
    for band in range(bands):
        section = slice(band * count, (band + 1) * count)
        measure = weights[0, section] / weights[0, section].sum()
        result[band] = kernel[:, section] @ measure
    return result


def main():
    splits = {}
    for split in ("train", "validation", "audit"):
        destination = ARCHIVE / "participant" / "input" if split != "audit" else ARCHIVE / "evaluator" / "hidden"
        with np.load(destination / f"{split}_features.npz", allow_pickle=False) as archive:
            features = {key: archive[key] for key in archive.files}
        with np.load(ARCHIVE / "evaluator" / "hidden" / f"{split}_latent.npz", allow_pickle=False) as archive:
            latent = {key: archive[key] for key in archive.files}
        splits[split] = features, latent
    decompositions = []
    features, latent = splits["audit"]
    for index, family in enumerate(latent["family"]):
        active = generator.active_parameters(int(family))
        forward = jacobian(lambda parameters: generator.whiten(generator.clean_observations(parameters, int(family)), features["sigma"][index]), latent["parameters"][index], active)
        left, singular, right = np.linalg.svd(forward, full_matrices=False)
        decompositions.append((active, singular, right))
    records = []
    for resolution in (.04, .06):
        generator.RESOLUTION = resolution
        targets = {split: np.stack([sheet_mass(parameters, int(family)) for parameters, family in zip(latent["parameters"], latent["family"])])
                   for split, (features, latent) in splits.items()}
        responses = []
        features, latent = splits["audit"]
        for index, family in enumerate(latent["family"]):
            responses.append(jacobian(lambda parameters: sheet_mass(parameters, int(family)), latent["parameters"][index], decompositions[index][0]) @ decompositions[index][2].T)
        for factor in (100., 300., 600.):
            changed = {split: latent["clean"] + factor * (features["observed"] - latent["clean"])
                       for split, (features, latent) in splits.items()}
            prediction = np.zeros_like(targets["validation"])
            for bands in (2, 3):
                train_mask = (splits["train"][1]["family"] == 3) == (bands == 3)
                valid_mask = (splits["validation"][1]["family"] == 3) == (bands == 3)
                reference_sigma = np.median(splits["train"][0]["sigma"][train_mask], axis=0) * factor
                raw = baseline.fit_predict(changed["train"][train_mask], targets["train"][train_mask, :bands].reshape(train_mask.sum(), -1),
                                           changed["validation"][valid_mask], reference_sigma, generator.CORRELATION)
                prediction[valid_mask, :bands] = baseline.simplex(raw.reshape(valid_mask.sum(), bands, 14))
            families = splits["validation"][1]["family"]
            squared = ((prediction - targets["validation"]) / generator.MASS_SCALES) ** 2
            errors = np.sqrt(squared.sum(axis=(1, 2)) / (14 * np.where(families == 3, 3, 2)))
            grouped = [float(np.mean(errors[families == family])) for family in range(4)]
            prior_errors = []
            for index, (response, decomposition) in enumerate(zip(responses, decompositions)):
                bands = 3 if splits["audit"][1]["family"][index] == 3 else 2
                variance = np.sum(response ** 2 / ((decomposition[1] / factor) ** 2 + 12), axis=1)
                prior_errors.append(float(np.sqrt(np.sum(variance / np.tile(generator.MASS_SCALES, 3) ** 2) / (14 * bands))))
            record = dict(resolution=resolution, noise_min=factor * 1.e-6, noise_max=factor * 4.e-6,
                          core=float(np.mean(errors)), worst=max(grouped), family_errors=grouped,
                          local_prior_mean=float(np.mean(prior_errors)), local_prior_max=max(prior_errors))
            records.append(record)
            print(json.dumps(record), flush=True)
            (ROOT / "evaluator" / "hidden" / "v2_sheet_final_grid.json").write_text(json.dumps(dict(
                rationale="Momentum/sheet-resolved coherence and satellite weights are not identifiable by mere continuation of a probe average; original mass scales retained per normalized sheet",
                topology="number of Fermi sheets is an additional public structural feature, no family or mixture weights supplied",
                grid="eta {.04,.06} and noise factors {100,300,600}; original T=.04; validation only; bounded final grid",
                records=records), indent=2) + "\n")


if __name__ == "__main__":
    main()
