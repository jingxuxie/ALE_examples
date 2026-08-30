# Private builder algorithm, not a solution lookup

`in_budget/solve.py` with its adjacent `portfolio.py` is an ordinary standalone
submission artifact. It reads only the current case and public model API. It
derives flux and hole geometry from those inputs, uses vortex-seeded local
minimizations and vortex/sector edits, and returns the best converged field. It
contains no hidden seeds for case generation, case-ID branches, energy tables,
or stored fields. Its optimizer RNG seed is algorithmic, not a hidden-case seed.

The default internal search deadline is 54 seconds, leaving startup/I/O margin
inside the evaluator's 60-second limit. `evaluator/hidden/qualify.py` runs this
artifact through the actual supplied sandbox and captures outputs outside its
mounts for later independent scoring. It uses a provisional denominator until
private references freeze; only the final rescored report establishes achievement.

`portfolio.py` one directory higher is the builder source, also used for longer
offline witness searches. Longer-run fields prove attained energies only.
`attempts/witness_feasibility.json` must not be presented as a passing solver run.
If no general executable passes the exact frozen target within the same resource
contract, status remains `hard_open_candidate` despite stored witness fields.
