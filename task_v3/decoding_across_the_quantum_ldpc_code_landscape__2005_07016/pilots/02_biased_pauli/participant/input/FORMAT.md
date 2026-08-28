# Mathematical and executable contract

## Model

All binary algebra is over GF(2); Pauli phases are irrelevant. A Pauli is
`(x,z)`, with `I=(0,0), X=(1,0), Y=(1,1), Z=(0,1)`. Its symplectic pairing
with `(u,v)` is `x v^T + z u^T (mod 2)`.

A case provides canonical CSS check matrices `base_hx` (rX,n), `base_hz`
(rZ,n), with `base_hx @ base_hz.T = 0`. Canonical generators in measurement
order are `(base_hx,0)` followed by `(0,base_hz)`; rows can be dependent.
The real codes have `(n,k)=(416,18)` or `(882,24)`. The `input/codes/`
archives contain only `base_hx`, `base_hz`, and scalar `n`, `k` metadata.
All scored problems have n >= 416. There is no circuit or readout noise.

`permutation[j]` is the physical position of canonical qubit j.
`frame[j]` is an invertible binary 2-by-2 matrix F_j with determinant one.
For errors, corrections, and generator rows alike:

```
[x_physical[permutation[j]]]           [x_canonical[j]]
[z_physical[permutation[j]]]  = F_j @  [z_canonical[j]]  (mod 2).
```

F_j need not be its own inverse. Cases include sector-wise Hadamards and
all six such single-qubit matrices. `gx`, `gz` (rX+rZ,n) are the resulting
physical stabilizer generators, in the measurement order just specified.
They satisfy `gx @ gz.T + gz @ gx.T = 0`. The physical correction must
satisfy `correction_x @ gz.T + correction_z @ gx.T = syndrome`.
The canonical and physical descriptions are redundant and agree exactly;
neither a frame nor a qubit permutation changes the generator row order.

`pauli_probs[j,:]` lists physical-qubit probabilities `[pI,pX,pY,pZ]`.
Each row is positive and sums to one. Qubits and shots are independent, but
the X and Z components on a single qubit generally are not:
`P(x=1)=pX+pY`, `P(z=1)=pZ+pY`, `P(x=1,z=1)=pY`.
Transform the four outcomes, not just their component marginals, when
changing coordinates. Total nonidentity rates are between 0.01 and 0.16;
nonidentity probability ratios can reach 100 and may vary by qubit. Neither
the dominant axis nor the bias strength is fixed across cases. The same
joint channel applies to every shot of a given case.

An input syndrome is generated from a hidden error `(error_x,error_z)`:
`syndrome = error_x @ gz.T + error_z @ gx.T (mod 2)`.
Success requires the residual error plus correction to lie in the row span
of `[gx | gz]`. Equivalently, the correction must reproduce the syndrome
and all 2k independent logical commutation signatures of the hidden error.
An arbitrary zero-syndrome residual can still be a logical failure. All
stabilizer-equivalent corrections count equally; matching a specific error
or reference bit string is not required. Logical labels are never inputs.

## NPZ input

Load using `numpy.load(path, allow_pickle=False)`. Exactly these fields are
provided; no seeds, family names, hidden errors, or logical data appear:

| Key | Type and shape | Meaning |
| --- | --- | --- |
| `schema_version` | integer scalar, 1 | Version |
| `base_hx`, `base_hz` | uint8, (rX,n), (rZ,n) | Binary CSS checks |
| `gx`, `gz` | uint8, (rX+rZ,n) | Binary physical generators |
| `frame` | uint8, (n,2,2) | Canonical-to-physical symplectic maps |
| `permutation` | int64, (n,) | Bijection as defined above |
| `pauli_probs` | float64, (n,4) | Physical joint channel |
| `syndrome` | uint8, (shots,rX+rZ) | Binary observations |

Do not assume an example's shot count. Scored batches have 64 to 256 shots;
the public examples have only three unlabelled shots on the real matrices.
The examples provide neither a quality estimate nor a training set.

## Output and execution

```
python solve.py --input /absolute/path/case.npz --output /absolute/path/answer.npz
```

Write an NPZ with exactly `correction_x` and `correction_z`, each an integer
or boolean array of shape (shots,n), with entries exactly zero or one.
Output uses physical coordinates. No pickles, NaNs, floats, transposed
arrays, implicit reshaping, or additional output fields are accepted.
The evaluator may choose arbitrary file names and launches a fresh process
per case, with the submission as its working directory. Do not rely on
cross-case state, paths outside the submission, or internet access.

The budget is 60 seconds of process CPU time per case on one CPU thread and
4 GiB address space. Wall timeout is 180 seconds; infrastructure startup is
not charged as CPU. Compilation is charged if done inside a case. The sandbox
provides NumPy 1.21, SciPy 1.8, g++, and the Python standard library, plus the
released original native BP+OSD source under `workspace/legacy_2020/`.
There is no working public Numba or specialized Python decoding package.
The private reference uses separate dependencies unavailable to participants.
No external solver retrieval is allowed. A timeout, CPU-budget violation,
malformed output, or process failure counts as zero success and zero
consistency for that entire case. CPU and wall times are reported separately.

Hidden quality is full-block logical success, averaged within equal-weight
code/noise families. Per-family quality is affine-normalized against frozen
weak and strong anchors: `(success-weak)/(strong-weak)`, without clipping.
The aggregate `mean_core` is the mean normalized family quality;
`worst_family` is its minimum. Values can be negative or greater than one.
Raw logical success, syndrome consistency, and runtime are reported too.
Runtime is a feasibility limit, not a hidden quality bonus. Passing the
structural smoke test does not demonstrate decoding quality.
