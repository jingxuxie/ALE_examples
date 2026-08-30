"""Private local identifiability diagnostic, never an oracle predictor."""

import json
import hashlib
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "input"))
import generator


def jacobian(function, parameters, active):
    columns = []
    for index in active:
        shifted = parameters.astype(complex)
        shifted[index] += 1.e-20j
        columns.append(np.imag(function(shifted)).ravel() / 1.e-20)
    return np.stack(columns, axis=1)


def local_case(parameters, family, sigma, resolution):
    generator.RESOLUTION = resolution
    active = generator.active_parameters(family)
    forward = lambda latent: generator.whiten(generator.clean_observations(latent, family), sigma)
    target = lambda latent: generator.target_mass(latent, family)
    information = jacobian(forward, parameters, active)
    response = jacobian(target, parameters, active)
    left, singular, right = np.linalg.svd(information, full_matrices=False)
    projected = response @ right.T
    unconstrained_std = np.sqrt(np.sum((projected / np.maximum(singular, 1.e-14)) ** 2, axis=1))
    prior_std = np.sqrt(np.sum(projected ** 2 / (singular ** 2 + 12), axis=1))
    scales = np.tile(generator.MASS_SCALES, 3)
    active_count = (3 if family == 3 else 2) * len(generator.MASS_SCALES)
    return dict(family=int(family), resolution_hwhm=resolution,
                smallest_whitened_singular=float(singular[-1]),
                largest_whitened_singular=float(singular[0]),
                local_unconstrained_rms_in_score_units=float(np.sqrt(np.sum((unconstrained_std / scales) ** 2) / active_count)),
                local_prior_rms_in_score_units=float(np.sqrt(np.sum((prior_std / scales) ** 2) / active_count)),
                local_prior_max_window_std=float(np.max(prior_std)),
                local_unconstrained_max_window_std=float(np.max(unconstrained_std)),
                number_of_weak_directions=int(np.sum(singular < 1)))


def main():
    hidden = ROOT / "evaluator" / "hidden"
    with np.load(hidden / "audit_latent.npz", allow_pickle=False) as archive:
        parameters, families = archive["parameters"], archive["family"]
    with np.load(hidden / "audit_features.npz", allow_pickle=False) as archive:
        sigma = archive["sigma"]
    cases = []
    for index, family in enumerate(families):
        cases.append(local_case(parameters[index], int(family), sigma[index], generator.RESOLUTION))
        print(index, family, cases[-1]["local_prior_rms_in_score_units"], flush=True)
    report = dict(target_sha256=hashlib.sha256((hidden / "target.json").read_bytes()).hexdigest(),
                  method="complex-step local Fisher, exact disclosed finite family and correlated noise",
                  role="diagnostic only: true latent locations used for derivatives, never predictive evidence",
                  covariance="both unconstrained linearized inverse and Gaussianized Uniform[0,1] prior precision 12I",
                  caveats=["local linearization is not a global uniqueness certificate",
                           "weak singular directions can leave latent parameters unidentified without spoiling window masses",
                           "the regularized prior diagnostic alone is not an attainability proof",
                           "no cases were filtered using this audit"],
                  cases=cases,
                  maximum_local_prior_rms=max(case["local_prior_rms_in_score_units"] for case in cases),
                  maximum_local_unconstrained_rms=max(case["local_unconstrained_rms_in_score_units"] for case in cases))
    (hidden / "identifiability_local.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
