"""A fixed-state exclusion identity, explicitly not a universal task proof."""

import json
import sys
from pathlib import Path

import numpy as np

PACKET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKET / "participant" / "workspace"))
sys.path.insert(0, str(PACKET / "evaluator" / "hidden"))
from oracle import DeterminantCC
from independent import IndependentSystem


def compression(positive, negative, reference, targets, multipliers, ground):
    right = positive @ reference
    bra = reference.copy()
    bra[targets] = multipliers
    left = bra @ negative
    normal = negative[-1]
    overlap_right, overlap_left = right @ ground, left @ ground
    coefficient = np.array([[right @ right - overlap_right * right[-1] / ground[-1], 1],
                            [1, left @ left - overlap_left * (normal @ left) / (normal @ ground)]])
    gram = np.array([[right @ right - overlap_right ** 2, 1 - overlap_right * overlap_left],
                     [1 - overlap_right * overlap_left, left @ left - overlap_left ** 2]])
    return coefficient, gram, {"biorthogonal_error": abs(left @ right - 1),
        "left_triple": float(left[-1]), "normal_right_error": abs(normal @ right),
        "ground_triple": float(ground[-1]), "normal_ground": float(normal @ ground)}


def main():
    data = json.loads((PACKET / "authoring" / "relaxed_bounds_lower_best.json").read_text())
    amplitudes = np.array(data["amplitudes"])
    multipliers = np.array(data["multipliers"])
    ground = np.array(data["ground_vector"])
    ground /= np.linalg.norm(ground)
    public = DeterminantCC()
    positive, negative = public.exponentials(amplitudes)
    coefficient, gram, invariants = compression(positive, negative, public.ref, public.targets, multipliers, ground)
    trusted = IndependentSystem()
    _, _, _, trusted_positive, trusted_negative = trusted.equations(np.zeros((20, 20)), amplitudes)
    trusted_coefficient, trusted_gram, _ = compression(trusted_positive, trusted_negative, trusted.ref, trusted.targets, multipliers, ground)
    exclusion = coefficient[0, 0] < 0 and coefficient[1, 1] > 0 and gram[0, 0] > 0 and gram[1, 1] > 0
    report = {"scope": "the single stored relaxed state only; NOT all permitted stationary CCSD states",
              "fixed_state_excluded": bool(exclusion), "coefficient_matrix": coefficient.tolist(),
              "projected_gram_matrix": gram.tolist(), "normalization_checks": invariants,
              "independent_coefficient_max_error": float(np.max(abs(coefficient - trusted_coefficient))),
              "independent_gram_max_error": float(np.max(abs(gram - trusted_gram))),
              "identity": "If H is Hermitian and psi its gapped ground state, stationary CCSD requires e*B >= gap*G on span(right,left), with e=E_CC-E_FCI. The opposite signs of B's two diagonal entries and strictly positive diagonals of G require e<0 and e>0 simultaneously.",
              "task_infeasibility_proved": False,
              "interpretation": "This explains why the near-optimal kinematic relaxation collapsed to a zero-gap Hamiltonian under inverse construction. It is not a lower bound over all states or a finite-probe impossibility result."}
    (PACKET / "authoring" / "relaxed_state_exclusion.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
