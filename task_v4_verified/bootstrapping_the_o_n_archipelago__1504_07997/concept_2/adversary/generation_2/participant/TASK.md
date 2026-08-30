# Sparse mixed-OPE completion — generation 2

Construct admissible sparse spectral certificates for eight reduced mixed-OPE
instances. Recover shared, rank-one positive matrix contributions reproducing
the observations within the stated tolerances. This finite leading-radial model
is not a full conformal-block or crossing-symmetry calculation.

## Deliverable
Write `output/answer.json` containing one certificate per instance. Any admissible
completion earns credit; no particular support or hidden answer is required.
Data and the exact contract are in `input/instances.json` and `input/FORMAT.md`.
Work in a writable output directory; participant assets may be read-only.

`baseline/solve.py` is a generalized previous-generation champion. Run:
`python baseline/solve.py input/instances.json output/answer.json`.
Check with `python workspace/check.py input/instances.json output/answer.json`.

## Objective and resources
Produce valid certificates for **all eight instances**: core score **1.0** and
worst-family score **1.0**. The numerical contract and public checker are unchanged.
You have one hour, up to four CPU threads and 4 GiB RAM. Installed Python, NumPy,
SciPy and mpmath are available; no network or privileged files. Only the final
certificate data is graded, not submission code.
