# Weak-spin reference checkpoint

## Status

The V=0.5, spin-one, L=32, T=8 candidate has **no accepted reference**.
Its unchanged-submission evaluation has not started. The bounded copy-only
canonical-readout diagnostic is complete. The V=1, T=10 fine reference remains
running at handoff. No refinement is authorized automatically: report both
measured convergence and projected cost to main before any larger run.
The acceptance threshold remains 0.97; neither an unconverged label nor a
public-contract violation can count as participant failure.

## Completed V=0.5 reference pair

| Quantity | Coarse | Fine |
|---|---:|---:|
| Fourth-order timestep ceiling | 0.1 | 0.05 |
| Bond cap / observed maximum | 96 / 96 | 192 / 192 |
| Wall seconds | 251.466251 | 2496.605652 |
| Fine CPU seconds | — | 2343.326035 |
| Accumulated discarded weight | 0.210961901 | 0.034092589 |
| Fine peak RSS, KiB | — | 328436 |

The maximum-difference, weak-scale normalized geometric convergence diagnostic
is **0.888478489755398**, not 0.97. The less conservative RMS geometric
comparison is 0.9652107438860102. These are numerical diagnostics, not rigorous
error bounds.

| Output block | Maximum absolute change | Weak scale | Max-difference component |
|---|---:|---:|---:|
| Density | 0.015815191111453 | 0.444998230020205 | 0.921425237685802 |
| Violation | 0.004981442562523 | 0.118404920124621 | 0.907671613743533 |
| Connected correlation | 0.001033211884954 | 0.008084525054531 | 0.745072981055631 |

The Hamiltonian charge-commutator residual is zero and the final MPS charge
label is `[0]`. Nevertheless, summing the returned fine densities with
alternating signs gives -0.00004598802116184686 at T=8. This fails the sidecar's
additional observable-charge check (1e-8). The discrepancy is a **reference
diagnostic**, not evidence against the participant. The separate coarse
copy-only experiment below establishes a canonical-readout problem on that
coarse state; the fine state has not undergone this diagnostic. The convergence
gate already fails independently of this check.

Evidence: `references/weak_spin1_V0p5_L32_T8/coarse.json`, `fine.json`, and
`convergence_coarse_fine.json` under the same directory. Full raw arrays are
preserved. Fine reference SHA-256:
`6d9357e17d99c6814e0d91cd583f082b29510a577edce1acf5b2f230bb0b2235`.

## Refinement cost checkpoint

The measured coarse-to-fine wall multiplier is 9.92819, CPU multiplier 9.32608.
Applying that wall multiplier again would suggest approximately 6.9 hours for
384 / 0.025 on this candidate. A deliberately broad 8–16 times fine-runtime
projection gives 5.5–11.1 wall hours (5.2–10.4 CPU hours), allowing for doubled
step count and growing block-SVD work. This is only a scaling estimate:
charge-sector populations, truncation, and host contention can change it.
Neither that cost nor convergence at the proposed level is guaranteed.

No 384 / 0.025 run has been launched. Existing valid fine work is not interrupted.

## Bounded copy-only diagnostic: complete

`canonical_diagnostic.py` calls the unchanged `charge_engine.predict` with the
frozen T8 case and coarse settings. A process-local TEBD subclass only observes
the evolving state. At each requested output time it records direct readout and
`norm_test()`, calls `state.copy()`, canonicalizes the copy with
`canonical_form(cutoff=0)`, then measures and checks the copy. It never replaces
the evolving state. This is an author diagnostic, not an official engine fix or
an accepted replacement reference.

The installed TeNPy MPS implementation documents deep copying of B/S values
(`authoring/runtime/tenpy/networks/mps.py:1702`), canonical checks (`:4398`), and
in-place finite canonicalization (`:4453`). The official MPS API documents the
same operations. The installed `authoring/runtime/tenpy/algorithms/tebd.py:831`
recommendation occurs in a random-unitary-evolution example, not a general
error guarantee. Primary API locator:
`https://tenpy.readthedocs.io/en/stable/reference/tenpy.networks.mps.MPS.html`.

The diagnostic completed normally in **234.291844 wall seconds**,
235.033592 CPU seconds, with peak RSS **271384 KiB**; the wall cap was 900s.
All eight measurements are preserved in
`diagnostics/canonical_coarse_T8/result.json` and individual measurement JSONs.

| T=8 coarse measurement | Direct | Canonicalized copy |
|---|---:|---:|
| Maximum `norm_test` entry | 0.000142034049506 | 2.801711029165142e-15 |
| Sum of alternating-sign densities Q | -0.000292280618435 | -3.552713678800501e-15 |
| Algebraic MPS sector | 0 | 0 |

Across all times, the largest post-canonicalization absolute Q residual is
1.687538997430238e-14 and maximum `norm_test` entry is 7.11777734565872e-15.
Before/after fingerprints of the evolving B/S tensors, canonical-form flags,
norm, and bond sizes match at every measurement. Bond sizes of each copy also
remain unchanged. The direct output reproduces every frozen coarse density,
violation, and correlation value **exactly** (maximum differences all zero),
and the accumulated discarded weight remains 0.2109619011385299. Frozen source
hashes remain unchanged. Thus the observed repair is to measurement of the same
truncated state, not feedback into its dynamics.

| Output block | Maximum canonical-readout change | Fraction of original coarse/fine maximum gap |
|---|---:|---:|
| Density | 0.000149166470170 | 0.009431847464 |
| Violation | 0.000082439875255 | 0.016549397934 |
| Connected correlation | 0.000017420098670 | 0.016860141587 |

This confirms canonical-environment measurement drift on the coarse state,
not actual charge breaking. The coarse-side readout corrections are at most
1.69% of the previous blockwise maximum coarse/fine differences. They do not
establish reference convergence. Fine-copy readout is unmeasured, and the
remaining discrepancies have not been separated into timestep versus bond
truncation error. The original 0.888478 convergence result is retained, with
no accepted label and **no participant failure or participant score**.

## Job handoff

- Copy-only diagnostic: unified exec session **41310**, completed, exit 0.
- Existing four-reference parent: unified exec session **9140**, still active.
- Remaining child: host PID **3382962**, parent PID **3382856**, CPU affinity 380,
  `probe.py reference --case weak_spin1_V1_L32_T10 --level fine --cpu 380`.
- Last host check: elapsed **58m19s**, CPU **43m00s**, state `R`, RSS 318980 KiB.
- Its log is `logs/weak_spin1_V1_L32_T10_fine.log`; completion writes
  `references/weak_spin1_V1_L32_T10/fine.json`. It has not been interrupted.
- Once it finishes, main can run `probe.py assess --case weak_spin1_V1_L32_T10
  --level fine`. Do not infer acceptance from successful execution alone.
- No submission evaluation, larger reference, or ratchet has been launched.

Main owns the decision on reference closure. This sidecar does not weaken the
0.97 gate, alter the original frozen engines/labels, or claim a counterexample
from unvalidated targets.
