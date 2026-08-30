# Finite phi4 gap submission

The submission entry point is `predict.py`. It is self-contained apart from
NumPy and SciPy and requires no model files, training-time preprocessing,
network, external commands, or child processes.

```sh
python predict.py --input INPUT.json --train TRAIN.json --output OUTPUT.json
```

The `--train` argument is accepted for interface compatibility. Predictions
come directly from the specified Hamiltonian, not a fitted regression model.
Only the physical parameters and chain length are needed from each input.

## Numerical method

Set `s = (lambda / 6)^(1/3)`, `r = mu2/s^2`, and `j = kappa/s^2`.
With `phi = x/sqrt(s)` and `pi = sqrt(s)*p`, the Hamiltonian divided by `s`
has local potential `r*x^2/2 + x^4/4` and bond term `j*(x_next-x)^2/2`.

Each bond's diagonal quadratic terms are included in its endpoint local
Hamiltonians. Each local Hamiltonian is diagonalized separately in its even
and odd sectors using an 80-state oscillator basis at frequency 2. The
position powers are formed before projection, retaining the required
`P*x^2*P` and `P*x^4*P` convention. The lowest eight states of each local
parity are retained, producing an interacting local basis of dimension 16.

The product Hamiltonian consists of the local diagonal energies and the
remaining interactions `-j*x_i*x_next`. Its two global parity sectors are
assembled as sparse matrices. Deterministically initialized Lanczos solves
return the lowest two energies per sector at tolerance `1e-12`. Their
differences give the three requested gaps, which are multiplied by `s`.

## Public checks

- All 192 labelled training cases were checked at local dimension 16:
  mean absolute log error `6.01e-11`, maximum `1.35e-8`.
- The final entry point was run on all 48 public validation cases:
  mean absolute log error `1.24e-10`, worst-family mean `7.45e-10`,
  pooled 95th percentile `5.55e-11`, maximum `8.24e-9`.
- The stated score formula on public validation gives `0.9999999944`.
  This is a local calculation, not a hidden-set evaluation.
- Output schema, exact ID coverage, and strictly positive finite targets
  were checked for the validation output.
- A balanced 72-case batch drawn from the public training cases completed
  under enforced 30-second CPU and 2-GiB address-space limits:
  12.31 CPU seconds, 13.37 wall seconds, and 71,548 KiB peak resident memory.
- `convergence_check.py` additionally compares local dimensions 16 and 20
  with independently chosen oscillator frequencies 2.0 and 1.4 at 24
  parameter-domain boundary/interior points. The maximum absolute log
  difference at points above the declared admission gap floor is `2.54e-9`.

The JSON metric files, predictions, resource logs, and convergence results
are retained alongside the entry point. `solver.py` and `check.py` are
development utilities and are not imported by `predict.py`.
