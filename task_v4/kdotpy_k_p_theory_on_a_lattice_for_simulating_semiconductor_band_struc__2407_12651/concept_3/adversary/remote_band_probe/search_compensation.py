import json
import os
from pathlib import Path
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evaluator"))
sys.path.insert(0, str(ROOT / "participant/workspace"))
from model import features, pack, unpack
import remote_reference as remote
from remote_model import coordinate_grid, manufacture


horizontal, vertical = coordinate_grid(25)
horizontal, vertical = horizontal.ravel(), vertical.ravel()
offset, basis = features(horizontal, vertical)
base = remote.matrix_values(remote.fourier_hoppings(unpack(np.zeros(30))), horizontal, vertical)
errors = [(mass, strain) for mass in (-0.05, 0.0, 0.05) for strain in (-0.06, 0.0, 0.06)]


def spectra(parameters):
    values = np.einsum("pij,j->pi", basis, parameters)
    nominal = base.copy()
    nominal[:, 0, 0] += values[:, 0]+values[:, 3]
    nominal[:, 1, 1] += values[:, 0]-values[:, 3]
    nominal[:, 0, 1] += values[:, 1]-1j*values[:, 2]
    nominal[:, 1, 0] += values[:, 1]+1j*values[:, 2]
    energies, gradients = [], []
    for mass, strain in errors:
        energy, vectors = np.linalg.eigh(manufacture(nominal, horizontal, vertical, mass, strain))
        orbital0, orbital1 = vectors[:, 0, :2], vectors[:, 1, :2]
        cross = orbital0.conj()*orbital1
        observables = np.stack((np.abs(orbital0)**2+np.abs(orbital1)**2, 2*cross.real, 2*cross.imag, np.abs(orbital0)**2-np.abs(orbital1)**2), axis=-1)
        gradients.append(np.einsum("pbi,pij->pbj", observables, basis))
        energies.append(energy[:, :2])
    return np.array(energies), np.array(gradients)


def optimize(initial, support):
    support = np.array(sorted(support), dtype=int)
    parameters = np.zeros(30)
    parameters[support] = initial[support]
    bounds = [(-1.9, -0.3) if index == 0 else (-1.5, 1.5) if 12 <= index < 21 else (-0.75, 0.75) for index in support]
    for temperature in (0.015, 0.004, 0.0012):
        def objective(selected):
            current = parameters.copy()
            current[support] = selected
            energy, gradient = spectra(current)
            lower = energy[..., 0]
            highest, lowest = lower.max(axis=1), lower.min(axis=1)
            high_weight = np.exp((lower-highest[:, None])/temperature)
            low_weight = np.exp((lowest[:, None]-lower)/temperature)
            widths = highest-lowest+temperature*(np.log(high_weight.sum(axis=1))+np.log(low_weight.sum(axis=1)))
            high_weight /= high_weight.sum(axis=1, keepdims=True)
            low_weight /= low_weight.sum(axis=1, keepdims=True)
            scenarios = np.exp((widths-widths.max())/temperature)
            scenarios /= scenarios.sum()
            loss = float(widths.max()+temperature*np.log(np.exp((widths-widths.max())/temperature).sum()))
            derivative = np.einsum("s,sp,spj->j", scenarios, high_weight-low_weight, gradient[..., 0, :])
            gaps = energy[..., 1]-energy[..., 0]
            gap_temperature = min(0.001, temperature)
            gap_weight = np.exp((gaps.min()-gaps)/gap_temperature)
            gap_soft = float(gaps.min()-gap_temperature*np.log(gap_weight.sum()))
            gap_weight /= gap_weight.sum()
            slack = max(3.055-gap_soft, 0.0)
            loss += 70*slack**2+0.002*np.sum(np.sqrt(current[1:]**2+1e-9))
            derivative -= 140*slack*np.einsum("sp,spj->j", gap_weight, gradient[..., 1, :]-gradient[..., 0, :])
            derivative[1:] += 0.002*current[1:]/np.sqrt(current[1:]**2+1e-9)
            return loss, derivative[support]
        result = minimize(objective, parameters[support], jac=True, bounds=bounds, method="L-BFGS-B", options={"maxiter": 140, "ftol": 2e-11, "maxls": 25})
        parameters[support] = result.x
    return parameters


def main():
    directory = Path(__file__).resolve().parent
    initial = pack(json.loads((ROOT / "champions/generation_1/submission/witness.json").read_text()))
    generator = np.random.default_rng(1742)
    config = json.loads((ROOT / "participant/input/model.json").read_text())
    started = time.monotonic()
    records = []
    for trial in range(3):
        starting = initial.copy()
        starting[1:] += generator.normal(0, 0.035 if trial else 0, 29)
        full = optimize(starting, range(30))
        support = [0]+(np.argsort(np.abs(full[1:]))[-8:]+1).tolist()
        fitted = optimize(full, support)
        witness = unpack(fitted)
        certificate = remote.spectral_certificate(witness, config, 161)
        record = {"trial": trial, "support": support, "elapsed_seconds": time.monotonic()-started, "certificate": certificate}
        records.append(record)
        (directory/f"compensated_{trial}.json").write_text(json.dumps(witness, indent=2)+"\n")
        (directory/"compensation_search.json").write_text(json.dumps(records, indent=2)+"\n")
        print(json.dumps({key: value for key, value in record.items() if key != "certificate"}), {key: value for key, value in certificate.items() if key.startswith("certified_")}, flush=True)


if __name__ == "__main__":
    main()
