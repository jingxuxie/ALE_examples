import numpy as np

from observables import schmidt_spectra
from refine import infer_charges
from trusted_contractor import canonicalize


def diagnostics(tensors, request, energy):
    spectra = schmidt_spectra(canonicalize(tensors))
    result = {
        "center_entropy": spectra[len(tensors) // 2 - 1]["entropy"],
        "max_entropy": max(entry["entropy"] for entry in spectra),
        "schmidt": spectra,
        "max_cutoff_edge_population": None,
        "full_residual_diagnostics_computed": False,
    }
    try:
        charges = infer_charges(tensors, request)
        result["bond_charge_counts"] = [
            {"cut": cut, "even": int(np.sum(charge == 0)),
             "odd": int(np.sum(charge == 1))}
            for cut, charge in enumerate(charges)
        ]
    except ValueError as error:
        result["charge_gauge_diagnostic_error"] = str(error)
    return result
