"""Expensive feature-only domain portfolio; no hidden labels or latents read."""

import os
from pathlib import Path
import sys

import numpy as np
from scipy.optimize import least_squares


PUBLIC = Path(os.environ.get("ALE_PUBLIC_INPUT", Path(__file__).resolve().parents[2] / "participant" / "input"))
sys.path.insert(0, str(PUBLIC))
import generator


def dictionary(per_family=96):
    random = np.random.default_rng(730921)
    families = np.repeat(np.arange(4), per_family)
    parameters = random.uniform(0, 1, (len(families), generator.PARAMETER_COUNT))
    features = np.stack([generator.clean_observations(latent, int(family))
                         for latent, family in zip(parameters, families)])
    return parameters, families, features


def infer(observed, sigma, bank, starts=2, max_evaluations=90):
    bank_parameters, bank_families, bank_features = bank
    distances = np.sum(generator.whiten(bank_features - observed, sigma) ** 2, axis=(1, 2, 3))
    fits = []
    for family in range(4):
        active = generator.active_parameters(family)
        eligible = np.flatnonzero(bank_families == family)
        selected = eligible[np.argsort(distances[eligible])[:starts]]
        for initial in selected:
            template = bank_parameters[initial].copy()

            def residual(active_parameters):
                full_parameters = template.copy()
                full_parameters[active] = active_parameters
                clean = generator.clean_observations(full_parameters, family)
                return generator.whiten(clean - observed, sigma).ravel()

            result = least_squares(residual, template[active], bounds=(0, 1),
                                   max_nfev=max_evaluations, ftol=2.e-7, xtol=1.e-7, gtol=1.e-5,
                                   diff_step=2.e-5, x_scale="jac")
            latent = template.copy()
            latent[active] = result.x
            chi_square = float(np.sum(residual(result.x) ** 2))
            fits.append(dict(family=family, parameters=latent, chi_square=chi_square,
                             evaluations=int(result.nfev), mass=generator.target_mass(latent, family)))
    fits.sort(key=lambda item: item["chi_square"])
    minimum = fits[0]["chi_square"]
    accepted = [fit for fit in fits if fit["chi_square"] <= minimum + 9]
    weights = np.exp(-.5 * np.array([fit["chi_square"] - minimum for fit in accepted]))
    weights /= weights.sum()
    mass = sum(weight * fit["mass"] for weight, fit in zip(weights, accepted))
    details = dict(best_chi_square=minimum, best_family=fits[0]["family"],
                   accepted_fits=len(accepted),
                   fits=[dict(family=fit["family"], chi_square=fit["chi_square"], evaluations=fit["evaluations"])
                         for fit in fits])
    return mass, details, fits
