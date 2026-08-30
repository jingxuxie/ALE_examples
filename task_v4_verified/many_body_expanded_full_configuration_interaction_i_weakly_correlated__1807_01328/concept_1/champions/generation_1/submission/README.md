# Adaptive correlation-energy policy

Run `python3 solution.py`. The process reads and writes the specified JSON-lines
protocol, flushes each action, and exits successfully on `done`.

## Method

The policy acquires all 56 three-virtual energies, forms exact low-order Möbius
increments, and selects 26 four-virtual experiments using their estimated
higher-order uncertainty. The total query cost is exactly 160 units per system;
no experiment includes more than four virtual orbitals.

Small NumPy neural networks predict unobserved fourth- and fifth-order
increments. For the more difficult families, regularized inverse paired-electron
Hamiltonian fits refine this prediction. Fits use analytic response derivatives,
exact observed-energy constraints, multiple initializations when necessary, and
an exact replacement of measured increments. Poorly fitted models fall back to
the statistical estimate. A process-wide CPU guard limits expensive searches.

## Runtime files

- `solution.py`: persistent protocol executable.
- `acquisition.py`, `experiment.py`, `neural.py`, `physical.py`: numerical helpers.
- `network4.npz`, `network5.npz`: frozen NumPy network parameters.

Only Python, NumPy, and SciPy are required at inference time. The other scripts,
data archives, and logs are construction and validation scratch work. Training
uses only new draws from the supplied simulator; no hidden assets are used.

## Validation

`final_practice.json` records the supplied 36-system protocol test: 4.7134
microhartree overall RMSE, 11.3000 microhartree worst-family RMSE, maximum cost
160, and a valid, passing protocol run. Further independent-sample reports are
stored alongside this file. These measurements do not guarantee hidden-set
performance.
