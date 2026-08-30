# Interface and physical contract

## Scope and submission

Primary mode F: repair an existing workspace, not reconstruct EERAD3.
Only `kinematics.f`, `phaseee.f`, and `eerad3lib.f` are compiled from your
artifact. You may add helper routines inside those files. They are GNU
Fortran fixed-form sources. Preserve external symbols, binary64 argument
types, and common-block layout. Changing the driver, Makefile, evaluator,
input, or baseline does not change evaluation. No extra dependencies,
external I/O, subprocesses, timing manipulation, or case identification.

The baseline consists of exact routine-body extracts from the supplied
official release; provenance and the upstream GPL are included. The 2014
release also contains this map in `src/aversub1.f`; the selected release
adds the `mapmomenta` bookkeeping exercised here.

## ABI

Vectors are `(px,py,pz,E)`, metric `(+---)` with energy in position four.
All real external arguments and common blocks are `real(8)`.

- `fillinv(n,p,sij)`: `p(4,n)`, `sij(n,n)`; return dimensional
  `sij(i,j)=2 p_i.p_j`, symmetric, with exactly zero diagonal.
- `dot(a,b)`: return the same massless physical Minkowski product divided
  by two relative to `sij`. Its domain here is positive-energy null vectors,
  not arbitrary massive/off-shell vectors. Binary64 input energies have
  rounding error: the reference null representative keeps spatial
  components and takes `E=|p|`. Do not resolve tiny collinear invariants
  by treating those energy-rounding residuals as physical masses.
- `pmap5to3(i1,i2,i3,i4,i5,j1,j2,j3)`: input indices permute 1..5;
  output indices permute 1..3. Antenna `(a,1,2,b)=(i1,i2,i3,i4)` maps
  to `(A,B)=(j1,j2)`; `i5` is copied to `j3`. Preserve the DAK2 branch,
  weights, and resulting map, not merely its shells.
- `DAK2(ya1,ya2,y1b,y2b,y12,yab,x,r1,r2,y)` remains available.
  It is exercised through the map, not graded as a standalone formula.
- `rotatetoz(a,rmat)`, `unrotatetoz(a,rmat)`: `a(4)`, `rmat(4,4)`;
  return a proper spatial rotation aligning nonzero `a(1:3)` to positive
  z, and its inverse. Time components remain identity. Preserve the
  well-resolved upstream convention; at coordinate singularities any
  continuous valid alignment is acceptable, with no global continuity
  requirement at the poles.

Common blocks: `/pmom/ p(4,5)` (input), `/yij5/ y(5,5)` (input),
`/pcut/ ppar(4,5)` (first three columns output), `/s3/ s12,s13,s23`
(output in canonical output-slot order), `/mapmomenta/ p5(4,5),p4(4,4),p3(4,3)`.
The `p3` array must duplicate the three mapped output slots; `p5,p4` are
not outputs of this operation. The driver calls `fillinv`, divides its
result by `Q^2` where `Q=sum(E)`, populates `/yij5/`, then calls the map.
`/s3/` must contain dimensionless `2 P_i.P_j/Q^2`; momenta stay dimensional.

## Domain and accuracy

Every input is a future-directed five-particle massless CM event to
binary64 rounding. Energies are strictly positive; exact singular
antennae and zero denominators are excluded. Families cover generic,
soft, double-collinear, triple-collinear, nearly parallel radiators,
rotations, relabelings, and common rescalings. Energies span overall
scales `1e-90..1e90`; soft fractions can approach `1e-16`, opening angles
`1e-12`, and radiator openings `1e-10`. Rotation axes can have component
ratios near `1e-200` and magnitudes `1e-70..1e70`. No special axis gauge
or particle labeling may be assumed. Arbitrary valid radiator choices
are allowed, not just well-separated endpoints.

Accuracy is measured against an independent high-precision massless
geometric oracle and physical properties. After division by Q, mapped
components have absolute tolerance `3e-9`; mass squares divided by Q²
have tolerance `3e-10`; conservation has tolerance `3e-11`. Mapped
invariants have absolute tolerance `3e-9`. Input pair invariants divided
by Q² require relative error `3e-8` plus absolute `1e-29` (the absolute
floor is not a license to discard resolvable small invariants). Rotation
orthogonality/alignment/inversion tolerance is `3e-12`; spectator and
`p3` bookkeeping tolerance is `1e-14` after normalization. Well-resolved
events additionally require mapped component and invariant agreement
to `3e-12`. Hard-limit identities are checked with a bound proportional
to the unresolved scale plus numerical slack. All cases and all
families must pass; mean scores alone do not establish success.

Near parallel radiators, the map orientation is ill-conditioned. If their
unit-direction chord length `d` is below `1e-4`, map-component comparison
allows additional absolute slack `16*epsilon_binary64/d` in units of Q,
and mapped-invariant comparison allows twice that slack. Shell,
conservation, invariant-consistency, spectator, and rotation checks are
not relaxed. The reference always uses the actually received values.

## Evaluation distribution

Generation two retains all 104 original correctness events and adds 1,620
stratified light-antenna events: 180 each with balanced openings, hierarchical
openings, one soft radiator, two soft radiators, two soft unresolved particles,
nested collinear structure, and three broader-opening strata with hard, one
soft, or two soft radiators. All 1,724 events and all 18 families must pass.
The same complete mixture is used for timing; there are no per-family timing
weights or hidden alternative numerical tolerances.

The tightly collimated strata have characteristic openings `1e-10..1e-4`;
internal nested openings extend to `1e-12`. Hierarchical strata include
internal openings through about `4.2e-4` while radiators approach `1e-10`.
The broader light-antenna strata have internal openings approximately
`6.3e-4..5.2e-2` and radiator openings `1e-10..1e-6`. Radiator or unresolved
energies may be simultaneously suppressed by factors down to `1e-14`,
with overall energy scales `1e-85..1e85`. Directions, input/output labels,
and scales vary. Exact degeneracies are excluded.

This is a stratified production-kernel stress workload, not a claim about
the relative frequency of events in a measured cross section. No jet-resolution
or event-shape acceptance cut restricts the mapping kernel's existing domain.
All original accuracy requirements, including the orientation uncertainty
allowance, remain unchanged.

## Build and stream protocol

From `participant/workspace`: `make`, then
`./mapping_driver < ../input/examples.txt`. GNU Fortran 11 or later is
required. The evaluator supplies its own identical trusted driver and
uses `gfortran -O2 -fno-fast-math -ffp-contract=off
-ffixed-line-length-none -std=legacy kinematics.f phaseee.f eerad3lib.f
driver.f90 -o runner`.

Input: first line `N repeats`; for each event, five rows of four vector
components, one line containing five input and three output indices,
then one row with the four-component rotation axis. No family labels
or oracle answers enter the executable.

Output: one line per event with 84 whitespace-separated binary64 reals,
Fortran column-major array order: normalized input invariants (25),
mapped momenta (12), `s12,s13,s23` (3), `p3` (12), rotation (16), inverse
(16). The final line is `TIME cpu_seconds checksum`. The trusted driver
times repeated in-memory execution, excluding compilation and text I/O.
Public `examples_expected.json` provides map and invariant references;
rotations can be validated by alignment, orthogonality, and inversion.

## Resource contract

The candidate must cost at most 18 times the unmodified source-native
baseline, preserving the generation-one ratio rather than tightening it.
Five adjacent baseline/candidate pairs alternate execution order and run
sequentially on the same pinned CPU. The score uses the median of the five
paired ratios, not the ratio of two separately collected medians.

A read-only Python supervisor inside the isolated PID namespace obtains
CPU consumption from kernel child accounting after reaping the native
process and all adopted descendants. Candidate-reported `CPU_TIME` is
diagnostic only and cannot determine the score. Whole-binary CPU includes
startup, input parsing, output formatting, and repeated kernel execution;
compilation and the supervisor's own CPU are excluded.

Before pairing, only the pristine baseline selects a common repeat count,
starting at 500 and increasing if necessary to reach at least 0.5 CPU
seconds, with a maximum of 20,000 repeats. Every measured baseline trial
must meet that minimum or the measurement is invalid and must be rerun.
This minimum amortizes measurement overhead; no artificial time floor is
added to either measured cost. A candidate warmup and every measured
execution must produce identical numerical records.

Compilation has a 45-second wall timeout; each isolated execution has
40 seconds wall/35 seconds CPU, a 37-second supervisor deadline,
1 GiB address space, and a 32 MiB file limit. Network and host task files
are absent. Evaluation emits `core_score`, `worst_family_score`,
`runtime_score`, `passed`, and `reason`, plus paired trusted timings.
