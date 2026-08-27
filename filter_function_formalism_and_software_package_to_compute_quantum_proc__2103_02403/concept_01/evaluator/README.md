# Private evaluator

Run from any directory with the evaluator's trusted Python environment (Python
3.10+, NumPy, SciPy, Linux `/proc`, and `/usr/bin/bwrap`):

```sh
python evaluate.py OUTPUT_DIR --result RESULT_JSON
python evaluate.py TRUSTED_REFERENCE_OUTPUT --result REFERENCE_RESULT_JSON --unsandboxed --skip-evidence
```

Only `evaluate.py` and this document belong to this implementation. Main owns
the reference implementation and private assets. The evaluator never imports
participant or solution modules, and does not use public labels or a source
implementation as an oracle.

## Private inputs

Paths are relative to the `concept_01` root:

- `participant/v_01/input/manifest.json` and `input/cases/` supply public inputs.
- `evaluator/hidden/manifest.json` is a nonempty list of
  `{"case_id": "...", "family": "...", "file": "case.json"}` entries.
- `evaluator/hidden/cases/` contains the JSONs and their relative NPZ assets.
- `evaluator/hidden/targets/{case_id}.npz` contains complex `channel` and `k2`.
- `evaluator/hidden/resources.json` maps each case ID to
  `{"seconds": ..., "peak_rss_mb": ...}` from a strong reference run.

Missing or malformed evaluator inputs produce `status: infrastructure_error`,
`score: null`, and exit code 2. They are not submission failures. A completed
evaluation exits 0, including when candidate invocations fail and earn zero.
Results are written atomically; JSON includes explicit errors, bounded child
stdout/stderr, per-case/per-family measurements, and total evaluator runtime.

## Execution and resource boundaries

Each invocation runs `bash OUTPUT_DIR/run.sh CASE DEST --mode MODE` from its
fresh destination directory. Only the case JSON and its referenced asset are
copied to a private temporary directory; the JSON asset path is rewritten to
remain valid. Targets, budgets, other cases, source code, and evaluator files
are not mounted in the child.

By default bubblewrap makes `/usr`, `/bin`, `/lib`, and `/lib64` read-only,
creates isolated proc/dev and private `/tmp`, mounts the candidate output at
`/candidate` read-only, the copied case at `/case` read-only, and only the
destination at `/runout` writable. User, mount, PID, IPC, network, UTS and
cgroup namespaces are isolated; capabilities are dropped. The child receives
a fresh environment, empty `PYTHONPATH`, `PYTHONNOUSERSITE=1`, and one-thread
BLAS settings. Its `run.sh` must enable its own vendored dependencies.

There is no automatic unsandboxed fallback. Missing bubblewrap or failures
before the trusted launcher starts the candidate are infrastructure errors.
The launch marker is captured from a pipe before executing candidate code,
so a candidate's own stderr cannot masquerade as a bubblewrap setup failure.
`--unsandboxed` is **only for a trusted reference**: it removes filesystem and
network isolation, not resource limits. Do not use it for submissions.

Each invocation has a 120-second wall timeout, a 2-GiB per-process address-space
limit, and sampled aggregate process-tree RSS enforcement at 2 GiB. The latter
is sampled, not a kernel aggregate-memory cgroup quota; very short spikes and
shared-page double counting are possible. `wait4` supplies CPU usage and peak
RSS; reported memory is the larger of that peak and the sampled tree peak.
Limits also disable core dumps and cap individual output files at 64 MiB.
Child logs are bounded to 128 KiB per stream. Timeouts, abnormal exits, invalid
arrays, and grossly nonphysical channels get zero accuracy and efficiency.

## Accuracy and efficiency

The evaluator independently forms the ideal propagator by chronological
prefix multiplication of `expm(-1j * H[s] * dt[s])`, then uses
`kron(U.conj(), U)` for the column-major ideal superoperator. Comparisons use
the full complex arrays, never just scalar infidelity:

```text
channel_rel = ||channel - target_channel||F / max(||target_channel - ideal||F, 1e-8)
response_rel = ||k2 - target_k2||F / max(||target_k2||F, 1e-8)
accuracy = 0.6 / (1 + (channel_rel / 0.05)^2)
         + 0.4 / (1 + (response_rel / 0.03)^2)
core = 0.7 * mean(family_accuracy) + 0.3 * min(family_accuracy)
time_efficiency = min(1, sqrt((reference_seconds + 0.5) / (actual_wall_seconds + 0.5)))
memory_efficiency = min(1, sqrt((reference_rss_mb + 64) / (actual_rss_mb + 64)))
efficiency = mean(0.7 * time_efficiency + 0.3 * memory_efficiency)
score = 0.85 * core + 0.10 * efficiency + 0.05 * evidence
```

Family accuracy is the average over every hidden case in that family. The
trace-preservation defect is `||vec(I)^T channel - vec(I)^T||F`. Hermiticity
preservation is checked by `||J - J.conj().T||F` for the trace-one normalized
Choi matrix; either defect above `1e-4` invalidates the output. Choi minimum
eigenvalues and unitality are diagnostic, not additional arbitrary penalties.
Nonfinite values, invalid shapes, unsafe paths, and malformed/oversized NPZs
are rejected. NPZ headers are bounded and validated before NumPy allocation;
pickle/object arrays are never allowed.

The scalar evidence conventions are independently implemented: infidelity is
`1 - real(trace(ideal.conj().T @ channel))/d**2`; leakage is loss from the
specified computational subspace starting in its maximally mixed state;
coherent size is half the Frobenius norm of the anti-Hermitian part of the
error channel; `k2_norm` is the full response Frobenius norm.

## Evidence audit

Evidence is a continuous fraction in `[0, 1]`, with denominator **always 1**.
Eight equally weighted groups cover tables, public-case coverage, ablations,
scaling, claims, reruns, figures, and report traceability. Checks within each
group are averaged. Missing/invalid artifacts receive failed checks, not an
all-or-nothing scientific judgment. `--skip-evidence` assigns evidence 1 and
explicitly marks it skipped; this operator-controlled option is reserved for
reference calibration, not submission evaluation.

Every row of `results.csv`, `ablation.csv`, and `scaling.csv` is audited, not
just the rerun sample. The standard schema is:

```text
row_id,case_id,mode,infidelity,leakage,coherent_size,k2_norm,seconds,peak_rss_mb,artifact
```

`artifact` is a relative process-output **directory**, containing
`process.npz` and `metrics.json`. Scalar CSV values and metrics.json observables
must match independent recomputation with `rtol=1e-6, atol=1e-8`. Resources must
be finite/nonnegative (RSS positive) and agree between CSV and metrics.json.
Historical resources cannot be recovered from an NPZ; sampled reruns supply
independent wall/RSS measurements, including startup overhead. Both are saved
for inspection rather than demanding identical timings on different runs.
All artifact and source paths reject absolute paths, `..`, and escaping
symlinks. CSVs are limited to 2,000 rows and text artifacts to 8 MiB.

`results.csv` must cover every public case in selected and baseline modes.
`scaling.csv` additionally supplies `segments,dimension` matching input arrays
and covers at least three distinct `(segments, dimension)` sizes. Scaling
may provide complete rows or refer to results rows using
`row_id,segments,dimension`; `source_row`/`result_row` and optional
`source_table` also permit a separate scaling row ID. Inherited resources and
all scalar metrics are still audited against the actual artifact.

At least two non-white cases need selected/refined/no_memory ablation rows.
Refinement diagnostics must identify different numerical settings or methods;
changing only mode labels or random seeds does not qualify. Equal or tiny
selected/refined channel differences are not penalized. At least one
multi-block memory case must have a no-memory channel or response difference
above floating-point roundoff, with no imposed minimum scientific effect size.

Five fresh invocations audit selected `driven_static`, selected `white_gate`,
refined and no_memory `driven_static`, and baseline `calibration_static` (or
the smallest public case if that ID is absent). They compare both channel and
response with **all** saved artifacts for the sampled case/mode, using
relative Frobenius tolerance `1e-5` and a `1e-8` denominator floor. The driven
refinement diagnostics are checked again from actual reruns. Stochastic
mismatches produce explicit reproducibility warnings and failed comparisons,
not an exemption. A logged `seed`, `rng_seed`, or `random_seed` in diagnostics
(or top-level `seed`) is replayed via `EVALUATOR_SEED`, `SEED`, and `RANDOM_SEED`;
the candidate must consume one of these or deterministically use its logged
seed. There is no undocumented `--seed` command-line argument. Inconsistent
seeds are flagged; at most one seed is replayed per sampled case/mode.

Claims must be a list with
`claim_id,text,table,rows,metric,operation,value`. Supported operations are
`value` (one row), `difference` (row 0 minus row 1), and `ratio` (row 0 divided
by row 1, with nonzero denominator). Each claimed value is checked against
its verified source rows with the same numeric tolerances. At least one
same-case selected/no_memory memory claim and one refinement/validity claim
are required. Semantic scientific justification remains a manual task.

Figures require valid PNG structure/checksums and verified table-row links,
not aesthetics. A canonical `figures/sources.json` is:

```json
{
  "primary_result.png": [{"table": "results.csv", "rows": ["selected_case", "baseline_case"]}],
  "robustness_or_scaling.png": [{"table": "scaling.csv", "rows": ["small", "medium", "large"]}]
}
```

A single source object instead of a list, a `figures` wrapper, or a list of
objects with `file`/`figure`/`image`/`path` and `sources` are also accepted.
Reports are checked for readable content and evidence links. Scientific
reasoning, chronology, numerical-method truthfulness, and figure meaning
require main's manual inspection. Suspicious universal Gaussian/exactness
claims are flagged for that inspection, **without an automatic penalty**.

The usual complete run executes six hidden cases plus five evidence reruns,
sequentially on one BLAS thread, with no unnecessary convergence sweep or
source-based reference solve. Total runtime depends on the submission; there
is no misleading five-minute global cutoff that truncates required cases.
Main should run end-to-end, sandbox-failure, resource-limit, numerical, and
adversarial-artifact tests after creating the private targets and budgets.
