import hashlib
import json
import os
from pathlib import Path
import sys

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evaluator"))
import reference as core
import remote_reference as remote
from remote_model import assemble, evaluate_fourier


def derivative_checks(witness):
    generator = np.random.default_rng(7351)
    horizontal, vertical = generator.uniform(-np.pi, np.pi, (2, 17))
    hoppings = remote.fourier_hoppings(witness)
    matrices = evaluate_fourier(hoppings, horizontal, vertical)
    rotation = np.diag([1.0, 1j, 1.0, 1j])
    rotated = evaluate_fourier(hoppings, -vertical, horizontal)
    covariance_error = float(np.max(np.abs(rotated-rotation@matrices@rotation.conj().T)))
    assert covariance_error < 2e-13
    energies, vectors = np.linalg.eigh(matrices)
    state = vectors[..., :, 0]
    denominators = energies[:, :1]-energies
    denominators[:, 0] = 1.0
    projectors = state[:, :, None]*state[:, None, :].conj()
    records = []
    analytic_gradients = []
    finite_gradients = []
    for coordinate in (0, 1):
        derivative = evaluate_fourier(hoppings, horizontal, vertical, coordinate)
        transformed = np.einsum("pai,pab,pbj->pij", vectors.conj(), derivative, vectors)
        weights = transformed[:, :, 0]/denominators
        weights[:, 0] = 0.0
        gradient = np.einsum("pim,pm->pi", vectors, weights)
        analytic_gradients.append(gradient)
        predicted_projector = gradient[:, :, None]*state[:, None, :].conj()+state[:, :, None]*gradient[:, None, :].conj()
        step = 5e-5
        arguments = [horizontal, vertical]
        plus_arguments, minus_arguments = list(arguments), list(arguments)
        plus_arguments[coordinate] = arguments[coordinate]+step
        minus_arguments[coordinate] = arguments[coordinate]-step
        plus = evaluate_fourier(hoppings, *plus_arguments)
        minus = evaluate_fourier(hoppings, *minus_arguments)
        plus_energy, plus_vectors = np.linalg.eigh(plus)
        minus_energy, minus_vectors = np.linalg.eigh(minus)
        plus_state, minus_state = plus_vectors[:, :, 0], minus_vectors[:, :, 0]
        plus_projector = plus_state[:, :, None]*plus_state[:, None, :].conj()
        minus_projector = minus_state[:, :, None]*minus_state[:, None, :].conj()
        for neighbor in (plus_state, minus_state):
            overlap = np.einsum("pi,pi->p", state.conj(), neighbor)
            neighbor *= (overlap.conj()/np.abs(overlap))[:, None]
        finite_gradient = (plus_state-minus_state)/(2*step)
        finite_gradients.append(finite_gradient)
        errors = {"hamiltonian_derivative": float(np.max(np.abs((plus-minus)/(2*step)-derivative))), "hellmann_feynman": float(np.max(np.abs((plus_energy[:, 0]-minus_energy[:, 0])/(2*step)-transformed[:, 0, 0]))), "eigenvector_parallel_gauge": float(np.max(np.abs(finite_gradient-gradient))), "spectral_projector": float(np.max(np.abs((plus_projector-minus_projector)/(2*step)-predicted_projector)))}
        assert max(errors.values()) < 2e-7, errors
        records.append(errors)
    analytic_berry = 2*np.imag(np.einsum("pi,pi->p", analytic_gradients[0].conj(), analytic_gradients[1]))
    finite_berry = 2*np.imag(np.einsum("pi,pi->p", finite_gradients[0].conj(), finite_gradients[1]))
    residual = float(np.max(np.abs(matrices@vectors-vectors*energies[:, None, :])))
    assert residual < 1e-12
    assert np.max(np.abs(analytic_berry-finite_berry)) < 2e-7
    decoupled = evaluate_fourier(assemble(witness, "parity_mixed", 0.0), horizontal, vertical)
    active = core.matrix_values(core.fourier_hoppings(witness), horizontal, vertical)
    np.testing.assert_allclose(np.linalg.eigvalsh(decoupled)[:, :2], np.linalg.eigvalsh(active), atol=2e-14)
    return {"coordinate_errors": records, "full_kubo_vs_phase_aligned_fd_error": float(np.max(np.abs(analytic_berry-finite_berry))), "eigenpair_residual": residual, "c4_covariance_error": covariance_error, "decoupled_control": "pass"}


def main():
    directory = Path(__file__).resolve().parent
    config = json.loads((ROOT / "participant/input/model.json").read_text())
    results = {}
    for label, relative in (("private_author", "attempts/topological_search/trial_7.json"), ("fresh1_champion", "champions/generation_1/submission/witness.json")):
        path = ROOT / relative
        witness = json.loads(path.read_text())
        spectral = remote.spectral_certificate(witness, config, 161)
        topology = remote.topology_certificate(witness, 128)
        shifted = remote.topology_certificate(witness, 128, (0.317, 0.419), 981)
        assert spectral["certified"] and spectral["certified_direct_gap"]>0 and spectral["certified_indirect_gap"]>0 and spectral["certified_gap12_lower"]>0
        assert topology["certified"] and shifted["certified"] and topology["chern"] == -1
        results[label] = {"source": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "spectral": spectral, "topology": topology, "shifted_topology": shifted, "derivatives": derivative_checks(witness)}
        print(label, "width", spectral["certified_bandwidth"], "gap01", spectral["certified_direct_gap"], "gap12", spectral["certified_gap12_lower"], "homotopy", topology["homotopy_gap_lower"], flush=True)
    (directory / "validation.json").write_text(json.dumps(results, indent=2)+"\n")
    print("All remote-model controls passed.")


if __name__ == "__main__":
    main()
