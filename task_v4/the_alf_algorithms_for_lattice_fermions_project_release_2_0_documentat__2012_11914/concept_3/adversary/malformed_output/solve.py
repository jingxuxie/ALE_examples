"""Must be rejected: output contains an untrusted extra runtime field."""

import sys

import numpy as np


with np.load(sys.argv[1], allow_pickle=False) as archive:
    identifiers = archive["sample_id"]
    bins = len(archive["omega_edges"]) - 1
np.savez_compressed(sys.argv[2], sample_id=identifiers, spectral_mass=np.full((len(identifiers), bins), 1.0 / bins), low_mass_quantiles=np.zeros((len(identifiers), 3)), runtime_seconds=np.array(0.0))
