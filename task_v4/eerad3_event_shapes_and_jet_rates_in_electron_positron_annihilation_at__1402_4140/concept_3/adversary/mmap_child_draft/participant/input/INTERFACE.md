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

Generation two preserves all 104 original correctness cases and the complete
1,620-case initial light-antenna challenge, then adds 8,280 independently drawn
events. The resulting one-pass batch has 10,004 distinct momentum inputs and
18 scored families. Each of nine light-antenna strata has 1,100 cases:
balanced, hierarchical, one soft radiator, two soft radiators, soft unresolved
particles, nested collinear, and three broader-opening strata with hard,
one-soft, or two-soft radiators. There is no duplicate momentum input within
a native process, no warmup pass, and no replay loop. Every returned record
in every measured trial is checked against its numerical reference and the
physical contract; no checksum or sampled subset substitutes for those checks.

Tight internal openings reach 1e-12, radiator openings approach 1e-10,
and the broader light-cluster strata have internal openings approximately
6.3e-4..5.2e-2 with radiator openings 1e-10..1e-6. Soft suppression factors
reach 1e-14; common scales range 1e-85..1e85, in addition to the original
cases. Exact degeneracies are excluded. This stratified kernel stress mix
does not claim to reproduce cross-section frequencies; no observable or
jet-resolution cut narrows the existing mapping domain. All original quality
tolerances and orientation allowances above remain unchanged.

## Build and binary stream protocol

The external Fortran ABI above is unchanged. Only the three kernel source
files are submitted. The evaluator supplies the identical trusted binary
driver included in the workspace. Build with `make`; for the public examples:

```
python3 ../input/binary_io.py encode ../input/examples.json examples.bin
python3 ../input/binary_io.py run examples.bin output.bin --executable ./mapping_driver
python3 ../input/binary_io.py decode output.bin
```

All binary fields are little-endian, without padding or Fortran record markers.
Input starts with the eight-byte magic (seven ASCII bytes `ERAD3B4` and one
zero byte), then a uint32 case count N and a zero uint32 reserved word. This
16-byte header keeps binary64 arrays aligned. Four contiguous buffers follow,
in this order: momenta(4,5,N) in binary64, labels(5,N) in int32, slots(3,N)
in int32, and axis(4,N) in binary64, all Fortran column-major. There is no
interleaving of event fields. The native driver maps these resident arrays
directly and performs no batch allocation, zeroing, or I/O copy. Output starts
with the eight-byte magic (seven ASCII bytes `ERAD3O4` and one zero byte),
a uint32 count, and a zero uint32 reserved word, then 84 binary64 values per event
in the original array order: normalized invariants (25), mapped momenta (12),
mapped invariants (3), p3 bookkeeping (12), rotation (16), inverse (16).
There is no TIME/checksum trailer. Extra bytes, wrong counts, and malformed
headers fail. The previous ASCII examples remain readable illustrations,
but the executable accepts the binary protocol, not the old repeat count.
The executable expects seekable input on descriptor 0 and a readable/writable,
prepopulated output file on descriptor 1, not an output pipe or empty file.
The public `run` helper prepares these buffers and reports a local direct-child
CPU diagnostic; only the evaluator supplies the authoritative paired score.

## Resource contract

The production CPU limit is not yet calibrated; no fresh attempt is allowed.
The predeclared calibration rule is the smaller of 8 and 0.45 times the
smaller of two independently measured generation-one incumbent median paired
ratios, rounded downward to 0.001. Each campaign compiles and executes new
native processes and checks all their numerical records. The two incumbent
medians must agree within a factor of 1.30, and each paired-ratio relative
median absolute deviation must be at most 25%; otherwise no target is committed.
Preparation also requires a numerically passing private feasibility control
to use at most 80% of that independently determined limit in both campaigns.
This requires more than a twofold measured throughput improvement over that
incumbent, rather than carrying over the old repetition-based 18x allowance.
The resulting numerical limit is fixed in RESOURCE.json before any fresh
generation-two attempt. It is not fitted to a private candidate's score.

Five adjacent baseline/candidate pairs alternate order on one pinned CPU.
Each native process handles the unique batch exactly once. A read-only
in-namespace supervisor measures kernel RUSAGE_CHILDREN after reaping the
native executable and all adopted descendants. All native startup, binary
I/O, and mapping CPU count; compilation and the supervisor's own CPU do not.
Before native execution, the supervisor stages the supplied binary bytes in
a fresh sealed RAM-backed input file and physically populates a fresh shared
output file with its header and zero records. The native executable is not
spawned until after staging and the initial trusted CPU counter read; it cannot
precompute during this phase. Native mmap, startup, array access, computation,
output writes, and descendant CPU remain fully charged. This models a native
caller supplying resident arrays without charging repeated transport copies
or bulk page zeroing to a short numerical kernel.
No native timer is used. The score is the median of the five actual CPU
ratios; neither denominator floors nor repeat amplification are applied.
Trusted user CPU, system CPU, and wall time are reported separately for each
run to expose I/O overhead or scheduling variability. Valid numerical
evaluations emit valid=true. Invalid submissions and infrastructure/measurement
errors emit valid=false, zero scores, and a distinct error_kind; infrastructure
failures do not establish numerical or performance hardness.

Compilation uses a writable scratch directory; execution mounts that same
compiled /work read-only. Every run receives fresh /tmp, /dev, PID, network,
and IPC namespaces. There is no writable state shared across native processes.
Thus within-batch input memoization has no duplicate hit and filesystem caches
cannot carry expensive answers into another trial. Submission code may not
identify hidden cases, access external data, fork subprocesses, or manipulate
timing/output. Host reference files and prior submissions are never mounted.

GNU Fortran flags remain -O2 -fno-fast-math -ffp-contract=off
-ffixed-line-length-none -std=legacy. Compilation has 45 seconds wall time.
Each native run has 35 seconds CPU, a 55-second supervisor deadline and
60-second outer wall timeout, 1 GiB address space, and bounded 32 MiB files.
