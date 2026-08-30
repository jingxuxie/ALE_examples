import functools
import json
from pathlib import Path

import numpy as np

import solver


def main():
    original_oscillator = solver.oscillator
    records = []
    for sites in (2, 3):
        for mass in (-4.2, -3.5, -1.4, 3.5):
            for coupling in (0.12, 0.56, 1.0):
                solver.oscillator = original_oscillator
                primary = solver.solve(mass, coupling, sites, count=16)
                solver.oscillator = functools.partial(original_oscillator, omega=1.4)
                reference = solver.solve(mass, coupling, sites, count=20)
                errors = np.abs(np.log(primary / reference))
                record = {
                    "sites": sites,
                    "mass": mass,
                    "coupling": coupling,
                    "primary_gaps": primary.tolist(),
                    "reference_gaps": reference.tolist(),
                    "errors": errors.tolist(),
                    "above_admission_gap_floor": bool(np.min(reference) >= 1e-6),
                }
                records.append(record)
                print(sites, mass, coupling, errors, flush=True)
    admitted = [record for record in records if record["above_admission_gap_floor"]]
    maximum = max(max(record["errors"]) for record in admitted)
    result = {"maximum_log_difference_above_floor": maximum, "records": records}
    Path("convergence_results.json").write_text(json.dumps(result, indent=2) + "\n")
    print("MAXIMUM ABOVE FLOOR", maximum, flush=True)


if __name__ == "__main__":
    main()
