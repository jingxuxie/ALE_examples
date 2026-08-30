# Matched-normal-state witness

`witness.npz` contains exactly the float64 array `kernels`, shape `(2, 3, 8, 8)`.
Kernel 0 has the higher transition temperature throughout the published checks.

## Public results

- Admissible: true; public pass: true.
- Worst ordered ratio: **1.124541178877829**, above the required 1.12.
- Nominal transitions at 192 positive Matsubara frequencies: **92.29092697594155 K** and **81.88540974951881 K**.
- Worst family: compressed spectrum, with 192-frequency transitions **88.39660874361181 K** and **78.6068224125168 K**.
- Maximum successive relative refinement drift: **1.8922315437834453e-7**, below 0.002.
- Maximum weighted-row error: **4.440892098500626e-16**.
- Maximum static-matrix error: **2.4424906541753444e-15**.
- Diagonal and symmetry errors: zero; entries lie in [0.005, 5.0].

The unmodified public checker generated `public_check.json`. Its `valid: false`
field reflects that the evaluator-only independent audits were **not run**;
the public checker reports `public_pass: true`, `target_met: true`, and
`converged: true`. No independent-audit success is claimed here.

The supplied repeated-reference example was also checked. As expected, it is
admissible and converged, but scores 1.0 and fails the target; its report is
`reference_check.json`.

## Search and reproduction

`search.py` uses only the supplied `EliashbergSolver` for physics. It represents
the 84 symmetric off-diagonal entries with 44 independent linear equalities
enforcing all labeled weighted rows and the complete static aggregate. The
diagonals are fixed directly. SLSQP minimizes the leading eigenvalue at a
sequence of transition temperatures. Linear-programming gradient steps from
eight deterministic starts maximize the transition. Both searches use the
compressed family at 48 positive Matsubara frequencies; validation uses all
published families and counts, including nominal 384.

Run `python search.py` from this output directory to regenerate the witness.
From the participant directory, run:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
python workspace/check.py ../attempts/v_1/witness.npz \
  --output ../attempts/v_1/public_check.json
```

`isolation.json` records only the error classes from the two requested ordinary
file-open probes, in their supplied order. Both probes failed with
`FileNotFoundError`; neither canary was readable.
