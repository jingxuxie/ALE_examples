import json
import sys
from pathlib import Path
import numpy as np
from scipy.linalg import eigh
from scipy.optimize import brentq


ROOT = Path(__file__).resolve().parents[1] / 'concept_01'
sys.path.insert(0, str(ROOT / 'solution/v_01/workspace'))
from transport.model import matrices, extend


def main():
    case = json.loads((ROOT / 'evaluator/hidden/cases.json').read_text())['cases'][2]
    central, leads = matrices(case)
    lower = min(cell[0, 0].real - 2 * abs(hop[0, 0]) for cell, hop, contact in leads)
    upper = max(cell[0, 0].real + 2 * abs(hop[0, 0]) for cell, hop, contact in leads)
    def embedded(energy):
        effective = central.copy()
        derivative = np.zeros_like(central)
        for cell, hop, contact in leads:
            displacement = energy - cell[0, 0].real
            hopping = abs(hop[0, 0])
            root = np.sign(displacement) * np.sqrt(displacement ** 2 - 4 * hopping ** 2)
            surface = (displacement - root) / (2 * hopping ** 2)
            slope = (1 - displacement / root) / (2 * hopping ** 2)
            effective += contact @ contact.conj().T * surface
            derivative += contact @ contact.conj().T * slope
        return energy * np.eye(len(central)) - effective, derivative
    poles = []
    for begin, end in [(lower - 8, lower - 1e-12), (upper + 1e-12, upper + 8)]:
        for branch in range(len(central)):
            def residual(energy):
                return np.linalg.eigvalsh(embedded(energy)[0])[branch]
            if residual(begin) * residual(end) < 0:
                energy = brentq(residual, begin, end, xtol=2e-14)
                matrix, derivative = embedded(energy)
                values, vectors = eigh(matrix)
                vector = vectors[:, np.argmin(abs(values))]
                normalization = float(np.vdot(vector, (np.eye(len(central)) - derivative) @ vector).real)
                density = abs(vector) ** 2 / normalization
                poles.append(dict(energy=energy, central_probability=float(np.sum(density)), density=density.tolist(), residual=float(np.min(abs(values)))))
    reference = np.load(ROOT / 'evaluator/hidden/gold/ring_holdout.npz')['density'][0]
    participant = np.load(ROOT / 'screening/v_01/fresh_01/evaluation/hidden_run/withheld_2.npz')['density'][0]
    result = dict(poles=poles, participant_minus_reference=(participant - reference).tolist())
    for pole in poles:
        pole['difference_match_max_error'] = float(np.max(abs(np.asarray(pole['density']) - (participant - reference))))
    (ROOT / 'screening/independent_ring_poles.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
