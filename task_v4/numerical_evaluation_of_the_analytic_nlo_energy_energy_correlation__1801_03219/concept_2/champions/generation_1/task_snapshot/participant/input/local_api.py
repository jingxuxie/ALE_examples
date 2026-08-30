"""Public screening API. Its floating reference is diagnostic, not ground truth."""

import argparse
import json
import math
from pathlib import Path

import numpy as np

from problem import FAMILIES, Kernel, load_witness, validate
from target import integrate


def refined(kernel, witness, order, panels):
    nodes, weights = np.polynomial.legendre.leggauss(order)
    points = ((np.arange(panels)[:, None] + (nodes[None, :] + 1) / 2) / panels).ravel()
    weights = np.tile(weights / (2 * panels), panels)
    values = [kernel.integrand(witness, family)(points) for family in FAMILIES]
    return [(float(np.dot(weights, value)), float(np.dot(weights, np.abs(value)))) for value in values]


def measure(witness, trace=False, kernel=None):
    validate(witness)
    kernel = kernel or Kernel()
    coarse = refined(kernel, witness, 32, 32)
    fine = refined(kernel, witness, 48, 64)
    results = {}
    for channel, family in enumerate(FAMILIES):
        target = integrate(kernel.integrand(witness, family), trace=trace)
        reference, absolute = fine[channel]
        refinement_gap = abs(reference - coarse[channel][0])
        observed = abs(target["value"] - reference)
        screening_margin = observed / max(20 * target["tolerance"], 50 * target["estimated_error"], 1e-5 * absolute)
        results[family] = {"target": target, "screen_reference": reference, "screen_l1": absolute,
                           "screen_refinement_gap": refinement_gap,
                           "screen_error": observed,
                           "screen_margin": screening_margin if target["converged"] else 0.0}
    return {"families": results, "worst_screen_margin": min(result["screen_margin"] for result in results.values()),
            "warning": "Binary64 refined screening only. Passing this API is not independent source/high-precision certification."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission")
    parser.add_argument("--report")
    parser.add_argument("--trace", action="store_true")
    args = parser.parse_args()
    report = measure(load_witness(args.submission), trace=args.trace)
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.report:
        Path(args.report).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
