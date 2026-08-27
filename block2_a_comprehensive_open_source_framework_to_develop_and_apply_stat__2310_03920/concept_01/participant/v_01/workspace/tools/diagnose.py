import csv
import json
from pathlib import Path
import sys
import numpy as np
from scipy.integrate import cumulative_trapezoid


def diagnostics(directory):
    with (Path(directory) / 'trajectory.csv').open() as handle:
        rows = list(csv.DictReader(handle))
    values = {column: np.array([float(row[column]) for row in rows]) for column in rows[0]}
    charge_change = values['charge'] - values['charge'][0]
    rate_integral = cumulative_trapezoid(values['current'] + values['source'], values['time'], initial=0)
    return {'norm_drift': float(np.ptp(values['norm'])), 'energy_drift': float(np.ptp(values['energy'])),
            'number_change': float(np.ptp(values['number'])), 'spin_change': float(np.ptp(values['spin'])),
            'continuity_quadrature_residual': float(np.max(np.abs(charge_change - rate_integral))),
            'warning': 'Continuity includes time-grid quadrature error. Conserved values do not certify the Hamiltonian or state.'}


if __name__ == '__main__':
    print(json.dumps(diagnostics(sys.argv[1]), indent=2))
