"""Author-only source consistency and physical reference checks; no solver runs."""

import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np

REFERENCE = Path(__file__).resolve().parent
sys.path.insert(0, str(REFERENCE))
from physics import ForwardModel, PARTICLE_HOLE, load_result, pfaffian_phase


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true")
    arguments = parser.parse_args()
    private = REFERENCE.parent
    request = json.loads((private / "challenge_pool" / "matched_1300" / "request.json").read_text())
    masks = load_result(request, REFERENCE / "matched_1300.json")
    scenario = {"mu_normal_mev": 10.0, "zeeman_mev": 0.5}
    model = ForwardModel(request, masks, scenario)
    started = time.monotonic()
    matrix = model.hamiltonian(0.0)
    particle_hole = np.kron(np.eye(3), PARTICLE_HOLE)
    small_request = json.loads(json.dumps(request))
    small_request["grid"].update(nx=5, ny=3)
    small_top = np.zeros((3, 5), dtype=bool)
    small_top[-1] = True
    small_bottom = np.zeros((3, 5), dtype=bool)
    small_bottom[0] = True
    small = ForwardModel(small_request, {"sc_top": small_top, "sc_bottom": small_bottom}, scenario)
    conjugation = np.kron(np.eye(5), particle_hole)
    dense_phases = [pfaffian_phase(small.hamiltonian(momentum).toarray() @ conjugation) for momentum in (0, np.pi)]
    dense_invariant = -1 if (dense_phases[0] * dense_phases[1]).real < 0 else 1
    assert small.topological_invariant() == dense_invariant
    ph_error = np.max(np.abs(conjugation @ small.hamiltonian(0).toarray().conj() @ conjugation + small.hamiltonian(0).toarray()))
    assert ph_error < 1e-9
    energies, _ = model.low_energy(0.0)
    invariant = model.topological_invariant()
    report = {"dimension": model.dimension, "hermiticity_error": float(abs(matrix - matrix.getH()).max()), "small_particle_hole_error": float(ph_error), "dense_vs_block_pfaffian_agrees": True, "energies_at_zero_mev": energies.tolist(), "class_d_invariant": invariant, "seconds": time.monotonic() - started, "full_source_comparison": False}
    if arguments.full:
        spectrum = model.spectral_gap(np.linspace(0, np.pi, 51))
        stored = float(np.load(REFERENCE / "matched_1300_stored_outputs.npz")["grid_gaps"].ravel()[0])
        report.update(full_source_comparison=True, source_gap_mev=stored, measured=spectrum, absolute_gap_error_mev=abs(spectrum["gap_mev"] - stored))
        if report["absolute_gap_error_mev"] > 0.0005:
            raise RuntimeError(f"Forward model does not reproduce stored author gap: {report}")
    (REFERENCE / "forward_check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
