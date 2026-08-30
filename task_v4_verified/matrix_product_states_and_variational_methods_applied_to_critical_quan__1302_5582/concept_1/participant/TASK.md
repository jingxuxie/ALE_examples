# Robust variational field states in fixed parity sectors

## Mission
Improve the supplied current-champion optimizer for finite, nonuniform phi4
chains. Return low-energy matrix product states within the requested bond cap
and global parity sector. The hidden suite varies mass and quartic profiles,
weak links, and alternating couplings. This is a finite-Hamiltonian optimizer
task, not a continuum extrapolation or gap-prediction task.

## Assets and interface
`workspace/` contains a starting solver and public energy contractor;
`baseline/` is the frozen champion production code. `input/` contains examples,
the exact Hamiltonian and array contract, and the scoring specification.
Submit a self-contained directory with `solve.py`, implementing
`python solve.py --request REQUEST.json --output STATE.npz`.
Return MPS tensors, not energy claims. Copy read-only starter files into the
writable submission directory before making changes.

## Objective
The checker recomputes energies and rewards logarithmic improvement over a
frozen baseline at two compute budgets, worst-family quality, and runtime.
Pass with score >= 80, core >= 0.80, worst-family >= 0.70, each long-budget
quality >= 0.55, and all outputs valid. Reference energies come from attainable
same-cap states; they are not asserted exact ground energies.
See `input/CONTRACT.md` and `input/scoring.json`.

## Resources
Eight hidden chains, each run independently at 6 and 40 CPU seconds, with
30/120-second solver wall guards. Interpreter startup and imports count;
trusted launcher setup does not. One execution thread, 2 GiB address space,
no GPU, network, subprocesses, or cross-request state. Python, NumPy, and SciPy
are available. The participant tree is read-only; only the submission/output
directory is writable during the fresh attempt.
