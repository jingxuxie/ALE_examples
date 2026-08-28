# Long-period topological-gap optimization

Improve the supplied periodic contact geometry at the requested operating points. The starting layout and working optimizer already produce a nontrivial, manufacturable junction; the mission is to improve its robust excitation gap at the full device scale without exceeding the compute budget.

Preserve contact connectivity, fabrication constraints, and the required topological phase. Implement `solve.py` in the assigned writable attempt directory, accepting `--input REQUEST --output RESULT` and returning the contact masks as JSON. You may reuse or replace the public baseline in `workspace/baseline/`.

The authoritative physical model, operating-point semantics, interface, resources, and scoring are in `input/CONTRACT.md` and `workspace/physics.py`.
