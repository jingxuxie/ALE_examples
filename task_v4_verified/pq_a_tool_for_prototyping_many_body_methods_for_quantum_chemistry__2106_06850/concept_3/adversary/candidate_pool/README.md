# Optional private ratchet pool — not an active task

Everything in this directory is organizer-only, including seeds, certificates,
prefix diagnostics, and generation source. Do not expose this directory or its
logs to participants. No active task files, thresholds, or attempts are changed
or read by this sidecar. It runs no contestant code and spawns no agents.

`index.json` indexes individually selectable candidates. Each candidate has a
full fixed-N target vector, planted certificate, and per-prefix metadata under
`cases/<id>/`. `targets.json` and `certificates.json` aggregate the same cases.
Depths are 24/28/32 for 10 orbitals with 4 or 6 electrons; optional 12-orbital,
6-electron cases use depths 28/32. These are possible future task instances,
not extra cases silently added to the running task.

The engine snapshot preserves the active gate algebra, canonical orientation,
spin conservation, angle range, norm tolerance, squared-overlap threshold
`0.999999999`, 128-KiB submission cap, and strict JSON validation. `pool_api.py`
changes only target loading to accept 1–32 candidates and the explicitly listed
larger sectors/depths. The active loader deliberately cannot load this pool.

## Physical-complexity criteria

Every prefix from depth 16 (10 orbitals) or 20 (12 orbitals) onward has complete
support in its fixed-spin sector and full alpha/beta Schmidt rank. Throughout
that suffix, every physical coefficient has magnitude at least `1e-6`, every
Schmidt value is at least `1e-4`, and the effective Schmidt rank `exp(entropy)`
is at least 55% of its maximum. Forced zeros outside the fixed-spin sector are
not counted as sparsity. The late suffix consists entirely of opposite-spin
double excitors, with noncommuting neighbors and at least `0.006` change in the
Schmidt spectrum per gate. Every angle has magnitude in `[0.42, 1.20]`, every
gate changes the state by at least `0.10` in L2 norm, and gate labels are unique.
These are authoring criteria, **not additional acceptance constraints** on a
future contestant circuit. Any legal within-cap circuit matching a target passes.

Alpha/beta Schmidt diagnostics use the tensor basis with all alpha creation
operators preceding all beta creation operators. The coefficient matrix applies
the fermionic sign `(-1)^(number of occupied beta-before-alpha inversions)` to
the interleaved-orbital determinant amplitudes before SVD. Rows and columns
enumerate increasing fixed-occupation alpha/beta masks. Maximum ranks are 10
for the 10-orbital sectors and 20 for the 12-orbital sector. `verify_pool.py`
checks this convention using product states and spin-local gates as well as
independent Jordan-Wigner exponentials.

These criteria remove immediate zero-support peeling along the planted suffix;
they do not prove search hardness or minimality, and do not rule out a different
shorter circuit or a successful reverse search. Main should test only a
**completed** champion on this private pool and select a genuine failure before
deciding whether to create and reseal a new participant task.

## Commands

From this directory, using Python 3.10+, NumPy and SciPy:

```bash
OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python generate_pool.py
OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python verify_pool.py
OPENBLAS_NUM_THREADS=1 python pool_api.py --submission certificates.json
OPENBLAS_NUM_THREADS=1 python pool_api.py --targets cases/pool_001/targets.json --submission cases/pool_001/certificate.json
```

Generation is bounded and refuses to overwrite an existing pool. Optional
12-orbital generation failures are recorded without relaxing physical criteria.
The verification report and manifest are private. The pool checker reads JSON
as data and returns `core`, `worst_fidelity`, `pass`, `reason`, and runtime;
it does not execute submission programs.
