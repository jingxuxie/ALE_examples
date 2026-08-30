# Private, general solver portfolio

Generation-time achievability experiment only; no participant attempts or future
attempt contents are accessed. This directory is not part of participant assets.

`v1/solve.py --request REQUEST --output STATE` is self-contained with its engine
and public-contractor snapshot. It uses only request coefficients and budgets,
not case identifiers, hidden energies, calibration tensors, or lookup tables.
The solver uses charge-preserving full-bond optimization, small mean-field
initialization portfolios, explicit tensor contractions, and inner CPU deadlines.

Only public examples and small independent correctness checks may run before
main authorizes evaluation. Do not call the frozen hidden evaluator until all
eight calibrations and main validation are complete and main explicitly signals.

At most three variants will be tried. Preserve source hashes, commands, measured
outputs, and near misses. A full passing algorithm is known only after this same
self-contained submission passes the frozen bwrap evaluator, including every
resource and validity gate. Public-example success is not such certification.

`v1` has two preserved actual-evaluator near misses. Every completed output had
quality one, but short-stage wall timeouts and one 6.012-second CPU overrun failed
the validity gate. Unaccounted CPU observations are explicitly marked unknown.

`v2` preserves the numerical optimizer and adds CPU cleanup headroom, atomic best
MPS checkpoints, and an import-free valid Fock-product fallback. A recent request
file's modification time is used only as a conservative wall-budget-origin hint;
stale files do not shorten the declared budget. This uses no case identity,
target energy, or state lookup. The alarm applies only to the solver's own process.
