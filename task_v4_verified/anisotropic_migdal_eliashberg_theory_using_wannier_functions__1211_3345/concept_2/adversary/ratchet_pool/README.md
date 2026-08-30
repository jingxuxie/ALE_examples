# Private ratchet preparation

This directory is a sidecar only. It does not change the active participant, evaluator, target, status, attempts, or champions and does not launch models. All generated files stay under this directory. A retained instance is not a demonstrated model failure: the parent must later run the actual successful search against it before selecting any ratchet.

The pool keeps eight patches, three modes, the original NPZ interface, the original entry bounds and invariant tolerances, zero Coulomb repulsion, and target **1.12**. Every alternative preserves its own full static aggregate, labeled per-mode rows, and mode diagonals between endpoints. Only nonuniform row profiles, static graph structure, spectral allocation, and phonon energies vary. The generator has eight deterministic specifications; it never creates an open-ended family of new tasks.

`generate_pool.py` performs bounded privileged multistart search. It records high- and low-endpoint outcomes separately so incomplete minimization is not mistaken for competing local maxima. Distinct high-temperature stationary clusters are empirical evidence, not a proof of basin structure or global optimality. The search-gap table includes gaps to the best observed outcome and target hit rates. Numerical equality of static eigenscores is checked for every retained witness.

Only passing, independently audited witnesses are retained with input arrays. Rejected specifications retain parameters and scalar search logs, but no witness artifact. Passing means exact-tolerance feasibility, the 1.12 worst-family/refinement ratio, converged 96/192 grids and nominal 384, independently assembled signed-frequency comparisons, and the regular-row no-go control. `trusted/` is a byte-for-byte snapshot of the existing trusted physics/audit implementation, not a new solver. File hashes are recorded in `snapshot_manifest.json`.

Run from this directory:

    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B generate_pool.py --cpu-seconds 900

The script refuses a budget above 900 CPU seconds and an already-used output location. Use `--output-subdir reproduction_01` for a separate deterministic reproduction inside this sidecar. It may stop early when the configured multistarts have saturated. Search timing and NPZ timestamps are not byte-reproducible; compare arrays and logical instance hashes.

Later, without running any candidate code, audit a candidate artifact against a retained instance:

    python -B audit_artifact.py --instance instances/INSTANCE_ID --artifact /absolute/path/witness.npz --output candidate_checks/check.json

The output path must remain under this sidecar. Artifact link, archive-size, NPY-header, shape, finite-value, and invariant checks are inherited from the trusted checker. This command audits an artifact only; the parent separately controls isolation and actual search execution.
