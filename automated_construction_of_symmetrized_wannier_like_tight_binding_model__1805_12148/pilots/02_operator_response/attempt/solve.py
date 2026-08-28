#!/usr/bin/env python3
"""Repair real-space Hamiltonian/position data and compute orbital responses."""

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np

from response import responses
from symmetry import project_operators


def solve(case_path):
    case_path = Path(case_path)
    with (case_path / "case.json").open() as handle:
        metadata = json.load(handle)
    with np.load(case_path / "model.npz", allow_pickle=False) as archive:
        payload = {name: archive[name] for name in archive.files}
    occupied = int(metadata["occupied"])
    energies, berry_raw, optical_raw = responses(payload, occupied)
    repaired = project_operators(payload)
    repaired_payload = dict(payload, **repaired)
    _, berry_repaired, optical_repaired = responses(repaired_payload, occupied)
    return dict(
        repaired, energies=energies, berry_raw=berry_raw, optical_raw=optical_raw,
        berry_repaired=berry_repaired, optical_repaired=optical_repaired,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    result = solve(arguments.input)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("wb") as handle:
        np.savez_compressed(handle, **result)


if __name__ == "__main__":
    main()
