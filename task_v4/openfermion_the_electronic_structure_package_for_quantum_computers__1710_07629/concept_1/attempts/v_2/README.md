# Fermionic normalization solver

Run from any working directory:

```
python3 path/to/solver.py REQUEST.json RESPONSE.json
```

The submission contains all its own algorithm and native-library files. Its only
runtime dependencies are the supplied Python, NumPy, SciPy, and standard system
libraries. It does not compile code, launch processes or threads, access the
network, or read example solutions at inference time. All asset paths are
resolved relative to the Python files.

## Method

- Start from several gauge-independent spectral orbital and auxiliary bases.
- Refine simultaneous orthogonal transformations using Cayley coordinates and
  decreasing smooth approximations to the exact normalization objective.
- Explore competing local frames with charge-vector alignments, randomized
  charge-vector QR bases, and secondary minima of orbital-pair rotations.
- Detect repeated smooth basins to spend the search budget on distinct starts.
- Finish with low-smoothing refinement and exact nonsmooth Givens polishing.
- Reorthogonalize the returned matrices and retain the best exact original cost.

The native objective and optimization loop use one thread. Search deadlines
reserve 10% of the batch limit for startup and scheduling, and cases receive time in
proportion to their dimensions. The Hamiltonian is never truncated or changed;
only the requested orbital and auxiliary transformations are returned.

## Validation

The public example improves by approximately **1.415%** over the frozen champion
cost (576.4318565 to approximately 568.27). Independent development variants
and all dimensions from 14 through 16 were also used for numerical checks.
A two-case 14/16-mode test runs below 20 seconds on one CPU with a 2 GiB address
space limit and process/thread creation disabled. Hidden cases were not accessed.

Measured numerical and resource checks are recorded in `validation.json`.
The required initial isolation report is in `isolation_audit.json`.

## Optional native rebuild

No compilation is necessary to run the submission. To rebuild with the system
C++ compiler during development:

```
g++ -std=c++17 -O3 -fPIC -shared -o core.so core.cpp
g++ -std=c++17 -O3 -fPIC -shared -o champion/polish.so champion/polish.cpp
```

`champion/optimize.py` and the Givens polisher are supplied champion utilities;
the remaining optimizer, search, and executable implementation are local to
this submission.
