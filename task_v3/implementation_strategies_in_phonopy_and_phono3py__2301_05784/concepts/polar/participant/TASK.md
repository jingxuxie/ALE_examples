# Polar lattice derivatives and degenerate-mode response

Deliver **`solve.py` in the writable attempt/output directory designated by the
runner**. The participant tree is read-only; `workspace/solve.py` is a starter,
not the delivery location.

Your solver must accept exactly two positional paths:

```
python solve.py INPUT.npz OUTPUT.npz
```

Compute two independently scored outcomes from real polar-crystal data:

- The full Cartesian derivative of a supplied short-range Fourier model plus
  its reciprocal dipole contribution.
- Degenerate-subspace response, directional velocity spectra, and Cartesian
  branch velocities selected by perturbation directions.

`workspace/CONTRACT.md` specifies all arrays, mathematical conventions, branch
ordering, and unresolved-degeneracy handling. The second outcome supplies its
own matrix derivatives and does not depend on the first.

`input/smoke.npz` is an unlabeled interface example. The starter uses incomplete
fixed-step and diagonal-only approximations. Cases include oblique frames,
near-zone-center queries, complex subspace bases, and larger batches.

Use available numerical Python libraries without network or private-data access.
Continuous scores normalize measured baseline quality to 0.5; references approach
1. Runtime and memory are reported, with default limits of 180 seconds and
8192 MiB per case. Any conforming numerical method is permitted.
