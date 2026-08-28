# Private narrowed-high-field reference calibration

This measures fixed source and original-zigzag designs on the newly supplied
request, not the submitted solver. A broad-region output's high-field tradeoff
alone is not evidence of a capability gap. Main owns the same-executable
adaptation run, submission measurements, and any subsequent interpretation.
No initial score, public contract, objective, source mask, or physical constraint
is changed by this calibration.

Run once from this directory:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python -B calibrate.py --wall-seconds 600
```

All writes stay inside `highfield_research/reference/`. The unchanged helper is
`../../reference/physics.py`. Six one-thread workers use CPUs 40, 42, 44, 46,
48, 50; the controller uses 51. The shared numeric wall budget is 600 seconds;
each worker has a 3 GiB address-space cap. No first-eight or last-twelve CPU
is used. The request is 61×65 sites / 15,860 DOF at a 20 nm lattice spacing.

The strong geometry must equal the archived `homogeneous_filtered.p` epoch 800
mask exactly; its source-member SHA256 is checked against the prior verified
source inventory. The weak geometry must equal both the request baseline and
the unchanged helper's original zigzag. Supplied provenance does not include
dimension or hashes: these are independently derived, verified, and recorded
in `fingerprint.json`, without editing the supplied files.

Each of the two designs is evaluated on all three supplied scenarios with
51 momenta in [0, pi] and an independent Pfaffian Q at 0 and pi. Checkpointed
measurement JSON includes all eight energies per momentum, gap curves, timings,
manufacturing, Q, affinity and resource metadata. Wavefunctions are not saved.
Timings cover the full unchanged low-energy API, not an isolated kernel.

`calibration.json` has `weak` and `strong` records, each containing
`robust_gap_mev`, `physical_feasibility`, and full measurements.
R = 0.5 mean(scenario gaps) + 0.5 min(scenario gaps). Feasibility requires
unchanged manufacturing, all three Q=-1, and each gap above 1e-5 meV.
Incomplete aggregates stay null and are not failures. Completed invalid or
losing source results are retained honestly. Unbounded weak=0/strong=1 anchors
are ready only if both designs are feasible and strong-minus-weak exceeds the
existing 1e-4 meV calibration threshold. No pointwise-max synthetic design is used.
