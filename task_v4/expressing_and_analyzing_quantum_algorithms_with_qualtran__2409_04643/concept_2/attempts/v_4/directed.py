import json
import time
from pathlib import Path

import numpy as np

from checker import audit_pair, evaluate
from search import screen
from target_method import fft_complementary_polynomial


def serialize(values):
    return [[float(value.real), float(value.imag)] for value in values]


def main():
    rng = np.random.default_rng(153573)
    best = 0
    started = time.monotonic()
    for batch in range(100):
        count = 1024
        length = 15
        dominant_energy = rng.uniform(0.86, 0.893, count)
        leading = rng.uniform(0.250001, 0.27, count) / np.sqrt(length)
        other = np.sqrt((1 - dominant_energy - leading ** 2) / (length - 2))
        phases = rng.integers(0, 2, (count, length)) * np.pi + np.pi / 2 + rng.normal(0, 0.2, (count, length))
        polynomials = other[:, None] * np.exp(1j * phases)
        polynomials[:, -2] = np.sqrt(dominant_energy)
        polynomials[:, -1] = leading * np.exp(1j * phases[:, -1])
        crest = np.max(abs(np.fft.fft(polynomials, n=4096, axis=-1)), axis=-1)
        norm = rng.uniform(0.72, 0.79, count)
        polynomials *= (norm / crest)[:, None]
        energy = np.sum(abs(polynomials) ** 2, axis=-1)
        valid = (energy >= 0.08) & (energy <= 0.3) & (abs(np.sum(polynomials ** 2, axis=-1)) <= 0.8 * energy)
        errors, margins, leaders = screen(polynomials)
        errors[~valid | (margins < 1e-8)] = 0
        print("SCREEN", batch, "max", errors.max(), "quantiles", np.quantile(errors, [0.5, 0.9, 0.99]), "elapsed", time.monotonic() - started, flush=True)
        for selected in np.argsort(errors)[-30:][::-1]:
            if errors[selected] < max(0.01, best / 2):
                break
            polynomial = polynomials[selected]
            records = audit_pair(polynomial)
            admissible = all(record["completion_valid"] and record["guard_valid"] for record in records)
            minimum = min(record["rms_error"] for record in records) if admissible else 0
            print("AUDIT", minimum, [record["rms_error"] for record in records], "guards", min(record["phase_guard_margin"] for record in records), flush=True)
            if minimum > best:
                best = minimum
                certificate = 0.8 * fft_complementary_polynomial(polynomial / 0.8, tolerance=0, num_modes=65536)
                Path("counterexample.json").write_text(json.dumps({"P": serialize(polynomial), "H": serialize(certificate)}))
                result = evaluate(Path("."))
                Path("best_report.json").write_text(json.dumps(result, indent=2))
                print("BEST", best, result["reason"], flush=True)
                if result["passed"]:
                    return


if __name__ == "__main__":
    main()
