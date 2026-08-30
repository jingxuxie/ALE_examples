# Private cancellation stress study

Privileged evidence only. Never stage this directory, its seeds, its searches,
or its analysis for a fresh solver. The two-candidate-batch cap is exhausted.
No fresh agent or new solution was constructed in this study.

## Official original-E evaluations

| Batch | Overall RMSE (microhartree) | Mixed RMSE (microhartree) | True CPU (s) | Wall (s) | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| `batch_01` | 47.013603 | 108.361857 | 103.483339 | 136.605049 | valid accuracy failure |
| `batch_02` | 49.094365 | 112.358353 | 104.407168 | 159.134543 | valid accuracy failure |

Both runs use the actual unchanged `concept_1/attempts/v_1`, strict bubblewrap,
the unchanged trusted PID-1 aggregate-resource guard, one persistent controller
per complete 120-case batch, CPU120/wall180/2 GiB, query160 per system, and the
original 10/25 microhartree thresholds. Neither failure is a format, isolation,
CPU, memory, or wall failure. No relaxed-wall diagnostic replay was needed.
The later E2 reference benchmarks reuse batch 2; they are not new candidate
batches. E2 declares wall600 as its official contract before any fresh launch.

## Construction and exact identities

Each batch has 20 deliberately conditioned mixed systems (ten from each of two
private witness neighborhoods), and 100 independent ordinary public-sampler
draws, 20 per other stratum. Batch 2 retains the same ordinary controls without
outcome-based resampling. These are not IID mixed-family draws.

For a fixed three-pair occupation, shifting every original site energy by 0.9
adds the scalar 2.7 to every restricted Hamiltonian. Next change site energies by
`-d[p]` and off-diagonal density by `(d[p]+d[q])/2`. Each occupied site appears
in exactly two occupied pairs, so the density change cancels `-sum(d[p])`
identically. Taking occupied displacements `[0.15,0.07,0]` aligns the occupied
energies with E. The original virtual energies shift into `[1.25,2.1]`.

The gauge identity holds for every determinant and all 128 original CAS
restrictions. Adding a genuinely coupled eighth virtual leaves restrictions
excluding that site unchanged. Its occupied hoppings have magnitudes .04-.08,
virtual hoppings .05-.15, and independent density couplings of scale .1. This
is not a spectator: the smallest new-site singleton correlation magnitude in
batch 2 is 0.002784461 hartree, above the requested 0.0003 threshold.

The original unperturbed seven-virtual signed order>=4 tails are +63.332642 and
-150.000356 microhartree despite tiny triples. Each restricted Hamiltonian uses
the public effective three-pair model, not purported molecular Coulomb integrals.
Finite symmetric hopping/density neighborhoods are in the public mixed Gaussian
support. All virtual energies satisfy the public range and all full spectra
satisfy the strict weak-reference/gap conditions, so this is physically
admissible conditioned stress, not an IID probability claim.

## Final-batch validity and diversity

- Across all 120 systems: reference weight >=0.945798358, gap >=0.423334646;
  maximum full eigenpair residual 8.180e-16.
- Across the 20 stress systems: reference weight >=0.976988624, gap >=0.542898457.
- Independent full energy discrepancy <=5.330e-15; independent residual <=6.163e-15.
- Every excluded-new-site restriction agrees exactly in the stored arithmetic.
  Diversified-core gauge correlation discrepancies are <=1.277e-15.
- All eight virtual labels, including the new site, are independently randomly
  permuted per case. All 256 energies are covariant to <=9.993e-16 and the full
  Hamiltonians to <=1.777e-15. The new site happens to visit seven of eight
  positions; the actual position histogram is saved, not claimed balanced.
- B1 uses a 22-dimensional truncated-SVD near-null subspace with singular-value
  cutoff 2e-6. Its many saturated B bounds prevented useful naïve exact-null
  steps: all 3000 preflight proposals were rejected before a second batch was
  saved or evaluated. Small coefficient-only linear feasibility problems sample
  bounded near-null directions; they do not optimize tails or champion error.
- The author seed uses the exact seven-dimensional nullspace of the 35-by-42
  central-finite-difference triple Jacobian. Both groups receive independent
  coefficient jitter of sigma 1e-7 and independent active-new-site couplings.
  Accepted maximum-coordinate changes are .01182-.02750 hartree. All original
  B control bounds hold with minimum margin 7.974e-6; all old triples remain
  below .370954 microhartree, checked from actual CAS energies rather than only
  a linear approximation. Strict physical and parent margins establish local
  neighborhoods; perfect zero increments are neither required nor claimed.

Canonical comparisons remove permutation-only diversity. In the B1 group,
pairwise maximum CAS2 differences have median 61.0714 microhartree (range
.6741-133.0895), and fourth-increment differences median 2.1337 (range
.0418-4.3755). Its signed old tail spans +56.3938 to +63.1066 microhartree.

The author group remains tightly clustered in observables despite distinct
coefficients: pairwise maximum CAS2 differences have median .3837 microhartree
(range .0474-.9207), and fourth-increment differences median .02370 (range
.00295-.06684). Its old tail spans -150.0654 to -149.9614 microhartree. Each
group has ten distinct CAS2 vectors at 12-decimal rounding. This is explicitly
two seed-derived neighborhoods, not twenty independent witness seeds, and
does not establish resistance to cross-case caching or broad population
hardness. Full pairwise coefficient/CAS2/fourth-order statistics are in
`batch_02/diversity.json`.

## Signed failure mechanism

Deterministic replay of the unchanged acquisition functions selects 26
quadruples containing the new site and zero old-only quadruples in all 20
stress cases, even after random relabeling. All 56 triples are measured. Tiny
old triples suppress the old-region covariance while the active new site
supplies stronger triples. The surviving old signed higher-order tails are
therefore not directly measured. Complete signed/absolute order sums and the
queried/unqueried decomposition are saved per case.

The diagnosis does not assume that all physical fitting is skipped. The
global uncertainty gate is above its skip threshold in all 20 cases. On the
final batch, seven cases receive a net correction relative to the exact neural
plus acquisition fallback; thirteen do not, including all ten author cases.
The evaluator does not expose whether a no-correction fit was rejected or
timer-skipped, so that distinction is not asserted. The author group's mean
old-region fallback error is +149.9333 microhartree; the new-region error adds
+4.2229, yielding mean actual +154.1562. Early author failures also occur before
late-run CPU gating can explain them. B1 fitting partially repairs the old tail
but its group RMSE remains 38.4211 microhartree. The 100 ordinary controls have
RMSE 19.1684 within this persistent run; their treatment can depend on previous
fit-time consumption. No independent per-case controller reset is used.

`batch_02/failure_analysis.json` records the deterministic acquisition masks,
their derivation (official logs contain counts, not masks), signed order sums,
old/new error attribution, and measured correction. The contribution identity
closes against each actual official error to 1e-11 hartree.

## Files and audit

`build_batch.py`, `build_diversified_batch.py`, and `analyze_batch.py` create the
private models, all-subset tables, provenance, Jacobians, covariance checks,
canonical core diversity, and signed error analysis. `replay_wall_diagnostic.py`
is unused; it only permits an explicitly labeled diagnostic replay after an
official wall failure, changing only outer/guard wall to 600, not CPU/query/RSS.
`packet_metadata.py` audits and freezes the separately authorized E2 packet.

Both batches contain `cases.npz`, `models.json`, `diagnostics.json`,
`validation_summary.json`, `provenance.json`, `score.json`, `summary.json`,
`failure_analysis.json`, and private SHA256 manifests. Original source models,
witnesses, evaluator code, and champion files are hash-checked unchanged.
Only this directory and the subsequently authorized `../ratchet_1/` are written.
