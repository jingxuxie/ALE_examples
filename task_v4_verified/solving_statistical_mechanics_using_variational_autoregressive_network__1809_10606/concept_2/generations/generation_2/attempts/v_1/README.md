# Exhaustively verified mode-B witness

`witness.json` is the submission. It uses the supplied frustrated bond system
and spin order, with optimized strictly lower-triangular logistic weights and
inverse temperature `1.4297178597693243`. The antipodal sector has radius 4.

## Exact numerical results

Every sum includes all 65,536 configurations; no proposal probabilities are
clipped, removed, or renormalized.

| Metric | Measured | Required |
| --- | ---: | ---: |
| Entropy | 3.557944800468276 | >= 3 |
| Reverse KL | 2.090970746304371 | >= 0.4 |
| Dimensionless reward variance | 0.008444917329754 | <= 0.05 |
| Ambient gradient infinity norm | 0.000812040077591 | <= 0.003 |
| Dimensionless energy error per spin | 0.004513372577164 | <= 0.02 |
| Target antipodal-sector mass | 0.456052433587253 | >= 0.35 |
| Proposal antipodal-sector mass | 0.000398197779043 | <= 0.001 |

There are 12 frustrated plaquettes. The largest weight-row L1 norm is
`6.906754778548555`, below `ln(999) = 6.906754778648554`. The smallest enumerated
binary conditional probability is `0.0010000000000998986`. Proposal
normalization is `1.0000000000000002`, and the maximum global spin-flip
symmetry error is zero. The sector contains 5,034 configurations.

Thus a sector carrying over 45.6% of the equilibrium probability receives
less than 0.040% of the proposal probability, despite small exact variance,
gradient, and mean-energy error. The positive variance does not contradict
the full-support zero-variance identity.

## Verification and construction

Run from this directory with Python, NumPy, and SciPy:

```
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B verify.py witness.json --report verification.json
```

`verify.py` independently reconstructs the lattice, checks the JSON schema
and structural bounds, enumerates the full state space, and checks all seven
gates. It additionally checks three ambient gradient entries with central
finite differences, including the largest-magnitude entry. The machine-readable
results are in `verification.json`; these are local verification results, not
a report from the separate evaluator.

`exact.py` contains the original enumeration and sector-search implementation.
`optimize.py` minimizes the exact reward variance with SLSQP, using positive
and negative weight parts for linear row-L1 constraints and simultaneous
entropy, KL, energy, and sector constraints. The construction retains the
baseline bonds, spin order, pattern, and radius; only beta and the weights
change. The supplied candidate is the result after 400 iterations. SLSQP
reached its iteration limit rather than certifying an optimum; optimality is
not needed, and both exhaustive implementations agree that every gate passes.

To reproduce the optimization, pass the supplied baseline JSON as the source:

```
python -B optimize.py /path/to/participant/baseline/witness.json --output reproduced.json --maxiter 400
```
