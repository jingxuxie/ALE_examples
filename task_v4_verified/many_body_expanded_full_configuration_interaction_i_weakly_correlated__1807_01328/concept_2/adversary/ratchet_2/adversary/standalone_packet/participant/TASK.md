# Persistent premature screening in a weakly correlated paired model

Find a static electronic-Hamiltonian witness whose third-order many-body
expansion appears converged under the supplied parent-increment gate while
missing a material correlation-energy tail. The witness must also persist under
two specified finite perturbation assays.

This is a three-pair, ten-spatial-orbital, seniority-zero effective model, not a
literal ab initio molecule or a universal claim about a published method.

## Assets and interface

Construction time: one hour.

`input/target.json` fixes the model and nominal constraints.
`input/assay_spec.json` specifies the assays and evaluator limits.
`input/FORMAT.md` gives the complete mathematics, JSON schema, distribution,
public API, and scoring. `workspace/` contains the model, a diagnostic checker,
and an admissible zero-control baseline; `input/training_uniforms.json` supplies
independent public training directions.

Treat `participant/` as read-only. Write **`witness.json` at the writable work
root**, containing only the two symmetric 7-by-7 VV control matrices and schema
version. Evaluation reads that static file; it does not execute submitted code.

## Target

Nominally, every triple increment must be at most **1 microEh**, the missing tail
at least **50 microEh**, and their specified ratio at least **100**. Reference
weight must be at least **0.95**, the paired-sector gap at least **0.4 Eh**, and
the diagonal reference margin at least **0.6 Eh**.

The same conditions must hold in **at least 122 of 128 cases in each family**:
VV-only uncertainty and uncertainty in all 100 effective-model coefficients.
Both use the same **0.001 Eh** radius and independent frozen draw pools. Nominal
success and success in both families are required.

The artifact limit is **32 KiB**. Official validation uses at most **90 seconds
wall time, 60 seconds CPU, and 512 MiB address space**, with closed stdin and one
BLAS thread. NumPy and SciPy are available. Public diagnostics are not the hidden
assay and do not guarantee an official pass.
