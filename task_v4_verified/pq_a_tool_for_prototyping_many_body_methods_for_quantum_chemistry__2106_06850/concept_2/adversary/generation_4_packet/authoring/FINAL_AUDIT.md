# Final private investigation audit

**Outcome: feasibility unknown. Best trusted core score: 0.0. No passing witness
and no universal impossibility proof were obtained.** The main worker retains
the fresh-attempt and final-status decision.

## Shutdown and isolation

The bounded investigation ended at 06:14:32 PDT on August 28, 2026, after 38.48
wall minutes. A wrap-up check at 06:21:28 PDT found both `jobs -l` and `jobs -pr`
empty. No further numerical search was launched during wrap-up.

All 20 pinned participant/evaluator file hashes were checked again and match.
No frozen public file, evaluator, manifest, or main readiness/status file was
changed. No active v4/v4_r2 submission or source was read, and no agents were
launched. All investigation changes remain inside this private `authoring/`.

## Trusted scores and violations

Seven final artifacts were independently evaluated with the unchanged trusted
scorer. **Every artifact scored zero and returned `robust_constraints_failed`.**
All 243 endpoints were evaluated for each artifact: **1,701 endpoint evaluations**.
All failed endpoint gates, so the scorer correctly skipped continuation work:
**zero generation-four path certificates were evaluated in this final portfolio**.
These are not partially credited or certified passing witnesses.

The known generation-three private seed has only the two new energy-error
failures. Its worst observed population violation is 0.02044251634925809 and
maximum DAD is 0.000969211546716603, but its maximum energy error is
0.000230401741981634, above 0.0001. The worst normalized margin is
-1.30401741981634 at point 241. Trusted runtime: 3.853108692 seconds; core: 0.

The density-quiet direct-probe optimization candidate `finite_author` has
maximum energy error 0.00021383115786433038, population violation
0.020050000202194433, and maximum DAD 0.0009900005422413618. It fails two energy
checks and four exact-gap checks. Worst normalized margin: -1.1383115786433038
at point 242. Trusted runtime: 4.641822168 seconds; core: 0.

The lowest maximum energy error among all seven artifacts is
0.00019536400083808303 (`reduced_gen1`), but that artifact also misses the
population target and fails density, gap, and reference-weight screens. It is
not a better admissible witness. All seven tie at the only certified score, zero.

Complete per-artifact scores, worst constraints, failure clusters, coverage,
runtimes, and artifact hashes are in `portfolio_certification_final.json` and
the individual reports under `certified_portfolio_final/`.

## Numerical coverage and proof scope

- 310 state-relaxation multistarts across exact-right, nearby-ground, both
  population branches, and Rayleigh-compressed variants.
- Four Hamiltonian-only stationary-root optimization portfolios seeded only by
  completed earlier witnesses; two bounded direct finite-neighbor optimizations;
  simultaneous three-root explorations; and two fixed-state inverse solves.
- Independent finite-difference checks of private implicit response derivatives.
- An exact rational Rayleigh sign certificate excluding one stored relaxed tuple
  from an exactly stationary, Hermitian positive-gap realization.

The observed relaxed gradient minima are **not global lower bounds**. The exact
rational certificate concerns **one tuple only**, not the whole allowed domain
or numerical tolerance envelope. Neither a universal derivative bound nor the
additional finite-curvature control needed to rule out the actual probes was
proved. See `OBSTRUCTION_NOTES.md` and `exact_relaxed_state_exclusion.json`.

`FINAL_AUDIT.json` supplies the machine-readable wrap-up. The full chronology,
search summaries, and isolation checks are in `investigation_report.json` and
`INVESTIGATION_REPORT.md`. These private findings do not establish empirical
fresh-agent hardness and do not change the main worker's status decision.
