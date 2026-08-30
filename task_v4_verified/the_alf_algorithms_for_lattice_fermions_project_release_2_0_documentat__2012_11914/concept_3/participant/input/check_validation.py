"""Score predictions against public validation labels."""

import argparse
import json
from pathlib import Path

import numpy as np

from scoring import score_prediction


def load(path):
    with np.load(path, allow_pickle=False) as archive:
        return {name: archive[name] for name in archive.files}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("prediction")
    arguments = parser.parse_args()
    directory = Path(__file__).resolve().parent
    print(json.dumps(score_prediction(
        load(arguments.prediction),
        load(directory / "validation_input.npz"),
        load(directory / "validation_labels.npz"),
    ), indent=2))
