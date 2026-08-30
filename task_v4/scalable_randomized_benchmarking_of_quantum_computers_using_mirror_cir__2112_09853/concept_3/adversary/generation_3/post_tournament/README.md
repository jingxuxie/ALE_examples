# C3 closed-attempt audit

No saved valid witness was found. Achievability remains **unknown**, not disproven.
All audit code and generated data stay in this directory. No optimization,
participant executable, or duplicate official final evaluation was run.

## Findings

- Main's official final reports: both structurally valid, ideal scores 1.0 in
  every family, core/worst score 1/3, failed quality.
- Final triple-failure counts in ladder16/grid20/bridge18 order:
  v3 = 14268/18030/32168; v4 = 1193/433/2872.
- v3 also fails single omissions in all families; v4 passes single omissions
  but fails double omissions in all families. The obstruction is faulted
  spreading, not ideal spreading or native resources.
- Screened 158 unique fresh family circuits, 172 including private/G2 sources.
  Every family candidate fails at least one quality condition; no full saved
  fresh witness or passing cross-source family portfolio exists in this inventory.
- Best ideal-feasible scratch candidates by score then failure count have
  **up-to-three** failing-scenario totals v3 = 3177/2775/3114 and
  v4 = 1206/361/2903. These improve diagnostics but still score 1/3.
- Best ideal-feasible all-source components have totals 258/282/363 and still
  fail. Private components are not fresh-agent submissions.
- Six official representative failures were independently replayed using
  scalar bit lists and explicit deletions. Opposite-direction replay recovered
  each input: twelve scalar conjugations total.
- Exact native screening agrees with all six official final-family failure
  totals, combinatorial scenario counts, and independently checked ideal scores.
- All 222 v3 and 327 v4 output files match helper deadline hashes, before and
  after the audit. Participant launch hashes and frozen evaluator hashes match.

## Evidence and reproduction

`eligibility_summary.json` contains coverage, candidate eligibility, source paths,
best candidates, and official/native parity. `candidate_inventory.json` retains
every decoded circuit, source, exact ideal metrics, and exhaustive native result.
`independent_scalar_witnesses.json` contains original positions and exact Paulis.
`fingerprints_final.json` records complete deadline/current SHA256 maps.

From the concept_3 root, reproduce this read-only-source audit with:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -B adversary/generation_3/post_tournament/audit.py
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -B adversary/generation_3/post_tournament/finalize.py
```

The first command uses the previously validated private native checker in
REPORT-only mode with three workers; 172 circuits took 24.48 seconds. It checks
every omission set of order 0 through 3, not Monte Carlo. For the threshold-three
fault requirement, forward exclusion of all weight-one/two Paulis from the same
low-weight set is equivalent to inverse exclusion by bijectivity. Ideal forward
and inverse constraints are scored separately. Full/family JSON and numeric
checkpoints are inspected as static data, never executed. Family-only and numeric
checkpoints are portfolio components, not directly valid full submissions.
