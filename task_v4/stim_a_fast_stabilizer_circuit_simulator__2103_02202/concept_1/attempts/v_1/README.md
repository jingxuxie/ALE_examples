# Robust detector-readout compression

Run `python3 solve.py --input INSTANCE.json --output ANSWER.json`.

The submission consists of `solve.py`, `engine.cpp`, and the compiled `engine`.
It uses only Python's standard library, NumPy, SciPy, and C++17. If the binary
is absent, the wrapper compiles the supplied source into temporary scratch space.

The solver compresses the observable fault-signature space exactly, evaluates
syndrome distributions with cached Walsh transforms, and combines beam search,
algebraic sparse-parity seeds, and multi-start one- and two-tap exchanges.
Both directly fitted risk and regime-wise lower bounds guide the search.
Final fixed correction tables use linear-programming dual certificates and a
bounded deterministic branch-and-bound search. No regime is inferred at runtime.

The default internal wall-clock budget is 40.5 seconds, including compilation
when needed. All output indices use the original input tap ordering.
The other Python programs and JSON files are local validation/scratch artifacts;
they are not dependencies of the submission.
