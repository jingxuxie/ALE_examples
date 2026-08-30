# Size-parameterized bounded baseline

Run the commands in TASK.md. `--target`, `--seed`, `--restarts`, and `--steps`
make the local search reusable without private information. Counts and cyclic
spacing are invariant under accepted swaps. Integer autocorrelation increments
are recomputed independently at every restart and before output.

The reference run uses seed 1701 and the same four 60,000-proposal restarts as
the smaller instance. Its temperature scale grows linearly with pair count.
This matches proposal count, not proposals per slot or wall time. The search
uses linear working storage rather than quadratic index tables. Only NumPy
and the standard library are required. The bundled artifact is a bounded
baseline, not evidence of optimality or a guaranteed exact solution.
