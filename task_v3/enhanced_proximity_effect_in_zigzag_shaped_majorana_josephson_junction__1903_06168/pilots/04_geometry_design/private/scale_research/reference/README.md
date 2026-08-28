# Private published-scale reference calibration

This is an out-of-initial-contract scale audit, not an initial participant failure,
score, acceptance gate, or ratchet. No optimizer or submitted geometry is run here.
All writes stay in this directory; the supplied request, scenarios, strong mask,
provenance, and `../../reference/physics.py` are read without modification.

From this directory, run once:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python -B calibrate.py --wall-seconds 900
```

The controller runs on CPU 27. Six one-thread workers run on CPUs
16, 18, 20, 22, 24, and 26, with a shared 900-second numerical wall deadline and
a 3 GiB address-space cap per worker. Each measures one design/scenario pair.
The weak mask is exactly `../request.json`'s `baseline_geometry`; the strong mask
is exactly `../strong.json`. Its epoch, array equality, and source-member digest
are independently checked against the existing private author archive.

Every completed measurement saves all 51 momenta in [0, pi], the eight low-energy
eigenvalues and gap at each momentum, per-call timings, an independent Pfaffian
Q at 0 and pi, manufacturing checks, affinity, and resource usage. The unchanged
helper checks eigenpair residuals internally. Call timings include Hamiltonian
assembly, factorization, eigensolution, and residual checks; they are not isolated
kernel timings. Wavefunctions are transient, not saved.

`calibration.json` contains `weak` and `strong`, each with `robust_gap_mev`,
`physical_feasibility`, and full measurements. R = 0.5 mean(gaps) + 0.5 min(gaps).
Physical feasibility requires unchanged manufacturing, all three Q=-1, and each
full-grid gap above 1e-5 meV. Incomplete results have null aggregate values and
are not failures. Completed invalid designs keep their measured R but cannot
define usable anchors. Normalization is unbounded weak=0/strong=1 only when both
designs are feasible and the strong-minus-weak separation exceeds the existing
1e-4 meV calibration threshold. Losing, invalid, or incomplete source references
are reported without changing masks, constraints, or the initial evaluator.

`fingerprint.json` records exact input, source-member, archive, geometry, helper,
and runner hashes. `runtime.json` records the numerical deadline and resource
assignment. The per-scenario JSON files are incrementally checkpointed in
`measurements/`; a deadline may leave partial traces, never scored as full gaps.
