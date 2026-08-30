# Final concept-two ratchet: partial-information mixed-OPE completion

The source is the frozen generation-two champion (`improve.py`, `seed.py`,
`continuous.py`, `pipeline.py`, and its collection logic), not the weaker
generation-one replay. Source files and generation-one/two snapshots are retained.
The original generation-two answer is independently rescored. Clean-state replay
controls on archived generation-two data are reported separately, without using
the archived answers as seeds.

## Actual numerical experiment

The base experiment tests 32 new valid cases, eight per original family, on an
eight-point grid of probe counts 12–26, atom caps 10–18, and derivative orders
0–2. Candidate count remains 96. In every case `3*M >= 2*K-1`, so the source's
fixed-support Levenberg–Marquardt fits have enough residual components. Its
continuous-energy fit already uses bounded TRF and permits more parameters than
observations; no solver-method workaround is necessary. The leading-radial and
Legendre model, shared coefficient, coefficient cap, 3% trace slack, and original
2e-8/2e-10 certificate tolerances remain unchanged.

Scalar-only partial-information cases prove easier in screening, and are not
declared hard. The targeted follow-up combines angular aliasing with mixed OPE
sign cancellation using eight fresh cases. This changes geometry/information,
not numeric precision or coefficient magnitudes. Every candidate is checked
against its planted vectors and independently reconstructed 80-digit kernels
before screening. Any valid completion is accepted, regardless of support.

Screening is 60 seconds per case; eligible normal-exit residual failures receive
300-second confirmations. Exceptions, missing continuous refinement, and outer
process timeouts are excluded from selection. The source's own bounded search
can exhaust its stage allowance; that is distinguished from a crashed or killed
program. Exact inputs, hashes, outputs, stderr, stages, and independent residuals
remain private. Results report all solved candidates as well as failures.

## Faithful cold-start baseline

The numerical bodies of `seed.py` and `continuous.py` are unchanged. In
`improve.py` only the old hardcoded input path is replaced by an injected path.
The generic orchestration supplies a fresh scratch root and input file, a short
predecessor numerical seed, then the champion's whitened seeds, discrete
improvement, continuous energy fitting, snapping to actual candidate dimensions,
and any remaining final improvement. No stored answers, planted support, old case
IDs, or hidden candidate masks are available. Continuous whitening and spin
matching use the original public metadata/current-iterate logic; its initializer
considers the entire supplied candidate dictionary. The historical collection
step is replaced by selecting the best freshly computed case from scratch.

The wrapper has a finite wall allowance; early unused time reaches the continuous
stage. Alarm exceptions bypass numerical exception handlers. All state is beneath
the requested output directory, so participant assets and inputs may be read-only.
`adaptation.patch` distinguishes orchestration/path adaptation from numerical
code. The shared Landlock/seccomp sandbox is unchanged and has no unsafe fallback.

## Interpretation and privacy

The final selection requires two confirmed failures per retained scientific
family, with unchanged checker semantics, 80-digit planted feasibility, independent
baseline residual checks, and opaque public IDs. Source IDs/seeds, generators,
witnesses, mappings, and evidence are private. Public material contains only the
task, schema, actual data, checker and runnable baseline.

This is an empirical rank-one completion/partial-information stress test, not a
proof of intrinsic hardness, uniqueness, or an input-only achievability claim.
Nonidentifiability is allowed because any certificate meeting the same constraints
earns credit. The original scalar-only hypothesis is explicitly not retained when
it is solved. Main owns the generation-three fresh attempt and final status; this
sidecar launches no agents and does not create a fourth concept or another ratchet.
