"""Must be rejected: correct archive keys but a NaN spectral mass."""

import sys

import numpy as np


with np.load(sys.argv[1], allow_pickle=False) as archive:
    identifiers = archive["sample_id"]
    bins = len(archive["omega_edges"]) - 1
mass = np.full((len(identifiers), bins), 1.0 / bins)
mass[0, 0] = np.nan
np.savez_compressed(sys.argv[2], sample_id=identifiers, spectral_mass=mass, low_mass_quantiles=np.zeros((len(identifiers), 3)))
