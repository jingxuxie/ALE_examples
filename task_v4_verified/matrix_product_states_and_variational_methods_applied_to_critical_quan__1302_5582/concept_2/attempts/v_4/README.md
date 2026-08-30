# Critical Ising uniform MPS

`state.npz` is the submission. It contains only the real array `A` with shape
`(2, 24, 24)` in the required physical and virtual parity bases.

The construction starts from the provided bond-24 baseline and optimizes all
specified distances directly. Each virtual-parity row block is represented by
a QR-orthonormalized matrix, enforcing right-canonical form and exact parity
throughout optimization. The stationary density is obtained by solving the
fixed-point equation in the real symmetric even-parity sector. Symmetric and
antisymmetric transfer sectors provide the order, connected-density, and
y-spin correlations. Binary matrix powers evaluate every required separation.
The loss combines the normalized energy excess and relative correlation errors.

`optimize.py` implements the differentiable construction using CPU PyTorch and
SciPy L-BFGS. A finite-difference directional check verified its gradient.
Independent comparisons against the supplied checker verified the correlation
calculations to approximately 1e-14 absolute precision.

`validate.py` invokes the supplied public checker on the final artifact and
writes its complete output to `validation.json`. Run it from this directory:

```sh
python validate.py
```

Optimization traces and intermediate tensors are retained for reproducibility;
only `state.npz` is the submission.
