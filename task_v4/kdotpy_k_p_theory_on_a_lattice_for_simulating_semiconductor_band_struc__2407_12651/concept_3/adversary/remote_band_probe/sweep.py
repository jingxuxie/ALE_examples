import hashlib
import json
import os
from pathlib import Path

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

from remote_model import ROOT, FAMILIES, assemble, band_metrics, coordinate_grid, evaluate_fourier, manufacture


def fhs(matrices):
    spectrum, vectors = np.linalg.eigh(matrices)
    states = vectors[..., :, 0]
    link_x = np.einsum("...i,...i->...", states.conj(), np.roll(states, -1, axis=0))
    link_y = np.einsum("...i,...i->...", states.conj(), np.roll(states, -1, axis=1))
    flux = np.angle(link_x * np.roll(link_y, -1, axis=0) * np.conj(np.roll(link_x, -1, axis=1)) * np.conj(link_y))
    return {"chern": float(flux.sum() / (2 * np.pi)), "maximum_flux": float(np.abs(flux).max()), "minimum_overlap": float(min(np.abs(link_x).min(), np.abs(link_y).min())), "minimum_active_weight": float(np.min(np.sum(np.abs(states[..., :2])**2, axis=-1)))}


def main():
    directory = Path(__file__).resolve().parent
    sources = {"private_author": ROOT / "attempts/topological_search/trial_7.json", "fresh1_champion": ROOT / "champions/generation_1/submission/witness.json"}
    records = []
    horizontal, vertical = coordinate_grid(81)
    for label, path in sources.items():
        witness = json.loads(path.read_text())
        for family in FAMILIES:
            for strength in (0.0, 0.5, 0.75, 0.9, 1.0, 1.2):
                hoppings = assemble(witness, family, strength)
                nominal = evaluate_fourier(hoppings, horizontal, vertical)
                metrics = band_metrics(np.linalg.eigvalsh(nominal))
                topology = fhs(nominal)
                cases = []
                for mass_error in (-0.05, 0.0, 0.05):
                    for anisotropy in (-0.06, 0.0, 0.06):
                        cases.append(band_metrics(np.linalg.eigvalsh(manufacture(nominal, horizontal, vertical, mass_error, anisotropy))))
                record = {"source": label, "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "family": family, "strength": strength, "nominal": metrics, "topology": topology, "sampled_worst_width": max(case["bandwidth"] for case in cases), "sampled_min_direct": min(case["direct_above"] for case in cases), "sampled_min_indirect": min(case["indirect_above"] for case in cases), "sampled_min_gap12": min(case["gap_12"] for case in cases), "hermiticity_residual": float(np.max(np.abs(nominal - nominal.conj().swapaxes(-1, -2))))}
                records.append(record)
                print(json.dumps(record), flush=True)
    (directory / "sweep.json").write_text(json.dumps({"families": FAMILIES, "mesh": 81, "records": records}, indent=2) + "\n")


if __name__ == "__main__":
    main()
