"""Slow inference-only reference; intentionally not a certified champion."""

import argparse
import json
from pathlib import Path
import sys

import numpy as np

from inference import dictionary, infer


parser = argparse.ArgumentParser()
parser.add_argument("--input", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
arguments = parser.parse_args()
with np.load(arguments.input, allow_pickle=False) as archive:
    observed, sigma, sheets = archive["observed"], archive["sigma"], archive["sheet_count"]
bank = dictionary()
predictions = []
for index in range(len(observed)):
    mass, diagnostic, fits = infer(observed[index], sigma[index], bank, sheet_count=int(sheets[index]))
    predictions.append(mass)
    print(json.dumps(dict(case=index, diagnostic=diagnostic)), file=sys.stderr, flush=True)
np.savez_compressed(arguments.output, spectral_mass=np.asarray(predictions))
