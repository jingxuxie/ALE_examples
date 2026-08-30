# Executable and mathematical contract

The real number-conserving Hamiltonian is

`H = sum(p,q) h[p,q] a†[p] a[q] + 1/2 sum(k) (sum(p,q) B[k,p,q] a†[p] a[q])²`.

Every `h` and `B[k]` is symmetric. Choose real orthogonal `U` (n by n) and `W`
(r by r). Define `h_new = U.T @ h @ U` and
`B_new[k] = sum(l) W[k,l] * U.T @ B[l] @ U`.
The exact cost is

`C = sum(abs(h_new)) + 0.5 * sum(k) sum(abs(B_new[k]))**2`.

This is a coefficient-based LCU normalization proxy, not spectral norm or
energy error. No truncation or nonorthogonal changes are allowed. Each
orthogonality Frobenius residual must be at most `1e-7`.

`REQUEST.json` contains `cases` and `seconds_per_case=10`. Each case contains
`id`, `family`, `one_body`, `factors`, and `baseline_cost`. The response contains
`solutions`, exactly one object per case with `id`, `orbital`, and `auxiliary`.
All numbers must be finite. Dimensions are 14–16 modes and 12–14 factors.

Cases are independent Hamiltonians from a competing-locality family: different
localized positive charge-operator factors can have different orbital frames,
with dense external orbital and auxiliary gauges. They remain Hermitian,
number-conserving, exact squared-operator representations. Public and hidden
instances have different physical one-particle spectra. The private selection
contains two stress cases, not a statistically representative sample.

For each case, ratio is `C / baseline_cost`. Core score is one minus the
geometric mean ratio. The family score is defined identically within each
family. There is only one family here, so worst-family score equals core score;
its threshold is not an independent robustness claim. Reference costs are
frozen measurements of the supplied champion, not global optima.

Linux x86-64, system Python, NumPy and SciPy are available. Inference uses one
fixed logical CPU, at most 2 GiB address space, and exactly `10*N` seconds of
wall and CPU budget for `N` cases. Interpreter startup and output count toward
the limit. Process/thread creation, networking and runtime compiler subprocesses
are denied. Participant and submission trees are read-only; use `TMPDIR` for
scratch. Output and logs must each be at most 8 MiB.

Example interface, with a supplied writable `OUTPUT_DIR`:

```
python3 baseline/solver.py input/examples.json "$OUTPUT_DIR/public.json"
python3 workspace/score.py input/examples.json "$OUTPUT_DIR/public.json"
```
