# Source-gap ledger

Audit date: 2026-08-27 America/Los_Angeles. This is an author-only document.

## Verified artifact boundaries

The official repository has 30 commits. The checked-out head is `5dbac32` (tag
0.3, October 20, 2024); tag 0.1 is `54e6886` and tag 0.2 is `54811e2`.
Release assets provide the same 213,294,213-byte, 100,000-jet CMS text sample.
The GitHub issues and pull-request API responses are both empty, not evidence
of an unreported numerical fix. In particular, `4263639` only corrects an
error message from “14” to “16”; it does not repair the calculation.

Sources retained in `author/`: complete FastEEC history, release/issue/PR API
responses, original and follow-up paper HTML, the CMS release asset, and the
official ResolvedEnergyCorrelators history. No later module or git history is
to be included in a participant directory.

## Eight distinct directions

### A — Historical bug repair / interface correctness
- Original-repository audit: `31266c6` versus `4263639` only changes the
  validation message. Changing that string demonstrably solves that delta;
  it is **not a meaningful scientific solution gap**.
- Adjacent visible start: the parent of `720b1a6` in
  ResolvedEnergyCorrelators, containing the pre-fix `RE3C.h` constructor.
- Private artifact: `720b1a6` (March 24, 2025) fixes the R2 histogram's use
  of `lin_bin2_` versus its constructor argument and supplies the missing
  explicit overflow argument. `37308db` separately replaces vector-jet-pt
  normalization by constituent scalar normalization in several modules.
- Outcome: mode-correct resolved ratio axes and consistent normalization.
- Shortcut: rescale a final histogram. It cannot repair an incorrectly
  initialized axis, misplaced overflow, or event-dependent denominator.
- Independent bottlenecks: constructor/member initialization and histogram
  argument binding; physical normalization in the multi-module writer path.
- Check: linear/log ratio endpoints, flow-bin ownership, and eventwise scalar
  sum identities, using post-fix code rather than presumed intended behavior.
- Decision: adjacent fixes are verified source gaps, but **unpiloted** under
  the four-concept budget. They were confirmed during deeper history auditing;
  no fifth concept or artificial mixture of repository states was built.

### B — Analytic continuation beyond integer projected correlators
- Visible start: v0.1 C/A integer implementation and input reader.
- Private artifact: v0.2 `eec_nu_point.h`, September 2024 follow-up
  arXiv:2409.12235, and precomputed author outputs.
- Outcome: signed fractional-order projected histograms on real jets.
- Shortcut: interpolate integer histograms, enumerate all particle subsets,
  or keep only pair terms. Integer interpolation cannot recover the
  fractional inclusion-exclusion measure; full enumeration is exponential
  in realistic constituent multiplicity; pair truncation misses cancellations.
- Bottlenecks: fractional subset weights and cancellation; tree-local
  resolution and no double counting; ensemble-scale memory/time.
- Check: independent exact small-jet enumeration, official later code,
  noninteger and near-integer branches, multiplicity-stratified CMS data.
- Decision: build **fractional** pilot.

### C — Realistic-scale high-order evaluation
- Visible start: v0.1 C/A unit-weight implementation, with the weighted and
  kT modules withheld as official private modules.
- Private artifact: v0.1 `eec_higher_weight.h`, `eec_fast_weight.cc`, and
  `eec_fast_kt_weight.cc` plus their C/A and kT unit-weight versions.
- Outcome: a batched, mode-complete weighted projected-correlator service.
- Shortcut: raise merged subjet pT to kappa, use one C/A resolution for all
  modes, or exact enumerate. These respectively change the observable,
  change the requested resolution policy, and become prohibitive at N=7/8.
- Bottlenecks: weight aggregation before/after clustering; dimensionful kT
  resolution; high-order combinatorics and reuse across queries.
- Check: all four official implementations, low-order exact checks,
  real high-multiplicity jets, momentum-rescaling and azimuth invariance.
- Decision: build **weighted** pilot, not assume difficulty in advance.

### D — Transfer from angular projection to massive subjet observables
- Visible start: v0.1 angular projector and available FastJet dependency.
- Private artifact: adjacent arXiv:2501.17218 and official
  `ResolvedEnergyCorrelators/write/src/ewocs.cc` / `ewoc_utils.cc`.
- Outcome: energy-weighted mass/angular distributions after finite-radius
  subjet clustering, with explicitly defined pp and spherical conventions.
- Shortcut: substitute mass for angle in a constituent-pair loop. That omits
  radius-dependent recombination, nonzero subjet masses, and the differing
  pp/ee energy and angular measures.
- Bottlenecks: clustering/recombination; physical observable and contact
  semantics; cross-geometry normalization and nonlinear weights.
- Check: source-derived reference adapter, exact two-body identities,
  CMS subjets plus explicitly labeled kinematic transfer fixtures. Synthetic
  transfer fixtures are not represented as real ee data.
- Decision: build **ewoc** pilot; likely useful as an empirical control.

### E — Real-data discrepancy in small-nu anomalous dimensions
- Visible start: integer CMS histograms and leading-log DGLAP predictions.
- Private artifact: follow-up arXiv:2409.12235, CMS fractional histograms,
  its reported small-nu saturation and fitted exponents.
- Outcome: distinguish breakdown of the leading-log model from numerical
  continuation bias and extract stable scaling intervals.
- Shortcut: fit one power law or extrapolate the DGLAP pole. Data outside
  the perturbative interval and small-nu behavior invalidate that shortcut.
- Bottlenecks: compute signed distributions; select defensible fit windows;
  distinguish running/mixing/model discrepancy from measurement effects.
- Check: stored data, fit-window stability, and independently reproduced
  paper fits. No detector-unfolded truth is provided by the original sample.
- Decision: retain as a candidate, **not build without a sufficiently
  independent, machine-checkable privileged fitting reference**.

### F — Recovering geometry discarded by a one-dimensional projection
- Visible start: v0.1 maximum-separation histogram implementation.
- Private artifact: arXiv:2410.16368 and later official
  `new_enc_3particle.cc` / `new_enc_4particle.cc`.
- Outcome: joint resolved three-/four-point angular distributions rather
  than a renamed projected correlator.
- Shortcut: multiply one-dimensional marginals, use only the farthest pair,
  or indiscriminately enumerate all tuples. Marginals discard signed
  orientation and conditional geometry; generic enumeration loses the
  cumulative-weight/contact structure and becomes expensive at scale.
- Bottlenecks: ordered relative-angle geometry and periodicity;
  coincidence/contact combinatorics; nonlinear phi-local prefix weights;
  high-dimensional accumulation and practical high-multiplicity execution.
- Check: later implementation, tiny direct enumeration, marginal/sum
  identities, distinct prong and multiplicity families.
- Decision: build **resolved** pilot.
- Before its first agent attempt, the reference and public contract were
  expanded from all-one weights to the existing implementation's non-unit
  nu1/nu2/nu3 branch. This was not a counterexample ratchet. The public
  contract explicitly disclaims unit normalization and phi-rebinning identities
  for that binned generalized statistic.

### G — Missing resolution and physics ablations
- Visible start: fixed-resolution v0.1 C/A code and published output files.
- Private artifact: original paper's unshipped angle-dependent-resolution
  study, its kT pT-rescaling study, and stored high-resolution outputs.
- Outcome: demonstrate calibrated accuracy/cost across pT and angle rather
  than claim that a single benchmark controls all scales.
- Shortcut: tune f on a single pT bin. Dimensionful kT thresholds and jet-edge
  behavior break that extrapolation.
- Bottlenecks: approximation bias diagnosis; scale-covariant resolution
  selection; uncertainty/cost accounting over independent ensembles.
- Check: withheld momentum strata, binwise errors and measured cost.
- Decision: candidate only. The angle-adaptive implementation is not public;
  a reference-output task is possible, but weaker than the verified modules.

### H — Exactness versus changing the observable
- Visible start: original maximum-pair-distance projector.
- Private artifact: v0.3 `eec_angles.cc` and arXiv:2410.16368.
- Outcome: scalable projected **resolved** correlators at arbitrary order,
  while preserving the distinction from the older maximum-pair observable.
- Shortcut: replace the old diameter with distances to one anchor and claim
  it is an exact acceleration. This computes a different observable; a
  noncollinear three-particle configuration separates them.
- Bottlenecks: efficient angular rank/cumulative weighting; semantic
  compatibility and contact handling.
- Check: both observables on the same real jets and separating triangles.
- Decision: candidate and diagnostic for F, not a fifth pilot. Merely asking
  for the one-dimensional new-angle kernel risks anti-compression failure.

## Pre-build anti-compression decisions

The four selected pilots have different central outcomes. None is accepted
because of a prediction that a standard solver will fail.

| Pilot | Could one fixed generic solver cover all cases? | Admission rationale |
|---|---|---|
| weighted | A generic exact tuple sum is mathematically sufficient. | Real N=7/8 constituent counts defeat it; independent weighted aggregation and kT-resolution behavior must also be integrated. |
| fractional | A generic full subset transform is mathematically sufficient. | Real CMS multiplicities defeat it; local resolution bookkeeping and signed continuation are independent requirements. |
| resolved | Generic full tuples cover integer observables. | Joint conditional geometry/contact terms and scale-efficient cumulative weighting are separate scored branches; 3- and 4-particle families are reported separately. |
| ewoc | Standard clustering plus a pair sum may solve it. | Two independent integration branches, clustering and pp/ee physical observable conventions, justify an empirical pilot, not a presumption of frontier difficulty. |

No pilot asks for a detector correction inferred from uncorrected CMS data.
No arbitrary precision threshold, malformed file, or withheld convention is
to be used as the central difficulty. Exact definitions belong in public
interface contracts; solution algorithms and reference outputs stay private.
