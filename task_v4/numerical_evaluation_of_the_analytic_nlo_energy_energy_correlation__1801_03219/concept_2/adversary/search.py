"""Privileged, reproducible near-nullspace search; never imported by grading."""

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from scipy.linalg import svd
from scipy.optimize import linprog


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/input"))
from problem import BINS, COLOR, FAMILIES, Kernel, QUANTUM, basis, response, validate
from target import GWEIGHTS, KWEIGHTS, NODES, integrate


def save(relative, data):
    destination = ROOT / relative
    text = json.dumps(data, indent=2) + "\n"
    if destination.exists():
        subprocess.run(["apply_patch", "*** Begin Patch\n*** Delete File: " + str(destination) + "\n*** End Patch\n"], check=True, stdout=subprocess.DEVNULL)
    patch = "*** Begin Patch\n*** Add File: " + str(destination) + "\n" + "".join("+" + line + "\n" for line in text.splitlines()) + "*** End Patch\n"
    subprocess.run(["apply_patch"], input=patch, text=True, check=True, stdout=subprocess.DEVNULL)


def matrices(kernel, witness):
    left, right = BINS[witness["bin"]]

    def stencil(panel_left, panel_right, weights, nodes=NODES):
        half = (panel_right - panel_left) / 2
        points = (panel_left + panel_right) / 2 + half * nodes
        spectra = 2 * (right - left) * kernel(left + (right - left) * points) * COLOR
        modes = response(points, witness)[:, None] * basis(points, witness)
        return half * np.einsum("n,nc,nk->ck", weights, spectra, modes)

    coarse = np.array([stencil(index / 4, (index + 1) / 4, KWEIGHTS) for index in range(4)])
    fine = np.array([stencil(index / 8, (index + 1) / 8, KWEIGHTS) for index in range(8)])
    embedded = np.array([stencil(index / 8, (index + 1) / 8, KWEIGHTS - GWEIGHTS) for index in range(8)])
    parent = fine.reshape(4, 2, 3, 24).sum(axis=1) - coarse
    constraints = np.concatenate((embedded, parent), axis=0).transpose(1, 0, 2)
    reference_nodes, reference_weights = np.polynomial.legendre.leggauss(40)
    reference = sum(stencil(index / 32, (index + 1) / 32, reference_weights, reference_nodes) for index in range(32))
    error = fine.sum(axis=0) - reference
    return constraints, error, reference


def quantize(template, vector):
    vector = np.asarray(vector)
    coefficients = np.rint(vector / np.abs(vector).sum() * (QUANTUM - 48)).astype(np.int64)
    witness = dict(template)
    witness["cosine"] = coefficients[:12].tolist()
    witness["sine"] = coefficients[12:].tolist()
    validate(witness)
    return witness


def assess(kernel, witness, reference):
    coefficients = np.array(witness["cosine"] + witness["sine"], dtype=float) / QUANTUM
    results = []
    for channel, family in enumerate(FAMILIES):
        result = integrate(kernel.integrand(witness, family))
        result["reference_screen"] = float(reference[channel] @ coefficients)
        result["error_screen"] = abs(result["value"] - result["reference_screen"])
        result["margin_screen"] = result["error_screen"] / max(20 * result["tolerance"], 50 * result["estimated_error"], 1e-5 * result["sampled_l1"])
        if not result["converged"]:
            result["margin_screen"] = 0.0
        results.append(result)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-configs", type=int, default=159)
    args = parser.parse_args()
    started = time.monotonic()
    kernel = Kernel()
    frozen = {name: hashlib.sha256((ROOT / "participant/input" / name).read_bytes()).hexdigest() for name in ("target.py", "problem.py", "kernel.json")}
    save("adversary/presearch_hashes.json", frozen)
    records = []
    best = -1.0
    attempts = 0
    configurations = [(bin_name, frequency, tilt, curvature) for tilt, curvature in [(0, 0), (-4, 4), (4, -4)]
                      for frequency in range(53, 20, -1) for bin_name in ("central", "backward", "collinear")]
    for bin_name, frequency, tilt, curvature in configurations[:args.max_configs]:
        template = {"version": 1, "bin": bin_name, "band_start": frequency, "tilt": tilt, "curvature": curvature}
        constraints, error, reference = matrices(kernel, template)
        row_scale = np.maximum(np.max(np.abs(constraints), axis=2, keepdims=True), 1e-12)
        matrix = (constraints / row_scale).reshape(-1, 24)
        _, singular, right_vectors = svd(matrix, full_matrices=False)
        candidates = [right_vectors[-index] for index in range(1, 5)]
        for count in (3, 6, 10):
            subspace = right_vectors[-count:].T
            for channel in range(3):
                candidates.append(subspace @ (subspace.T @ error[channel]))
        for bound in (1e-10, 1e-9, 1e-8):
            raw = constraints.reshape(-1, 24)
            for channel in range(3):
                inequalities = np.block([[raw, -raw], [-raw, raw], [np.ones((1, 24)), np.ones((1, 24))]])
                limits = np.concatenate((np.full(2 * len(raw), bound), [1.0]))
                solution = linprog(np.concatenate((-error[channel], error[channel])), A_ub=inequalities, b_ub=limits,
                                   bounds=(0, None), method="highs", options={"dual_feasibility_tolerance": 1e-9, "primal_feasibility_tolerance": 1e-9})
                if solution.success:
                    candidates.append(solution.x[:24] - solution.x[24:])
        for vector in candidates:
            if not np.any(vector):
                continue
            try:
                witness = quantize(template, vector)
            except ValueError:
                continue
            results = assess(kernel, witness, reference)
            margin = min(result["margin_screen"] for result in results)
            attempts += 1
            if margin > best:
                best = margin
                save("adversary/best_screen/witness.json", witness)
                save("adversary/best_screen/screen.json", {"margin": margin, "results": results, "singular_values": singular.tolist()})
                print(json.dumps({"attempt": attempts, "bin": bin_name, "band": frequency, "best_margin": best,
                                  "panels": [result["panels"] for result in results],
                                  "errors": [result["error_screen"] for result in results]}), flush=True)
            if best > 3:
                break
        records.append({"bin": bin_name, "band": frequency, "tilt": tilt, "curvature": curvature,
                        "smallest_singular": float(singular[-1]), "best_margin": best})
        if best > 3:
            break
    save("adversary/search_outcomes.json", {"attempts": attempts, "seconds": time.monotonic() - started,
                                          "best_screen_margin": best, "configurations": records,
                                          "warning": "Screening uses refined binary64 quadrature, NOT the acceptance reference. A screened witness is not yet certified."})


if __name__ == "__main__":
    main()
