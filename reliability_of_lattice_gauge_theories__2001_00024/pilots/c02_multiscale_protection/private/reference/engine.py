import os
import pathlib
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("NUMBA_CACHE_DIR", "/tmp/ale_reference_numba")
ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "authoring" / "runtime"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "participant" / "workspace"))

import numpy as np
import quimb.tensor as qtn
from scipy.optimize import least_squares
from dense_cluster import initial_indices, local_terms, simulate


def infer_parameters(case):
    def residual(parameters):
        values = []
        for record in case["calibration"]:
            predicted = simulate(record["settings"], parameters, record["times"], record["pairs"])
            for name in ("density", "violation", "correlation"):
                values.extend((np.asarray(predicted[name]) - np.asarray(record["observed"][name])).ravel())
        return np.array(values)
    fits = []
    for guess in ([0.1, 0.1, 0.0], [0.23, 0.2, -0.1], [0.04, 0.06, 0.15]):
        fits.append(least_squares(residual, guess, bounds=([0.025, 0.025, -0.25], [0.3, 0.3, 0.25]), xtol=1e-11, ftol=1e-11, gtol=1e-11))
    fit = min(fits, key=lambda entry: entry.cost)
    return fit.x.tolist(), {"residual": float(np.linalg.norm(fit.fun)), "jacobian_singular_values": np.linalg.svd(fit.jac, compute_uv=False).tolist()}


def predict(settings, parameters, times, pairs, step=0.025, bond=64, cutoff=1e-10, order=4):
    start = time.monotonic()
    sites, bonds, gauss, operators = local_terms(settings, parameters)
    local_dim = len(operators["identity"])
    state = qtn.MPS_product_state([np.eye(local_dim)[index] for index in initial_indices(settings)])
    hamiltonian = qtn.LocalHam1D(settings["length"], H2=bonds, H1=sites, cyclic=False)
    evolution = qtn.TEBD(state, hamiltonian, dt=step, split_opts={"max_bond": bond, "cutoff": cutoff}, progbar=False)
    output = {"density": [], "violation": [], "correlation": []}
    max_bond = 1
    for current_time in times:
        evolution.update_to(float(current_time), order=order, progbar=False)
        state = evolution.pt
        state.normalize()
        density_terms = {(site,): operators["number"] for site in range(settings["length"])}
        density_values = state.compute_local_expectation(density_terms, return_all=True)
        density = [float(np.real(density_values[site,])) for site in range(settings["length"])]
        violation_terms = {(0,): gauss[0]}
        violation_terms.update({(site - 1, site): gauss[site] for site in range(1, settings["length"])})
        violation_values = state.compute_local_expectation(violation_terms, return_all=True)
        violation = [float(np.real(violation_values[(0,) if site == 0 else (site - 1, site)])) for site in range(settings["length"])]
        correlations = [float(np.real(state.correlation(operators["number"], left, right))) for left, right in pairs]
        output["density"].append(density)
        output["violation"].append(violation)
        output["correlation"].append(correlations)
        max_bond = max(max_bond, state.max_bond())
    output["parameters"] = list(parameters)
    return output, {"seconds": time.monotonic() - start, "max_bond": max_bond, "step": step, "bond_limit": bond, "cutoff": cutoff, "order": order}


def solve(case):
    parameters, _ = infer_parameters(case)
    return predict(case["experiment"], parameters, case["times"], case["pairs"])[0]
