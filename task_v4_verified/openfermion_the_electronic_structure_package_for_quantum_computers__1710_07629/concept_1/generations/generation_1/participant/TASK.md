# Further compression of fermionic representations

Reduce the coefficient-normalization cost of exact fermionic Hamiltonian
representations beyond the supplied champion, using orbital and auxiliary
orthogonal basis changes without altering the Hamiltonian.

Assets: a runnable champion with source and native library, one public example,
the exact objective and public scorer, and the contract in `input/FORMAT.md`.
All assets, including `workspace/`, are read-only.

Place a self-contained `solver.py` and supporting files in the supplied output
directory. Implement `python3 solver.py REQUEST.json RESPONSE.json`.

The fixed target is **1.0% additional aggregate reduction** over the supplied
champion reference costs, with **0.5% minimum family reduction**. All returned
transformations must be valid. The two hidden cases belong to one disclosed
competing-locality family; this is a narrow stress task, not a broad
generalization benchmark. Neither hidden Hamiltonian is a regauging of the
public example.

Development time is one hour. Hidden inference gets **20 seconds total** for
two cases, one CPU, and 2 GiB. More generally, the batch limit is `10*N` seconds
for `N` cases, including startup. Scoring reports aggregate reduction,
worst-family reduction, validity, and runtime. Internet and runtime process or
thread creation are unavailable; precompiled native code is allowed.
