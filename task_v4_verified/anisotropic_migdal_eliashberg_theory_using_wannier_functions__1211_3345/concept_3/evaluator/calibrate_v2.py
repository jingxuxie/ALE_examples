"""Authorized bounded prelaunch calibration; public validation scores only."""

import json
import hashlib
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "adversary" / "prelaunch_v1"
sys.path.insert(0, str(ROOT / "adversary" / "prelaunch_v1" / "participant" / "input"))
sys.path.insert(0, str(ROOT / "adversary" / "prelaunch_v1" / "participant" / "baseline"))
import generator
import solve as baseline
from evaluate import score, target_configuration
from identifiability import jacobian


def main():
    archived_target = (ARCHIVE / "evaluator" / "hidden" / "target.json").read_bytes()
    configuration, target_hash = json.loads(archived_target), hashlib.sha256(archived_target).hexdigest()
    splits = {}
    for split in ("train", "validation", "audit"):
        public = ARCHIVE / "participant" / "input" if split != "audit" else ARCHIVE / "evaluator" / "hidden"
        with np.load(public / f"{split}_features.npz", allow_pickle=False) as archive:
            features = {key: archive[key] for key in archive.files}
        with np.load(ARCHIVE / "evaluator" / "hidden" / f"{split}_latent.npz", allow_pickle=False) as archive:
            latent = {key: archive[key] for key in archive.files}
        splits[split] = features, latent
    original_splits = splits
    records = []
    for temperature in (.16, .4, .8):
        resolution = .12
        omega = (2 * generator.INDICES + 1) * np.pi * temperature
        splits = {}
        for split, (features, latent) in original_splits.items():
            standard_noise = (features["observed"] - latent["clean"]) / features["sigma"]
            ratio = (.6 + .4 / (1 + omega / 6)) / (.6 + .4 / (1 + generator.OMEGA / 6))
            changed_sigma = features["sigma"] * ratio
            clean = np.stack([generator.clean_observations(parameters, int(family), omega)
                              for parameters, family in zip(latent["parameters"], latent["family"])])
            splits[split] = ({"sigma": changed_sigma, "observed": clean + changed_sigma * standard_noise},
                             dict(latent, clean=clean))
        derivatives = []
        features, latent = splits["audit"]
        for index, family in enumerate(latent["family"]):
            active = generator.active_parameters(int(family))
            function = lambda parameters: generator.whiten(generator.clean_observations(parameters, int(family), omega), features["sigma"][index])
            forward = jacobian(function, latent["parameters"][index], active)
            left, singular, right = np.linalg.svd(forward, full_matrices=False)
            derivatives.append((active, singular, right))
        generator.RESOLUTION = resolution
        labels = {}
        for split in ("train", "validation"):
            latent = splits[split][1]
            labels[split] = np.stack([generator.target_mass(parameters, int(family))
                                      for parameters, family in zip(latent["parameters"], latent["family"])])
        responses = []
        latent = splits["audit"][1]
        for index, family in enumerate(latent["family"]):
            response = jacobian(lambda parameters: generator.target_mass(parameters, int(family)),
                                latent["parameters"][index], derivatives[index][0])
            responses.append(response @ derivatives[index][2].T)
        for factor in (1., 10., 100.):
            data = {}
            for split in ("train", "validation"):
                features, latent = splits[split]
                data[split] = latent["clean"] + factor * (features["observed"] - latent["clean"])
            reference_sigma = np.median(splits["train"][0]["sigma"], axis=0) * factor
            predicted = baseline.fit_predict(data["train"], labels["train"].reshape(len(data["train"]), -1),
                                             data["validation"], reference_sigma, generator.CORRELATION)
            predicted = baseline.simplex(predicted.reshape(labels["validation"].shape))
            metrics = score(predicted, labels["validation"], splits["validation"][1]["family"], configuration)
            prior_errors, unconstrained_errors = [], []
            for response, derivative in zip(responses, derivatives):
                singular = derivative[1] / factor
                scales = np.tile(generator.MASS_SCALES, 2)
                variance = np.sum(response ** 2 / (singular ** 2 + 12), axis=1)
                free_variance = np.sum((response / np.maximum(singular, 1.e-14)) ** 2, axis=1)
                prior_errors.append(float(np.sqrt(np.mean(variance / scales ** 2))))
                unconstrained_errors.append(float(np.sqrt(np.mean(free_variance / scales ** 2))))
            record = dict(temperature=temperature, resolution=resolution, noise_min=1.e-6 * factor, noise_max=4.e-6 * factor,
                          public_validation=metrics, local_prior_mean=float(np.mean(prior_errors)),
                          local_prior_max=max(prior_errors), local_unconstrained_max=max(unconstrained_errors),
                          local_prior_case_errors=prior_errors)
            records.append(record)
            print(json.dumps(record), flush=True)
            report = dict(authorization="explicit user authorization for pre-tournament redesign, 2026-08-28",
                          grid="T in {.16,.4,.8}; eta=.12; noise factor in {1,10,100}; original window scales unchanged",
                          baseline_data="public train and validation cases only, paired noise rescaling",
                          v1_target_sha256=target_hash, records=records,
                          limitation="local Gaussian prior approximation is diagnostic, not a global or predictive proof")
            (ROOT / "evaluator" / "hidden" / "v2_frequency_calibration.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
