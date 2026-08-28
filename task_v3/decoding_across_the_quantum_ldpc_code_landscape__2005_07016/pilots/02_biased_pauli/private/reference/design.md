# Pilot02 design, recorded before implementation

## Scope and source boundary

All authored files and generated outputs stay within `pilots/02_biased_pauli`.
The repository, task, pilots, and pilot ancestors (including resolved `/home`
ancestors) were checked for `AGENTS.md`; none applied when this design was
recorded. No participant run, agent, or pilot launch is authorized here.
The supplied assets resolve to `../../research/{sources,vendor}` relative to
this pilot, rather than a root-level `output/research` on this mount.

The capability donor is the official `quantumgizmos/bp_osd` implementation,
specifically `bposd.css_decode_sim._channel_update`, its two-stage BP+OSD
schedule, and the official `quantumgizmos/bias_tailored_qldpc` matrix files
for the [[416,18]] and [[882,24]] lifted products. The latter repository
accompanies arXiv:2202.01702. Its sector-two Hadamard construction is extended
only by coordinate changes (known local Clifford frames and permutations),
not by an invented stronger decoder. Original BP+OSD provenance is
arXiv:2005.07016. Exact source/package hashes will be recorded at build time.

## Independent bottlenecks

1. **Symplectic code/frame transfer.** Inputs describe a non-CSS physical
   stabilizer in a per-qubit Clifford frame and a permuted coordinate system.
   A capable solution must consistently transport generators, errors, joint
   Pauli probabilities, syndromes, and corrections. Swapping marginal rates
   without transforming the joint distribution is not sufficient. Instances
   include the actual sector-two Hadamard and all six binary one-qubit
   symplectic maps. No row scrambling or artificial secret transformation.
2. **Correlated posterior and logical degeneracy.** X and Z components on a
   qubit are correlated through a four-outcome Pauli channel. Independent
   marginals discard the conditional information used by the official
   channel-update implementation. Sparse BP with ordered-statistics recovery
   must work at n=416 and n=882, not by exhaustive tiny-code enumeration.
   Success is equality of logical cosets, never equality to a particular
   sampled error or reference correction. Same-syndrome logical mistakes
   receive no success credit; stabilizer-equivalent answers receive full
   credit. The official reference is not asserted to be optimal or an exact
   degeneracy-aware posterior enumerator.

## Anti-compression test

The public prestate is an independent physical-X/Z-marginal, reliability-
ordered linear-syndrome solve with no correlation update, logical labels, or
hidden examples. Following the fair-prestate clarification, the participant
also receives the original 2020 native BP+OSD snapshot supplied in pilot01.
The runnable baseline remains intentionally weak, but implementing binary
BP+OSD from scratch is explicitly not the task gap. The later conditional
channel update and frame-transfer adapter remain private.

Before acceptance compare this prestate, the unmodified source-backed strong
adapter, a frame-correct independent BP+OSD ablation, and a frame-incorrect
ablation. The first tests the overall capability gap; the latter two isolate
the independent bottlenecks. Record consistency and full-block logical
success, across both genuine matrix sizes and bias/correlation shifts.
Reject claims of hardness supported only by baseline syndrome invalidity,
toy block lengths, arbitrary random parity checks, or a tiny generic solver.
If correlation ablation has no measurable cost, change the declared channel
regimes using a separate calibration stream, never cherry-pick scored shots.
No shot rejection based on decoder success is allowed.

## Evaluation and secrecy

Pilot and challenge streams use disjoint deterministic private seeds.
Holdout has an unallocated fresh seed, with both seed selection and case
generation deferred until a challenge failure region has been identified.
Generation requires an explicit new seed and profile file, never an inspected
pilot/challenge/calibration seed, without changing the participant API.
Public examples are tiny structural smoke batches on the real matrices, not
quality tests, and contain no error/logical labels or reference outputs.

Each case is a batch of independent code-capacity Pauli errors with exact
syndromes, known per-qubit joint probabilities, and fixed code/frame metadata.
Private data store complete logical signatures and valid official corrections
before any submission is run. Frozen per-family weak and strong anchors define
an affine score `(success - weak)/(strong - weak)`. Do not clip: a solver can
score below zero or above one, so improvement does not saturate. Report the
mean and minimum family score as well as all raw successes and runtimes.
Validate all strong corrections against physical syndromes, independently
verify complete logical tests, and require >0.9 relative reference quality.

Only `participant/` is released to a participant. `private/`, `attempt/`,
source trees, private dependencies, evaluation seeds, calibration, answers,
and quality reports must remain inaccessible in the participant sandbox.
Running an untrusted submission is a main-orchestrator responsibility: a
Python subprocess by itself is not a security boundary. The evaluator must
support an external isolation launcher; trusted-reference checks may use the
direct subprocess mode explicitly. No LSD, analog evidence, or circuit-level
decoding is included.
