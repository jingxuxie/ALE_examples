# Scientific provenance and scope

## Primary sources actually inspected

- The parent task's `private/CANDIDATES.md`, especially directions A/C and the
  explicit warning that the later 39-qubit code/data are unavailable.
- Harper, Flammia and Wallman, arXiv:1907.13022v2, *Efficient learning of quantum
  noise*: Methods, Gibbs Random Fields; Figure 4; supplement IV, Scalable
  Estimations. These describe positive factorized noise models, inference from
  local marginals, and a nearest-neighbor chain demonstration reaching 100
  qubits. The supplement distinguishes learning local parameters from obtaining
  the global normalization. It does not supply a ready-made universal topology
  learner for this pilot.
- Official `rharper2/Juqst.jl`, `src/marginal.jl`: local marginal axis conventions,
  both `gibbsRandomField` variants, `getGrainedP`, and grouped
  `conditionalMutualInfo`/`getSummand`. We inspected `git show 08101ff`, not merely
  a changelog description. The preserved patch changes the flattened XY stride
  from the Y cardinality to the X cardinality. Equal-size X/Y blocks conceal
  the defect; unequal blocks can yield wrong values or an out-of-range index.
- Harper and Flammia, arXiv:2303.00780v1, *Learning correlated noise in a 39-qubit
  quantum processor*: Appendix F, equations F1--F10, gives Markov conditions,
  binary-monomial couplings, and inversion of conditional log probabilities.
  Section VII says code/data are available on reasonable request. **Neither was
  obtained.** The paper is a mathematical source, never a code/data oracle.

Source locators, checksums and checkout revision are in `source_manifest.json`;
the actual upstream correction is in `juqst_08101ff.patch`. The first paper's
local PDF is checksummed and its supplement was read in the public rendering; Appendix F
and the availability statement of the adjacent paper were read from its public
PDF. The source capture script needs the existing parent checkout, not a network
download. Julia is not installed in this author environment. We execute a
Python translation of the corrected CMI indexing, not the upstream Julia
package. Entropy-based and exhaustive checks independently validate that port.

## What is new here

All models, observations and targets are author-generated, not downloaded
experimental data. We use `theta_S = -J_S` relative to the sign convention in
F2, and fix the redundant constant potential to zero. For a center i whose
observation envelope contains its Markov blanket,

`log p(x_i=1,b) - log p(x_i=0,b) = sum_{S contains i} theta_S prod_{v in S\{i}} b_v`.

The reference screens grouped and single conditional dependencies with the
fixed CMI routine, then inverts this local binary polynomial and reconciles
duplicate coefficients across centers. This is an author implementation of
local parameter reconstruction motivated by the cited formulas, not a copied
39-qubit implementation. Unnecessary observation-envelope edges have zero
conditional dependence; mediated marginal correlations need not be zero.

The generator uses chains, two-leg ladders with cycles, and chains of stems
carrying three-body leaf branches. Their actual pathwidth is at most two, so
the published treewidth-at-most-three promise is conservative. Parameters,
labels, scope orders, candidate distractors, bursts, masks and activities vary.
The challenge pool has independent seeds, larger/different sizes and shifted
activity values. Six further seed/region cases are tested without storing
their answers in the participant tree.

The activity operation is exactly `p_a(x) proportional to p(x)*a^|x|`. It is a
specified statistical reweighting, **not** the continuous-time physical noise
extrapolation of the later experiment. Weight/parity/burst events are diagnostic
queries, not logical failure rates from an error-correcting decoder.

## Scientific caveats

- This is the ideal, exact-local-distribution limit. There is no finite-shot
  estimation, SPAM-fitting stage, inconsistent-marginal reconciliation problem,
  or robustness guarantee for those experimental complications.
- Binary GRFs can describe stochastic binary support errors (for example an
  X-only Pauli channel). We do not identify these arbitrary synthetic marginals
  with the observed-error cone of an actually Clifford-twirled device, nor
  recover separate X/Y/Z channel probabilities.
- Bounded degree alone does not make general partition functions tractable.
  Efficient exact inference here relies on the explicit bounded-width promise.
- Extremely small high-weight events stress numerical inference; they are not
  claims of experimentally measurable relative precision at those probabilities.
- Canonical pair truncation and a pair-MI spanning tree are controlled
  implementation ablations, not optimal refits of every possible lower-order
  model and not evidence about the unavailable 39-qubit dataset.
- No fresh agent, tournament or isolated ultima-alpha attempt was run by this
  worker. Empirical contestant hardness remains for the main author's attempts.
