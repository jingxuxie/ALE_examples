#!/usr/bin/env python3
"""Repair a complete Wannier model and evaluate original/repaired responses."""

import argparse
import json
from pathlib import Path

import numpy as np

from operators import project_operators
from response import responses


def solve(case_path):
    case_path = Path(case_path)
    with (case_path / "case.json").open() as source:
        metadata = json.load(source)
    with np.load(case_path / "model.npz", allow_pickle=False) as archive:
        payload = {name: archive[name] for name in archive.files}
    occupied = int(metadata["occupied"])
    energies, berry_raw, optical_raw = responses(payload, occupied)
    result = project_operators(payload)
    repaired = dict(payload, **result)
    _, berry_repaired, optical_repaired = responses(repaired, occupied)
    result.update(
        energies=energies,
        berry_raw=berry_raw,
        optical_raw=optical_raw,
        berry_repaired=berry_repaired,
        optical_repaired=optical_repaired,
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    result = solve(arguments.input)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("wb") as destination:
        np.savez_compressed(destination, **result)


if __name__ == "__main__":
    main()
