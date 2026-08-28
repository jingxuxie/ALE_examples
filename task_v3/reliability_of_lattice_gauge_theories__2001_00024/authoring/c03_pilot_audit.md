# c03 bounded post-pilot audit

## Scope and evidence status

Only this audit document is written. No participant, submission, reference,
pool, evaluator, or other author artifact is modified by this auditor. No solver, evaluator,
Codex agent, new case, or ratchet is run by this auditor. Main executed the
original screening/challenge evaluations and the two timing-fair screening
retries. Both original splits are now accounted for below. Confirmation was
not evaluated as part of this audit.

Paths below are relative to the task root
`tasks_v3/reliability_of_lattice_gauge_theories__2001_00024`.

Run metadata: `authoring/runs/c03_resonance_compiler/screening/result.json`
records exit code 0, `timed_out=false`, elapsed authoring time
1540.0294754505157 seconds, and `participant_unchanged=true`.
That elapsed time is NOT per-case solve time. Current core hashes match the
submission hashes recorded by the run:

| File under `pilots/c03_resonance_compiler/attempt/` | SHA-256 |
|---|---|
| `solver.py` | `202138fccdc3141c68c1c7b1334d3081e7dc0bd285727d0b7087a7899b95d6f7` |
| `optimizer.cpp` | `f88ce88e33ba5e6c68a9091f26bdd4bea7510606b9c4126114fe85c774f27583` |
| `optimizer.so` | `3da591d7faab1c165360382f9b8724294254dbd674ff22532d2a226914aaea1f` |

I read the Python implementation and all 309 lines of its native optimizer.
The source and binary are both present; this audit does not rebuild the binary
or independently prove source/binary equivalence. Submission-authored validation
files are not treated as independent score evidence.

## Original evaluation results

The initial `screening_evaluation.json` was read from
`authoring/runs/c03_resonance_compiler/screening/`. It is the LEGACY startup-charged
report, not the forthcoming fair merge. Its exact aggregate is
`mean_core=0.7618559498657015`, `worst_family=0.6495125524822437`.
The family means are U1 local 0.6495125524822437, U1 correlated
0.6597509935908489, and Z2 pseudogenerator 0.976304303524012.
Those depressed aggregates are NOT valid evidence of substantive hardness.

The two zero cases are precisely:

| Case | Legacy reported seconds | Runner evidence | Classification |
|---|---:|---|---|
| `screening_u1_local_00` | 60.21690966404276 | `runner_ok=false`, `case wall-time limit exceeded` | infrastructure timeout identified by main; fair rerun required |
| `screening_u1_correlated_02` | 73.67060168000171 | `runner_ok=false`, `case wall-time limit exceeded` | infrastructure timeout identified by main; fair rerun required |

Their zero algebra values and the messages `certificate must be a list`,
missing `analog`, and missing `digital` arise from the evaluator scoring an
empty fallback after the timeout. They are NOT observed malformed certificates
returned by the solver. The legacy elapsed figures do not isolate startup,
worker execution, and termination overhead, particularly the 73.67-second case.

All seven returned answers have `sector_f1=transfer_f1=algebra=1`,
`runner_ok=true`, no runner error, and an empty scoring-error list:

| Case | Case score | Raw analog / frozen analog reference | Raw digital / frozen digital reference | Reported solve seconds |
|---|---:|---:|---:|---:|
| `screening_u1_local_01` | 0.9813297923928225 | 0.8529315104166668 / 0.5227075520833333 | 0.9844442925347221 / 0.9844442925347221 | 52.08059669402428 |
| `screening_u1_local_02` | 0.9672078650539087 | 0.8795225260416667 / 0.8795225260416667 | 0.9709728624131946 / 0.9580865559895835 | 52.07652007503202 |
| `screening_u1_correlated_00` | 0.9897160485287654 | 0.6212189964157706 / 0.5033144265232974 | 0.4453163754480286 / 0.33534413829151727 | 52.072937032033224 |
| `screening_u1_correlated_01` | 0.9895369322437811 | 0.5862707659115427 / 0.44006634304207115 | 0.4481743078029483 / 0.3674248247033441 | 52.11890680901706 |
| `screening_z2_pseudogenerator_00` | 0.9797734323098065 | 0.5338391203703704 / 0.4493483796296297 | 0.5374322916666666 / 0.5177625385802468 | 52.071976503997575 |
| `screening_z2_pseudogenerator_01` | 0.9758956886341433 | 0.5165086805555555 / 0.4987725694444445 | 0.5270885416666662 / 0.4666579861111111 | 52.125306674977764 |
| `screening_z2_pseudogenerator_02` | 0.9732437896280859 | 0.5058255208333333 / 0.4955824652777778 | 0.5268658854166662 / 0.4878459201388884 | 52.078084489970934 |

Thus all 14 observed control objectives meet or exceed their strong reference:
12 exceed it, two equal it. There is no demonstrated algebra failure, no
sub-reference optimization result, and no demonstrated solver-side runtime or
clerical failure among these seven cases. The successful-case mean is
approximately 0.97952908, a diagnostic ONLY, not a replacement nine-case score.
Observed successful RSS is 33,360–36,476 KiB. Main owns rerunning the same two
cases and transparently merging their replacement results; this audit does not
impute scores for them. The legacy archive is now
`screening_pre_startup_grace.json`, SHA-256
`2ec81171a98c8dd2b8bb7f0c4cd3d553e3ab3a794a68f1d655065a7e5a255e60`.

### Corrected screening: all nine independently pass

Main reran ONLY those two cases with the unchanged submission under the new
startup-grace/strict-worker timing, and merged them with the seven original
successful results. The corrected `screening_evaluation.json` has SHA-256
`1f06b905745aa8f8c634616f3b5ec9dd6e2b61d59cd1af3921cf6347c59c013f`.
Its `timing_audit` retains the original filename, both original and corrected
case records, the 30-second namespace grace, the 60-second worker budget, and
the unchanged submission hash map. This is transparent replacement, not
discarding unfavorable valid results or awarding extra solving time.

| Metric | Corrected value |
|---|---:|
| Mean core | 0.9795690669861015 |
| Worst-family mean | 0.9716400624094256 |
| U1 local mean | 0.9716400624094256 |
| U1 correlated mean | 0.9907628350248667 |
| Z2 pseudogenerator mean | 0.976304303524012 |
| Algebra, sector F1, transfer F1 | 1.0 each |
| Analog component mean | 0.9731636506643784 |
| Digital component mean | 0.9660087205485299 |

| Retried case | Corrected case score | Worker seconds | CPU seconds | Outer wall seconds |
|---|---:|---:|---:|---:|
| `screening_u1_local_00` | 0.9663825297815459 | 52.06018126296112 | 52.120512000000005 | 54.631576023995876 |
| `screening_u1_correlated_02` | 0.9930355243020538 | 52.10931648500264 | 52.110031000000006 | 52.43606124003418 |

Both have perfect certificates, valid controls, and no runner/scoring errors.
The local case matches both reference raw qualities, 0.7989505208333334 analog
and 0.9683062065972222 digital. The correlated L=128 case achieves
0.5957768338727076 analog versus reference 0.45264104638619207, and
0.43856565758719857 digital versus reference 0.30374112279755494. Its robust
minimum margins are 0.39349999999999996 and 0.36993055555555515 respectively.
Across corrected screening, all 18 control objectives meet their strong anchors:
14 improve and four equal them. All nine case scores are at least the frozen
reference's 0.9663825298. The former failures are resolved as infrastructure,
not solver algebra, optimization, missing API fields, or an over-budget worker.

### Challenge timing check

The original challenge log was already present with modification time
August 27, 2026, 18:44 PDT. The helper and evaluator fairness-patch modification
times are August 27, 2026, 18:47:46.059818884 PDT. Main's
`authoring/evaluate_finished.py` opens that log immediately before launching the
split evaluator. Therefore the original challenge likely started with legacy
imported code; editing the files does not update an already-running Python
module. This is a timing inference, not a direct observation of its module
objects. The sandbox process namespace does not expose the host evaluator PID.
Any original challenge timeout would need the same fairness check, not a
substantive failure label. The completed report has NO timeout or other failure,
so its successful results require no timing correction or duplicate run.

### Original challenge: all twelve independently pass

Source: `authoring/runs/c03_resonance_compiler/screening/challenge_evaluation.json`.
This is main's original challenge run, not a rerun requested by this auditor.
Report SHA-256:
`9838f2bdeeea5a47ce58c479cab31baa6cb6f8cfa3ad6193e2c9035b9128dc5b`.

| Metric | Value |
|---|---:|
| Mean core | 0.9830295800047967 |
| Worst-family mean | 0.9769645061177112 |
| U1 local mean | 0.981946426542069 |
| U1 correlated mean | 0.9901778073546096 |
| Z2 pseudogenerator mean | 0.9769645061177112 |
| Algebra, sector F1, transfer F1 | 1.0 each |
| Analog component mean | 0.9799248980756993 |
| Digital component mean | 0.9695420729604254 |

| Challenge case | Case score |
|---|---:|
| `challenge_u1_local_03` | 0.9817667086098455 |
| `challenge_u1_local_04` | 0.9671035223521267 |
| `challenge_u1_local_05` | 0.9822399568135011 |
| `challenge_u1_local_06` | 0.9966755183928029 |
| `challenge_u1_correlated_03` | 0.9931713886721627 |
| `challenge_u1_correlated_04` | 0.989440959873436 |
| `challenge_u1_correlated_05` | 0.9899146634445853 |
| `challenge_u1_correlated_06` | 0.9881842174282544 |
| `challenge_z2_pseudogenerator_03` | 0.9774100821933392 |
| `challenge_z2_pseudogenerator_04` | 0.9772871534015787 |
| `challenge_z2_pseudogenerator_05` | 0.9766550983002009 |
| `challenge_z2_pseudogenerator_06` | 0.976505690575726 |

All twelve have `runner_ok=true`, null runner errors, empty scoring-error lists,
and perfect certificates. Reported worker seconds range from
52.07046671403805 to 52.1197119159624; RSS ranges from 32,668 to 42,664 KiB.
No analog or digital raw objective is below its frozen strong reference:
22 of 24 improve, two equal. Both ties are U1 local objectives: digital in
`challenge_u1_local_03`, analog in `challenge_u1_local_04`.

At the largest physical size L=160, the source-correlated U1 family achieves
analog quality 0.5995885371805914 versus reference 0.4176582328452484, and digital
quality 0.4443057798593165 versus reference 0.393867514235812. Its minimum robust
margins are 0.4374444444444444 analog and 0.3766388888888887 digital. This directly
rules out interpreting success as only a small-L or elementary-channel result.

Together, corrected screening plus original challenge give 21/21 successful
cases, 21/21 perfect certificates, and 42/42 control objectives at least as good
as the existing strong reference (36 strict improvements, six ties). No tested
family supplies an algebraic, optimization, or solver-runtime counterregion.

### Timing fairness hold

Main reports measured bwrap startup variability of 2–17 seconds and identifies
that the legacy helper charges namespace startup against the same 60-second
wall limit as solving. These startup measurements are supplied by main, not
re-measured in this audit. The submission intentionally budgets approximately
52 seconds after entry to `solve`; startup greater than roughly eight seconds
can therefore exhaust the legacy outer limit even when solving itself is
within contract. Module import and serialization consume some slack as well.

Main reports the fairness patch landed: optional 30-second namespace-startup
grace with STRICT 60-second worker wall and CPU alarms, not extra solving time.
Existing evaluator processes
may retain the old helper. Preserve legacy reports as evidence, but do not
interpret a startup-contaminated zero case score or empty-certificate default
as an algebra or optimization failure. A legacy timeout is unresolved runtime /
infrastructure attribution until main's isolated worker-timed rerun or explicit
startup/worker telemetry resolves it. This auditor neither reruns cases nor
changes the helper. Successful legacy cases remain useful correctness evidence;
timeout-contaminated aggregate scores do not establish substantive hardness.

## Core completeness: static findings

The submission implements the requested core, rather than returning a schedule
without a physical certificate or recognizing a handful of channel names.

* `attempt/solver.py:31`: `_paths` decomposes operator matrices into bit-flip
  patterns and input-dependent amplitudes. Terms producing the same flip pattern
  are grouped; this is an exact way to retain coherent cancellations, since
  different flip patterns cannot reach the same output from a fixed input.
* `attempt/solver.py:57`: `_local_transfers` enumerates only the relevant local
  link bits. It checks every assigned adjacent U1 pair, determines target matter
  occupations, sums amplitudes before the 1e-12 reachability test, and emits
  distinct departures. It does not enumerate the full 2^(2L) Hilbert space.
* `attempt/solver.py:112`: U1 uses the additive staggered Gauss map. Lines 115–117
  separately compute Z2 G and W transfers; the code does not substitute the
  violated-generator set for the pseudogenerator penalty.
* `attempt/solver.py:129`: translation caching uses the relevant Z2 target
  signature and explicitly restores U1 anchor parity. Certificates retain signed
  sector/penalty pairs; only the optimization rows merge overall-sign equivalents.
* `attempt/solver.py:166` and `attempt/optimizer.cpp:293`: analog and circular
  digital margins include the specified coefficient uncertainty. Native digital
  distances are measured in units of pi, so its modulo-2 expression is the
  protocol's modulo-2pi expression, not a missing-pi error.
* `attempt/solver.py:253`: root `solve(case)` returns the required three output
  components. It budgets about 52 seconds including local compilation, reserving
  slack under the 60-second limit. The native path has a Python fallback on
  shared-library load failure (`attempt/solver.py:266`). There is no case-ID
  answer lookup or private-reference import in the inspected solver.

This is substantive implementation of both representations, coherent
reachability, bounded controls, and aliases. Static inspection alone does not
prove every output correct; the independent report components decide that.

## What compresses the task

I measured the following directly from the existing frozen screening/challenge
case/reference JSON, without invoking a solver or evaluator. A row's circular
span is L minus the largest gap between its support indices; it matches the
native optimizer's `width` construction (`attempt/optimizer.cpp:283`). There are
seven cases per family across the two original splits, with L=32–160.

| Family | Distinct penalty rows | Maximum row support | Maximum circular span | Individually sign-symmetric coefficient sites |
|---|---:|---:|---:|---|
| U1 local | 80–400 | 2 | 1 | all L sites, every case |
| U1 correlated | 155–774 | 4 | 3 | zero sites, every case |
| Z2 pseudogenerator | 96–480 | 2 | 2 | all L sites, every case |

Every case has only eight allowed digital phase ticks. The algebra can be
compiled generically, after which both representations and both schedules share
the same small-width factor optimization problem. Increasing L does not increase
these spans. This is the central compression risk, not a full-Hilbert shortcut.

The submission exploits that structure legitimately:

1. `attempt/solver.py:281` checks whether reflecting one coefficient's sign
   permutes the complete penalty-row set up to overall sign. Restricting that
   coefficient to nonnegative ticks then preserves both objectives exactly:
   caps/uncertainty are symmetric and all margins are absolute/circular distances.
   It is not an unsupported assumption that all coefficients may be positive.
2. `attempt/optimizer.cpp:55` uses a mean-margin/threshold-deficit utility and
   coordinate optimization. `attempt/optimizer.cpp:91` adds a finite-width
   dynamic program with rotating, fixed prefix values to close the ring.
3. The DP searches full or sampled local tick alphabets, includes current ticks,
   and combines periodic restarts, perturbations, and polishing
   (`attempt/optimizer.cpp:202`, `attempt/optimizer.cpp:226`). It is not a proof
   of global optimality: fixed boundary values, selected alphabets, sampled
   thresholds, and a wall deadline still leave optimization risk.
4. `attempt/optimizer.cpp:293` precomputes each physical row's analog or digital
   utility table. Thereafter the same optimizer handles every family/schedule.
   The Python controller allocates 43% of its budget to analog, 23% to screening
   all phases, and refines the three best digital candidates with the remainder
   (`attempt/solver.py:303`).

Thus the solver does genuinely different algebra, but the proposed optimization
axes are not independent algorithmic barriers after compilation. Native code is
a normal implementation choice under the root Python API, not a clerical exploit.

## Failure classification rubric

* Algebra: `sector_f1` or `transfer_f1` below one is independent evidence of a
  missing/spurious physical transfer. Distinguish a correct sector map with wrong
  W penalties from a wrong reachability/sector map.
* Optimization: valid controls with perfect algebra but lower raw analog or
  digital quality are synthesis losses. Compare raw qualities to frozen anchors,
  not only the smooth calibrated scores. A control score below 0.95 means below
  that feasible reference, not necessarily a zero local gap.
* Runtime/clerical: use `runner_ok`, `runner_error`, `errors`, and per-case
  `seconds`; the 1540-second authoring duration is not such a failure. Native
  loading is not instrumented in the evaluator report, so a successful report
  alone cannot prove which optimizer branch executed. Apply the timing fairness
  hold above before attributing ANY legacy timeout to the submission.
* Reference interpretation: the strong anchor has control score 0.95 and case
  score 0.9663825298 by construction. Exceeding it demonstrates improvement over
  a feasible precomputed reference, not global optimality. The perfect-certificate
  weak baseline is 0.1357208808 overall.

## Source-grounded checks and excluded extensions

Only existing physical cases with frozen strong references can support a
hardness claim in this bounded audit. The original cases below fail to furnish
a counterexample. Other source extensions are noted only to explain why they
are not admissible evidence here; none is proposed as a new counterregion.

Primary source checks use the inspected arXiv PDFs: *Gauge-Symmetry Protection
Using Single-Body Terms*, arXiv:2007.00668v2, Secs. III, IV B, V B; and
*Stabilizing lattice gauge theories through simplified local pseudogenerators*,
arXiv:2108.02203v2, Table I, Eqs. (5)–(7), Appendix A3. Equation numbers refer to
those versions, not necessarily journal pagination. The pilot remains an
author-reimplementation of a restricted engineering objective, not an official
bug-fix or a test of all the papers' dynamical claims.

### 1. U1 correlated local cancellation: meaningful but already present

The single-body paper's Sec. V B explicitly supplies
`sigma^-_(j-1) tau^+_(j,j+1) sigma^-_(j+2) + H.c.`. Using THIS protocol's Gauss
convention gives a reachable row proportional to `(1,1,-1,-1)` on consecutive
sites j-1 through j+2. An input with all link bits zero and all matter occupied
is a physical witness. Every exactly period-two coefficient sequence cancels
that row. This derivation uses physical operators, not an arbitrary integer
constraint. However, the frozen `four_site_crosstalk` already contains it at
every anchor, and the submission neither assumes period two nor omits the row.
It is a useful diagnostic for any correlated-family optimization shortfall,
not a newly demonstrated counterexample to this submission.

### 2. Z2 penalty signs: already handled; regrouping is not a validated region

Table I / Eq. (5) distinguish W from G outside target: for target +1,
G=-1 can accompany W=-1 or W=3. Under the protocol these give the SAME sector
departure -2 but penalty departures -2 and +2. The submission explicitly handles
both. The source's local error Eq. (6) also motivates coherently regrouping the
two density contributions on one link and varying assisted-hopping amplitudes.
The inspected flip-pattern compiler already sums precisely those amplitudes.
No strong precomputed reference exists here for a new regrouped cluster, so this
is not promoted to a counterregion, an established algebraic weakness, or a
ratchet proposal.

### 3. Digital alias competition

The single-body paper's Sec. IV B / Eq. (20) establishes that stronger digital
protection need not be better because rotations wrap. In the pilot's restricted
objective, `phi*(r dot c)=2*pi*k` is an exact alias even with nonzero analog gap.
Clock windows and overlapping physical error rows can create competing aliases.
Here the submission already uses
the exact circular metric for every allowed phase. Merely adding more clocks
or targeting its phase-budget split would be a compute-budget trap, not evidence
of missing Floquet algebra. No new clock cluster is constructed or tested, and
none is proposed without an existing strong, physically validated reference.

### 4. Genuine source extensions that are NOT current-contract failures

The pseudogenerator paper's Eq. (7) and Appendix A3 study nonlocal product errors
against compliant versus short-period noncompliant protection. Those distinguish
all-sector protection from local protection, but importing them at L=32–160
would change the local-support/output-size problem. Likewise, full interacting
Floquet dynamics and higher-order/long-time leakage are expressly outside c03's
contract. They must not be scored as omissions in this solver. No c04 long-time
probe is duplicated here.

Raising the support span solely beyond the native DP's explicit width-six limit
would also be a post-hoc implementation trap. Any wider-support proposal needs
an independently justified physical noise model and feasible bounded reference;
an arbitrary signed-row puzzle is not an acceptable replacement.

## Disposition

**Recommend discard as a hardness candidate, not a ratchet.** Corrected screening
is 0.9795690669861015 / 0.9716400624094256 mean/worst-family; original challenge
is 0.9830295800047967 / 0.9769645061177112. All 21 cases have perfect certificates
and both feasible control anchors met or exceeded. The two apparent screening
failures disappeared in unchanged-submission fair retries. The invalid legacy
0.761856 aggregate must not be used to retain the pilot.

There is currently NO demonstrated natural counterregion with an existing strong
reference that defeats this solver. The source-grounded four-site correlation,
G-versus-W distinction, and digital aliases already occur in the original task
and are handled. No unsupported wider/nonlocal or clock-budget cluster is
recommended. The general local compiler plus one bounded-width search backend
has solved the tested core across both representations, both schedules, and
L up to 160. That is legitimate scientific compression, not a clerical bypass.
Do not add artificial masks, code-targeted width cliffs, or timing traps to
reverse this result. The transparent fair screening merge and the successful
original challenge complete the audit. No ratchet is built.
