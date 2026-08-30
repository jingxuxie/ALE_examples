# Builder audit: concept_1 only

## Scope and freeze

Mode A: improve joint logical decoding beyond PyMatching 2.4.0's actual two-pass
correlated matching. No fresh participant has been launched. No other concept
has been edited. The participant receives only `participant/` and its separate
writable output directory, with no web access or hidden builder artifacts.

Scientific targets were frozen at 2026-08-28T16:14:45.680987+00:00, before any
fresh participant. Pooled failures must decrease by at least 25%; independent
holdout failures by at least 20%; every noise family must have at most 1.05 times
baseline failures; the paired 95% absolute-improvement interval must exclude
zero. CPU budget is 180 seconds; wall watchdog 900 seconds; address space 6 GiB.
The fresh development budget remains one hour of wall time.

The original freeze digest was
`e2f540021e0eb7b8761e2cb6e80d0027342b8cdf04160cd685f576d37dbd2c1a`.
At main's request, private assets were moved from `hidden/` to
`evaluator/hidden/`; only artifact path strings changed in the freeze. The
current digest is
`cf748aa082b351abed346d2dc55ae6e1c4b7f270d3683fcc45784ad2cf408ebd`.
Neither sampled bits, baseline predictions, numerical targets, nor the frozen
public worker/model code changed. Launcher-only CPU-accounting corrections are
described below. Main should freeze the complete final evaluator tree at handoff.

## Sampling and scale

There are six public model specifications, grouped into three **noise families**
on toric-code geometries, not three unrelated code families. Distances are 7 and
9. The three-round temporal models include noisy intermediate readout and
same-site temporally correlated Y bursts. These are local phenomenological
Pauli-frame models, not gate-level circuit simulations or literal simultaneous
measurement of noncommuting observables.

Each elementary mechanism is independently Bernoulli sampled, with all components
of a correlated event firing together. Detector/observable labels are H/L parity,
not decoder output. There is no weight truncation, rejection sampling, balancing,
or selection based on baseline mistakes. Public calibration has 512 shots per
case; the builder pilot has 128; challenge and holdout each have 1,024. All use
independent secret 128-bit seeds. Only the first 32 pilot shots per case were
used for the bounded-time MAP diagnostic. Final scores never use pilot samples.

| Model | Detectors | Mechanisms | Hidden baseline failures / 2,048 |
| --- | ---: | ---: | ---: |
| biased_7 | 98 | 294 | 240 |
| biased_9 | 162 | 486 | 362 |
| crosstalk_7 | 98 | 490 | 316 |
| crosstalk_9 | 162 | 810 | 438 |
| memory_7 | 294 | 1,274 | 70 |
| memory_9 | 486 | 2,106 | 97 |

The 12,288-shot baseline has **1,523 failures**, or 12.3942%. Challenge contributes
755 and holdout 768. Family totals are 602, 754, and 167. The pooled target is
therefore at most 1,142 candidate failures, holdout at most 614, and family maxima
632, 791, and 175 respectively. The uncorrelated ablation has 2,472 failures,
so the supplied correlated baseline is substantially stronger than plain MWPM.
Public calibration has 389 baseline failures out of 3,072.

The detector-matrix nullity is already 198 for the smallest model and 1,622 for
the largest. All four logical-frame bits are independent modulo detector rows.
This is not a tiny syndrome table or a tractable exhaustive enumeration benchmark.

## Attainability evidence and limits

`attempts/private_map_pilot.json` records a privileged bounded-time physical-MAP
MILP diagnostic on 192 independent pilot shots. Baseline failures were 26 and
the diagnostic had 18 (30.8% fewer), but it **failed family nonregression**:
the temporal family worsened from 2 to 8. Biased-family failures went from 9 to 3
and crosstalk from 15 to 7. This demonstrates substantial non-Bayes headroom in
two families, not a certified logical maximum-likelihood bound.

The diagnostic consumed about 63.4 CPU seconds for just 192 shots; its time-limited
incumbents are not necessarily optimal. It is **not** a runtime-qualified passing
reference. Keeping baseline predictions on the temporal family would remove the
observed regression, but that is a post-hoc pilot observation, not an independent
validation. No full-suite passing implementation has been established. This
uncertainty is retained explicitly rather than claiming a feasible reference or
weakening the target after a fresh attempt. No perfect reference was awaited.

## Validation and isolation

`evaluator/test_evaluator.py` has nine scientific/schema tests: Stim independently
checks H/L parity including repeated targets across separators; all logical ranks
are checked; unconditional sampling moments and variable fault weights are
checked; seeds/split sizes are checked; baseline output and permutation invariance
are checked; paired statistics and malformed outputs are checked; runtime symlinks
are forbidden; and isolated attempt subdirectories are allowed while privileged
roots are rejected. Raw results are in `attempts/unit_tests.log`.

`evaluator/validate.py` runs the baseline, actual-path/environment/network/fork
isolation probes, a valid all-zero decoder, an invalid float-output decoder, and
a two-CPU-second burn decoder. Raw JSON reports and `validation_summary.json`
distinguish invalid submissions from valid submissions that miss the target.
All these are trusted builder probes, not fresh participant attempts.

Default bwrap PID-1 handling empirically undercounted a known CPU burn. The final
launcher uses **`--as-pid-1`** and trusted parent `wait4`. A parent-built seccomp
filter blocks all process/thread creation and cross-process memory access. This
prevents unaccounted descendants; it also requires native extensions to be
compiled during development, not launched as subprocesses during evaluation.
`*_pre_cpu_fix.json` reports are preserved only as historical diagnostic evidence
and must not be used for runtime claims. Consult the current `cpu_probe.json`.
The final isolated baseline uses 1.993842 CPU seconds; the two-second burn probe
uses 4.019546, an increment of 2.025704 CPU seconds. All five isolated probes
and all nine scientific/schema tests pass. The baseline is valid but correctly
fails the improvement gates (`core_score=0`, `worst_family_score=0`,
`runtime_score=resource_score=1`). These values are also recorded in `status.json`.

Nested network namespaces fail in the outer tool sandbox, so main must run the
trusted evaluator with `exec require_escalated`. The **inner isolation remains
mandatory** and there is no unsandboxed fallback. System files are read-only,
parent `/proc` and host task paths are absent, no network is available, and only
label-free NPZs enter the request mount. The parent never imports candidate code
and rejects pickle, malformed shapes/dtypes, and oversized output archives.

Dependencies occupy about 313 MiB of real files inside participant. The pinned
CPython-3.10 x86-64 Linux wheels include NumPy, SciPy, Matplotlib, NetworkX, Stim,
and PyMatching. System NumPy/SciPy were 1.21.5/1.8.0 and lacked required optional
imports; the local compatible stack avoids relying on `/home` or `/opt`. Only
runtime bindings/binaries are provided, not the upstream C++ decoder checkout.

Paired intervals are approximate normal/delta-method intervals; the discordant
binomial test is exact. They are not corrected for adaptive multiple queries.
Keep holdout feedback privileged and reserve it for final adjudication. The
5% family guard is a fixed paired-suite point-count gate, not a simultaneous
confidence guarantee. CPU and address space are process limits, not a cgroup
RSS quota. Retry infrastructure watchdog failures without changing the targets.
