# Collective-fluxoid ratchet: validated private integration packet

## Decision and limits of evidence

The frozen proposal is scientifically valid and has a genuine resource-bounded
passing executable. It is **ready for Main's review/integration**, not an
unqualified assertion of clean-low-load champion failure. No fresh model was
launched; no original participant, evaluator, archive, or root status was edited
by this builder. All assets here remain private until Main approves publication
of the explicit `candidate_public` allowlist.

Twenty-four physical cases were searched. Thirteen cold-champion gaps were at
least 0.5. After all 24 warm replays, only six retained both a gap at least 0.5
and meaningful winding changes. Ordinary pinning and vortex cases were largely
robust; the incomplete `analysis_partial.json` is not the final result. Rather
than manufacture three families, the proposal selects **three cases in one
collective-fluxoid family**. The other three surviving cases are not hidden
targets. Two become development examples, without exposing their witness fields.

## Frozen energy target

`focused_proposal/manifest.json` stores exact baseline/witness arrays and hashes;
`focused_proposal/target.json` fixes the objective. No new references are fitted
to the repeated champion or fresh submissions.

| Case | Active sites / holes | Frozen B | Private attained W | Gap | Changed hole windings |
| --- | --- | ---: | ---: | ---: | ---: |
| nf01 | 4,840 / 48 | -1680.027801600737 | -1687.818806762435 | 7.791005161698 | 30 |
| nf02 | 5,828 / 49 | -1999.743913953164 | -2010.212492391659 | 10.468578438494 | 26 |
| nf04 | 6,954 / 64 | -2697.151165912640 | -2708.314629666345 | 11.163463753705 | 23 |

Each JSON's initial field is **exactly B's field**. Returning it is valid with
zero closure, independent of timing. This removes artificial no-regression
failures from stochastic baseline replays. The baseline executable is the exact
generation-1 champion, not a weaker replacement.

For checked energy E, closure is `clip((B-E)/(B-W),0,1)`. The three-case mean is
both core and worst-family score. The unchanged thresholds are **0.65 core /
0.45 worst family**; with one family, 0.65 is binding. Each case must also satisfy
the unchanged stationarity, no-regression, 60-second wall/CPU, one-core, 2 GiB,
256 MiB scratch, and 4 MiB compressed/decompressed NPZ conditions. Witnesses are
attained feasible upper bounds on the unknown minimum, never ground-state claims.

## Unchanged champion replay

Two sequential repeat sets use the **same frozen inputs**, not a chain of improved
starts. All six outputs independently pass feasibility and resource checks.

| Repeat | nf01 closure | nf02 closure | nf04 closure | Core = worst family |
| --- | ---: | ---: | ---: | ---: |
| 1 | 0.206331245372 | 5.43e-12 | 2.00e-11 | 0.068777081799 |
| 2 | 1.90e-11 | 5.43e-12 | 2.00e-11 | 1.48197e-11 |

Trusted payload CPU is **47.20–54.07 seconds**, wall **54.29–54.80 seconds**,
and CPU/wall **0.8646–0.9866**. Idle-core selection could not guarantee quiet SMT
siblings on this shared host. Thus these are repeated, sequential, resource-valid
quality failures, **not uniformly clean low-load tests**. Main must accept this
caveat or obtain a controlled low-load confirmation before claiming that stronger
condition. An already-launched 180-second exact-champion-engine diagnostic is
recorded separately in `report.json`; it cannot replace the 60-second contract.
That diagnostic finishes in 174.11–174.61 seconds: nf01 reaches
-1682.679606631535, while nf02 and nf04 remain at their frozen-baseline energies
within 2.4e-10. It still fails the quality target. This longer-search evidence
supports the collective-sector diagnosis without pretending to satisfy a
resource-bounded or controlled-low-load test.

Preliminary `focused_champion_repeat_*` runs are excluded from CPU certification:
outer Bubblewrap `wait4` measured only launcher CPU on this host. The corrected
`cpu_monitor/run.py` is a read-only, non-dumpable trusted parent inside the
namespace. It waits for the actual solver and adopted descendants; its accounting
descriptor is not inherited by the solver. Payload logs are separate. A probe
confirms parent-descriptor access is denied and forged stdout timing is ignored.
The monitor adds no submission privileges and mounts no witness directory.

## Constructive achievability

`challenger/solve.py`, with sibling `engine.py`, is an ordinary executable that
uses only its input arrays. On the exact focused input bytes, the previously
completed 60-second sandbox qualification attains **core/worst 0.999999999989**,
runtime score **0.105497352367**, with all outputs valid. Wall times are
53.49–53.77 seconds. The original six-case qualification also passed at
0.826308239436 / 0.500000000007. These are independent field rechecks of real
resource-bounded runs, not witness-field lookup or a claim that expensive
portfolio fields alone prove solver feasibility. The newer protected payload
CPU monitor was not used in that earlier qualification; the same one-core helper
and hard 60-second CPU limits were used.

The algorithm supplies correlated hole-winding candidates, then relaxes the full
continuous complex field with the champion's nonlinear optimizer. Geometry and
fluxes are inferred from the input, without IDs, stored solutions, or target
energies. It can reach these ordered-loop witnesses rapidly; this packet makes
**no claim that a future agent will find the task hard** or that the proposed
algorithm generalizes to every physical geometry.

## Scientific bottleneck and checks

The selected grains have 48–64 near-half-flux perforations separated by narrow,
connected superconducting bridges. nf01 has weak flux/material perturbations;
nf02 adds a small alternating flux bias; nf04 staggers the hole geometry and
contains 57 suppressing pin patches. All stiffnesses are positive (1.2).
Solenoidal flux lies inside vacuum holes; active-link phases are exact physical
vector-potential integrals plus pure gauge, not independent random bond phases.
The declared model is finite-lattice, fixed-vector-potential, near-Tc GL, not
SuperConga Eilenberger, screening, or a continuum-limit assertion.

The remaining error is collective winding allocation across coupled loops.
Witnesses change 30, 26, and 23 reliably measured hole windings, not numerical
plaquette noise. Tight L-BFGS polishing improves B by only 1.29e-9, 6.18e-10,
and 2.26e-9, with no winding change, compared with 7.79–11.16 energy-unit witness
gaps. This diagnoses a topological-sector search issue rather than a loose
gradient tolerance or a simple scale increase. Stationarity is verified; no
uncomputed Hessian certificate is asserted.

`validation.json` passes nine classes of checks on all 24 physical cases:
directional finite differences, independent energy and gradient agreement,
gauge-invariant energy and covariant gradient, exact uniform zero-field energy
and gradient, physical plaquette flux, connectivity, and positive stiffness.
Focused plaquette errors are at most 1.61e-15. `focused_validation.json` passes
ten evaluator tests, including family cardinality, missing/duplicate cases,
feasibility, frozen public starts, exact reference recomputation, public asset
allowlisting, and a compressed NPZ bomb rejected before `np.load`.

## Files to hand off

- `focused_proposal/manifest.json`, `focused_proposal/target.json`: private frozen target.
- `candidate_public`: complete safe public tree; only this tree may be exposed.
- `candidate_public_manifest.json`: public hashes and explicit no-witness policy.
- `focused.py`: runnable sidecar evaluator, including three-case aggregation.
- `challenger/solve.py`, `challenger/engine.py`: qualified executable, private.
- `report.json`, `status.json`, `packet_manifest.json`: machine-readable summary and hashes.
- `INTEGRATION.md`: both cardinality checks, supplied-baseline contract, accounting caveat.

Main owns final integration, archive preservation, sandbox policy, and fresh
launches. Do not mount this private packet or the archived champion directory
as participant/submission content.
