# Construction and validation

Only `../participant/` is participant-visible. Keep this directory, `build.py`,
the upstream source tree, cached outputs, reports, and attempt results private.
The main harness supplies the dependency-only participant runtime. The evaluator
isolates submissions with bwrap by default; private files are not mounted.
If namespace creation is blocked by an outer sandbox, main must launch the
evaluator with the appropriate escalation. Isolation failures never trigger a
privileged fallback.

The absent capability is an independent-real-degree Fourier representation
plus complex, channel-aware spectral density transport. Gap B supplies the
representation/scaling sources; gap H motivates exact density/gradient checks
and realistic-volume execution. This is not a benchmark of merely calling an
FFT. Seven separate families are declared in the public contract.

Privileged numerics call the retained `bijx.fourier` implementations directly:
`FourierMeta`, `FourierData`, `fft_momenta`, `spectrum_asymmetry`, and
`bijx.bijections.fourier.SpectrumScaling` (which calls `complex_affine_apply`).
`reference/official.py` only adapts array axes and takes JAX derivatives;
it does not reproduce the packing or determinant algorithm. Channel axes are
temporarily leading batch axes for spatial-only `FourierData` conversion.
Transport uses the official explicit channel/space-dimensional interface.
No source modules are delivered to participants.

`challenge_pool/manifest.json` records module and upstream-test hashes, source
revision, runtime versions, all geometry families, archive hashes, and weak
errors. The authoritative checked-out source is used, not an assumed version
from installed packages. A fast `--source` copy must match those file hashes.

Regenerate all examples, challenges, official outputs and calibration, and
validate the official and weak CLIs with four pinned cores:

```
taskset -c 36-39 /tmp/ale_python/cpython-3.12.12-linux-x86_64-gnu/bin/python3.12 build.py
```

Use `--skip-cli-validation` only for data regeneration when intentionally
deferring CLI checks. The independent checks still run. They compare packing
to NumPy FFT plus literal index traversal, decode unrelated coordinates,
check diagnostics against all stored pairs, compare real dense determinants
and adjoints on tiny events, and check JVPs/parameter gradients with central
differences. These private tests are independent of the stored answer files.
The builder explicitly runs its trusted official/weak anchors without isolation.
Existing reference reports and precomputed outputs are preserved as privileged
numerical-validation evidence; they are not evidence of a sandbox smoke test.

```
python private/evaluator.py --submission participant/workspace --report attempt/report.json --pool challenge
python private/evaluator.py --submission private/reference --report private/strong_report.json --no-isolate
python -m private.reference.checks
```

Submit a directory containing `solve.py`; auxiliary participant-written modules
are allowed. `--isolate` is the default; `--no-isolate` is an explicit trusted
reference-only opt-out. Isolated execution always uses the public
`/task/input/runtime/bin/python3.12`, never `ALE_PYTHON` or a host fallback.
Bwrap uses `--die-with-parent --unshare-all --new-session --clearenv`, read-only
`/usr`, `/lib`, `/lib64`, fresh `/proc` and `/dev`, tmpfs `/tmp`, read-only public
`/task` and `/submission`, and only current-case I/O writable at `/work`.
The participant and submission directories are also mounted read-only at their
original absolute paths, including both `/home/...` and `/srv/home/...` when
they resolve to the same host directory. Only those exact directory roots are
mounted: their ancestors are empty sandbox directories, never host mounts.
Private-path rejection checks both aliases, so remapping cannot expose a
private pool, reference, or shared source tree through an alternate spelling.
`PATH` points to the public runtime and `/usr/bin`; `PYTHONPATH` contains
`/submission:/task/workspace`. The process environment and inherited descriptors
are restricted, and stdout/stderr logs remain outside `/work`. Output symlinks
and special files are rejected before host-side reading. Private directory
mounts are rejected. No private pool/reference/source tree is exposed.
The four-core/four-thread cap is preserved, respecting tighter outer affinity.
Only privileged reference mode uses `ALE_PYTHON`, then the public runtime, then
the installation under `/tmp/ale_python`, then its own interpreter.
Each case is a fresh CLI invocation. Runtime is measured externally, including
startup/I/O, and reported overall and per geometry; a 60-second cap prevents
unscalable dense alternatives. Accuracy, not JAX compilation speed, determines
the seven family scores. Invalid individual arrays receive error 1e6, so a
partially implemented submission still earns credit on independent components.

The weak anchor in `reference/weak/solve.py` is a plausible magnitude-only
rFFT shortcut: it packs storage rather than independent modes, discards phase,
uses twice every stored slot for density, mishandles shared channels, ignores
symmetry checks, and leaves momenta unfolded. Its errors calibrate the smooth
log-error score, rather than defining pass/fail thresholds. Exact official
outputs anchor score 0.95 and unclipped normalized skill 1.0; the weak solution
anchors 0.10 and skill 0.0. Reports retain raw errors to make both transparent.
