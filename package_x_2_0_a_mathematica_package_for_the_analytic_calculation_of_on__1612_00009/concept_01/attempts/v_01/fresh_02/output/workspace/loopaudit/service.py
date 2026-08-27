import time

import numpy as np

from .contract import decode, encode
from .backend import evaluate


def run_cases(payload, settings):
    records = []
    for case in payload["cases"]:
        started = time.perf_counter()
        integrals = {}
        for integral in case["integrals"]:
            integrals[integral["id"]] = evaluate(integral, settings)
        observables = {}
        for observable in case.get("observables", []):
            assembly_started = time.perf_counter()
            combined = np.zeros(4, dtype=complex)
            absolute_error = 0.0
            for term in observable["terms"]:
                values = decode(integrals[term["integral"]]["coefficients"][term.get("order", "base")])
                factors = list(map(float, term.get("epsilon_polynomial", [1]))) + [0, 0]
                combined += np.array([factors[0] * values[0], factors[0] * values[1],
                                      factors[0] * values[2] + factors[1] * values[1],
                                      factors[0] * values[3] + factors[1] * (values[0] + values[2])
                                      + factors[2] * values[1]])
                absolute_error += (sum(abs(factor) for factor in factors) * max(abs(values))
                                   * integrals[term["integral"]]["estimated_error"])
            scale = max(float(observable.get("normalization", 1)), 1e-300)
            observables[observable["id"]] = {"values": encode(combined),
                                            "residual": float(np.max(np.abs(combined)) / scale),
                                            "seconds": time.perf_counter() - assembly_started,
                                            "work": len(observable["terms"]),
                                            "estimated_error": float(absolute_error / scale),
                                            "strategy": "Laurent-convolution-before-truncation"}
        records.append({"id": case["id"], "family": case.get("family", "unspecified"),
                        "integrals": integrals, "observables": observables,
                        "seconds": time.perf_counter() - started})
    return {"schema": 1, "cases": records}
