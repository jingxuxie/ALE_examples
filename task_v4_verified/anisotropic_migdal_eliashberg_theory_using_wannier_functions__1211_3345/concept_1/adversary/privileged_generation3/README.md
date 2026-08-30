# Private generation-three achievability portfolio

This directory is privileged authoring evidence, not a participant asset. It is
not supplied to fresh v5. No activated participant, evaluator, status, threshold,
reference, or dataset file is changed. Final task integration belongs to parent.

## Candidate and evidence

`candidate_1/solve.py` is the inference entry. It reads only runtime public input
and writes `delta,z`. `candidate_1/v4.py` preserves the earlier archived private
fresh champion byte-for-byte; it is not public baseline material. At most two
algorithms were authorized; only candidate 1 is attempted because it passes.

`summary.json` records the complete outcome, CPU accounting and exact active
generation identity. Each full-suite JSON under `reports/` has a companion
`.provenance.json` with the command, immutable evaluator codepath, all input and
reference file hashes, candidate source hashes, active 98-file prelaunch seal
SHA256, and dataset-manifest SHA256. `report_sources/` retains each exact tested
source tree. A matching policy hash alone is not used as generation identity.

Both `candidate_1_full` and `candidate_1_full_repeat` run the unchanged active
twenty-case scorer. The preliminary four-case continuum run is diagnostic only,
not an achiever claim. Resource gates remain 12 parent-measured child CPU seconds,
2048 MiB address space, one thread/process, and 1800 wall seconds per case.

## Operator change

The many-bin path builds an exact frequency-domain patch-pair symbol by summing
all input phonon bins before nonlinear iteration. It still applies every bin's
contribution; it neither compresses raw anisotropic matrices nor changes the
full-grid physics. DCT/DST parity represents the same finite Matsubara sums.

Coarse kernels are assembled using signed zeroth/first kernel prefix moments,
which exactly sum piecewise-linear interpolation over the finite grid. A weighted
SVD compresses this warm-start/preconditioning operator. Its approximation is not
used as the final residual: exact full-grid residuals drive subsequent corrected
Newton steps. Inputs with at most eight modes keep the archived v4 method, which
preserves the difficult few-mode nearcritical controls.

`operator_audit.json` contains eight independent operator checks performed in a
sandboxed non-solving test entry, including even/odd fusion versus the unfused
mode loop, prefix/modal sums versus explicit interpolation, Coulomb weights,
node reproduction and nonlinear maps. The test uses a truncation of the public
96-bin example, not hidden labels or a reference-initialized inference run.

## Reproduce privately

From the repository root, set `SIDECAR` to the canonical absolute path of this
directory, then choose a previously unused report tag:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 BLIS_NUM_THREADS=1 \
PYTHONDONTWRITEBYTECODE=1 python -B "$SIDECAR/run_suite.py" \
  --candidate candidate_1 --tag parent_confirmation
```

The wrapper checks the active generation-three seal before/after, copies candidate
source into a new private snapshot, and calls the immutable active
`evaluate.evaluate` function. That evaluator alone invokes its hardened launcher
and shared sandbox runner. No candidate module is imported in the trusted parent.
All temporary inputs/outputs are beneath this sidecar's `scratch/` directory.

The portfolio stops after one full-suite confirmation repeat; no second candidate
or further tuning is needed. Private same-budget attainability and the separate
fresh-v5 hardness outcome must not be conflated.
