# Pilot02 private operations

Run commands from the pilot root. Only `participant/` is released to an
agent. `attempt/` must be empty before the main orchestrator starts its run.
No agent or pilot is launched by these authoring tools.

## Sources and fair prestate

- Official `quantumgizmos/bias_tailored_qldpc`, revision
  `51205f0c9a1ba2cb578edfc9afc6d8ec0604d6d9`: the actual text matrices
  `lifted_product_[[416,18,20]]_{hx,hz,lx,lz}.txt` and
  `lifted_product_[[882,24,24]]_{hx,hz,lx,lz}.txt`, not synthetic substitutes.
  Source accompanies arXiv:2202.01702; the distance in a filename is not an
  independently computed minimum distance guarantee.
- Official `quantumgizmos/bp_osd`, revision
  `8894ec654b24ae875c07e5a361dcae9a77d748ce`: unmodified
  `src/bposd/css_decode_sim.py`, copied under `upstream/` with licenses.
  The adapter calls its actual decoder setup and conditional channel-update
  methods, using the documented min-sum / OSD-CS(10) parameters, n/10 BP
  iterations, and 0.625 scaling. Decode the lower-mean canonical component
  first, choosing one of its two supported update directions. No truth or
  logical labels enter the decoder, and no custom strong search is added.
- The participant gets the original 2020 native BP+OSD snapshot supplied by
  pilot01 (`74f86d3...`), byte-for-byte with its original dependencies/license.
  Its scalar binary-channel interface is preexisting infrastructure. The
  later per-qubit conditional Pauli update and local-frame adapter are not
  released. `TASK.md` contains no paper mention.
- SHA-256 provenance, actual matrix ranks/support sizes, and package details
  are in `provenance.json`. Private dependencies resolve from the supplied
  shared `../../research/vendor`, or `PILOT02_VENDOR`; ordinary installed
  packages matching `requirements.txt` also work when no vendor is present.
  The supplied ldpc directory has a 2.4.1 distribution record but a 2.4.0
  module version banner; this discrepancy is recorded rather than hidden.

The only source adaptation is transporting the canonical CSS model, Pauli
channel, and corrections through specified symplectic frames/permutations.
No LSD, analog measurements, or circuit decoding is involved. Public files
contain full code checks plus two three-shot unlabelled structural examples.

## Scoring and isolation

```
python -B private/evaluator.py --submission participant/workspace \
  --report private/reference/evidence/submission_pilot.json --split pilot
python -B private/evaluator.py --submission /path/to/submission \
  --report private/reference/evidence/submission_challenge.json --split challenge
```

The main orchestrator runs this outside the outer sandbox with its approved
escalation. The evaluator uses a byte-for-byte copy of shared
`research/isolation.py::run_submission`, never imports submission code, and
mounts no private source, decoder packages, truth, answers, or seeds into the
participant sandbox. NumPy 1.21, SciPy 1.8, and g++ are the public toolchain;
no public-working Numba or specialized Python decoding package is assumed.
All launcher temporary files are rooted in this pilot's private `.runtime/`.

The per-case limit is 60 CPU seconds and 4096 MiB. Timeout is 180 wall seconds
to tolerate startup/mount jitter. CPU is `user_seconds + system_seconds` from
the helper; wall time is separate. Missing resource accounting is an invalid
run. No runtime bonus is mixed into quality.

The 512-shot pilot and 1024-shot challenge each have four equal-weight
code/channel families: both real sizes under sector-two Hadamard bias and
general local-Clifford correlated noise. Challenge shifts the per-axis weights
and total rate, with fresh frames, permutations, and errors. Every shot is
retained. Frozen weak/strong anchors are computed on each split before any
participant run. `mean_core` and `worst_family` use the unbounded affine
normalization described in `input/FORMAT.md`; zero is the actual weak
prestate and one is the source-backed strong decoder, not an oracle.

`replay_reference/` is an explicitly privileged **infrastructure replay** of
precomputed strong outputs, keyed by input-file digest. It is not a solver
for unseen cases, is never participant-visible, and must not be cited as
fresh decoding. To verify the isolated evaluator plumbing, the main may use
it as `--submission private/reference/replay_reference`. Actual decoder CPU
times and quality come from direct source-backed generation, not replay time.

## Evidence and independent accuracy audit

```
python -B private/reference/audit.py
python -B participant/workspace/smoke.py --input participant/input/examples/smoke_416.npz
```

`evidence/audit.json` and `evidence/{pilot,challenge}_{strong,weak}_report.json`
are the authoritative precomputed quality checks. The audit independently
uses explicit nonzero supports and Python-integer GF(2) rank, rather than
trusting the generator's sparse logical calculations. It verifies full
logical completeness, inverse-frame syndrome agreement, all sampled-error
syndromes/signatures, every reference correction, malformed output rejection,
stabilizer-equivalent answer invariance, and same-syndrome logical failure.
Sparse construction explicitly eliminates stored zeros. Source text is
validated as binary before dense serialization; numerical zero entries are
never treated as logical support.

`evidence/correlation_screening.json` is a separate parameter-calibration
stream, not a scored sample selection. Frozen manifests also include
frame-correct independent BP+OSD and omitted-output-frame ablations. Raw
full-block logical success and consistency are separate, so the weak
baseline cannot appear weak merely from invalid syndromes.

## Reproduction and fresh holdout

The committed pool is ready to use; do not rerun preparation over frozen
assets. `build.py --prepare` snapshots the supplied assets in a new clean
pilot; `--split pilot --shots 128` and `--split challenge --shots 256` produce
the present scored streams. Builds refuse existing split data, including
interrupted builds, to prevent silently replacing inspected instances.

**Holdout is not generated and has no allocated seed.** Only after the main
identifies a challenge failure region, write a private JSON list of profiles
with `name,n,frame,rate,weights` (the same schema as `build.py::PROFILES`),
choose a new secret integer seed not in `challenge_pool/seed_manifest.json`,
and run:

```
python -B private/reference/build.py --split holdout --shots 256 \
  --holdout-seed NEW_SECRET_INTEGER --profiles private/reference/holdout_profiles.json
python -B private/evaluator.py --submission /path/to/submission \
  --report private/reference/evidence/submission_holdout.json --split holdout
```

Do not reuse pilot, challenge, either calibration stream, or an inspected
holdout. Do not use holdout generation to change the initial four pilots.
