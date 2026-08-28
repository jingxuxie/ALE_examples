# Gate-set calibration solver

Run `python solver.py INPUT.npz OUTPUT.npz`. The implementation is self-contained
and uses only NumPy, SciPy, and the Python standard library. Set
`SOLVER_VERBOSE=1` to print timing and optimization diagnostics to stderr.

## Model

Each experiment is represented by its exact Clifford sign and a sparse row of
nonnegative coefficients. Its signed mean is the sign times
`exp(-design_row @ parameters)`. Gate coefficients are twice the number of
anticommutations with each declared Pauli error; SPAM coefficients indicate
intersection with each declared factor. Backward propagation applies the
inverse ideal gate before recording that gate's noise contribution.

## Identification

Preparation and measurement can exchange a support-dependent potential only
on factors declared in both channels. For a factor `F`, its support function
has the Pauli-character expansion

`1{F intersects support(P)} = 4**(-|F|) * sum_{E supported within F} (1-chi_E(P))`.

A structural gauge changes a gate's attenuation by the difference of this
potential at the output and input supports. In the Pauli-character basis,
this is computed by conjugating at most 15 errors per SPAM factor. Any
resulting coefficient on an undeclared gate error must vanish. This gives
the complete structural gauge space without enumerating all global Paulis.

Calibration identification separately tests membership in the row space of
the supplied training design. Zero and proportional columns are handled
explicitly. Remaining null directions are probed using regularized sparse or
dense factorization with inverse iteration, or high-accuracy sparse least
squares. The solver chooses between primal and dual Gram matrices to reduce
the factorization size.
No fitted boundary or prior is used to decide identifiability.

## Estimation

Records with identical unsigned attenuation designs are pooled after their
counts are corrected for the ideal sign. Proportional parameter columns are
combined in a way that preserves the positive-rate feasible set. A weighted
log-contrast initialization is refined with the exact binomial likelihood
and nonnegative rates. Held-out predictions retain their ideal signs.

## Development checks

`python test_solver.py` checks Clifford phases against dense primitive
unitaries, large Clifford lookup tables against direct propagation, and
structural/calibration labels against explicit small-system null spaces.

Additional checks cover query rescaling, empty calibrations, computational
sectors, and a weak 24-qubit design compared with a dense null-space result.
A 24-qubit, 24-channel benchmark with 6,976 parameters and 15,000 training
records runs in approximately 18 seconds and uses about 247 MiB RSS under a
3 GiB address-space limit on the supplied environment. A coupled mixed-gate
benchmark of the same parameter size runs in approximately 27 seconds and
uses about 730 MiB. A 9,568-parameter case with structural and additional
calibration null directions runs in approximately 25 seconds. These are synthetic
development checks, not scores or labels for the unlabeled public example.
