import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import time

for variable in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ[variable] = "1"

import mpmath as mp
import numpy as np
from scipy.linalg import expm
from scipy.special import expit


ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "adversary/champion_audit_v1"


def mp_matrix(instance, labels):
    size = math.prod(instance["shape"])
    matrices = {label: mp.zeros(size) for label in labels}
    for label, source, target, amplitude, phase in instance["bonds"]:
        value = -mp.mpf(str(amplitude)) * mp.exp(mp.j * mp.mpf(str(phase)))
        matrices[label][source, target] += value
        matrices[label][target, source] += mp.conj(value)
    for index, value in enumerate(instance["site_potential"]):
        matrices["V"][index, index] = mp.mpf(str(value))
    return matrices


def mp_layer(instance, label, weight):
    size = math.prod(instance["shape"])
    result = mp.eye(size)
    if label == "V":
        for index, value in enumerate(instance["site_potential"]):
            result[index, index] = mp.exp(-weight * mp.mpf(str(value)))
        return result
    for component, source, target, amplitude, phase in instance["bonds"]:
        if component != label:
            continue
        angle = weight * mp.mpf(str(amplitude))
        result[source, source] = mp.cosh(angle)
        result[target, target] = mp.cosh(angle)
        result[source, target] = mp.sinh(angle) * mp.exp(mp.j * mp.mpf(str(phase)))
        result[target, source] = mp.conj(result[source, target])
    return result


def mp_product(instance, stages, step):
    size = math.prod(instance["shape"])
    result = mp.eye(size)
    for stage in stages:
        result = result * mp_layer(instance, stage["component"], step * mp.mpf(str(stage["coefficient"])))
    return (result + result.H) / 2


def mp_green_positive(propagator, repeats):
    values, vectors = mp.eighe(propagator)
    if min(values) <= 0:
        raise ArithmeticError("positive product lost positivity even in high precision")
    return vectors * mp.diag([1 / (1 + mp.exp(repeats * mp.log(value))) for value in values]) * vectors.H


def verify(instance, candidate, baseline, step, repeats, digits):
    mp.mp.dps = digits
    step = mp.mpf(str(step))
    components = mp_matrix(instance, ["X0", "X1", "Y0", "Y1", "V"])
    total = sum(components.values(), mp.zeros(math.prod(instance["shape"])))
    values, vectors = mp.eighe(total)
    exact = vectors * mp.diag([mp.exp(-repeats * step * value) for value in values]) * vectors.H
    exact_green = vectors * mp.diag([1 / (1 + mp.exp(-repeats * step * value)) for value in values]) * vectors.H
    errors = {}
    for name, stages in (("candidate", candidate), ("baseline", baseline)):
        product = mp_product(instance, stages, step)
        repeated = product ** repeats
        green = mp_green_positive(product, repeats)
        errors[name] = {"propagator": mp.norm(repeated - exact) / mp.norm(exact), "green": mp.norm(green - exact_green) / mp.norm(exact_green)}
    return {"digits": digits, "dtau": float(step), "repetitions": repeats, "case_id": instance["id"], "relative_errors": {name: {observable: mp.nstr(value, 45) for observable, value in entries.items()} for name, entries in errors.items()}, "ratios": {observable: mp.nstr(errors["candidate"][observable] / errors["baseline"][observable], 45) for observable in ("propagator", "green")}}


def check_double(instance, candidate, baseline, step, repeats):
    dimension = math.prod(instance["shape"])
    components = {label: np.zeros((dimension, dimension), dtype=complex) for label in ("X0", "X1", "Y0", "Y1", "V")}
    for label, source, target, amplitude, phase in instance["bonds"]:
        components[label][source, target] += -amplitude * np.exp(1j * phase)
        components[label][target, source] += -amplitude * np.exp(-1j * phase)
    components["V"] = np.diag(instance["site_potential"]).astype(complex)
    values, vectors = np.linalg.eigh(sum(components.values()))
    exact = (vectors * np.exp(-repeats * step * values)) @ vectors.conj().T
    exact_green = (vectors * expit(repeats * step * values)) @ vectors.conj().T
    result = {}
    for name, stages in (("candidate", candidate), ("baseline", baseline)):
        product = np.eye(dimension, dtype=complex)
        for stage in stages:
            product = product @ expm(-step * stage["coefficient"] * components[stage["component"]])
        product = (product + product.conj().T) / 2
        spectrum, eigenvectors = np.linalg.eigh(product)
        stable = (eigenvectors * expit(-repeats * np.log(spectrum))) @ eigenvectors.conj().T
        repeated = np.linalg.matrix_power(product, repeats)
        direct = np.linalg.inv(np.eye(dimension) + repeated)
        result[name] = {"propagator": float(np.linalg.norm(repeated - exact) / np.linalg.norm(exact)), "green_spectral": float(np.linalg.norm(stable - exact_green) / np.linalg.norm(exact_green)), "green_direct_inverse": float(np.linalg.norm(direct - exact_green) / np.linalg.norm(exact_green)), "direct_vs_spectral_green_relative": float(np.linalg.norm(direct - stable) / np.linalg.norm(stable)), "condition_I_plus_P_power": float(np.linalg.cond(np.eye(dimension) + repeated)), "minimum_single_step_eigenvalue": float(spectrum.min())}
    return result


def main():
    global DIRECTORY
    parser = argparse.ArgumentParser()
    parser.add_argument("--regime", default="larger_steps")
    parser.add_argument("--digits", type=int, default=70)
    parser.add_argument("--count", type=int, default=2)
    parser.add_argument("--directory", type=Path, default=DIRECTORY)
    parser.add_argument("--dtau", type=float)
    arguments = parser.parse_args()
    DIRECTORY = arguments.directory
    started = time.monotonic()
    fixtures = json.loads((DIRECTORY / (arguments.regime + "_worst_fixtures.json")).read_text())
    candidate_bytes = (DIRECTORY / "candidate.json").read_bytes()
    candidate = json.loads(candidate_bytes)["stages"]
    baseline = json.loads((DIRECTORY / "baseline.json").read_text())["stages"]
    reports = []
    for record in fixtures["worst_records"][:arguments.count]:
        instance = next(instance for instance in fixtures["instances"] if instance["id"] == record["case_id"])
        step = arguments.dtau if arguments.dtau is not None else record["dtau"]
        report = verify(instance, candidate, baseline, step, record["repetitions"], arguments.digits)
        report["broad_scan_record"] = record
        report["independent_scipy_expm_check"] = check_double(instance, candidate, baseline, step, record["repetitions"])
        reports.append(report)
        print(json.dumps(report), flush=True)
        output = {"candidate_sha256": hashlib.sha256(candidate_bytes).hexdigest(), "mpmath_version": mp.__version__, "oracle": "Independent arbitrary-precision full 33-stage analytic bond exponentials; Hermitian eigendecomposition of H and of the complete P; Fermi functions of log eigenvalues, never a direct inverse for the reference.", "reports": reports, "elapsed_wall_seconds": time.monotonic() - started}
        suffix = "" if arguments.dtau is None else "_h_" + str(arguments.dtau)
        (DIRECTORY / (arguments.regime + suffix + "_high_precision.json")).write_text(json.dumps(output, indent=2) + "\n")


if __name__ == "__main__":
    main()
