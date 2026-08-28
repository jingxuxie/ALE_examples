# Pilot03: real Wannier device transport

Status: READY AFTER REQUIRED SCORING AUDIT. All 12 official references are stored; current nonsaturating strong controls exceed 0.9 in every test/challenge family. Use `private/reference/post_audit_summary.json` for fresh grading, not the preserved legacy score reports. Confirmation is reserved. No scale reduction was made.

Launch freeze: the participant bundle is frozen for the initial pilot. Its file hashes and aggregate content digest are recorded in `pilots/03_device_transport/private/reference/participant_freeze.json`. The attempt placeholder was removed; the parent owns subsequent attempt contents. No further public changes are planned. The parent will generate fresh region-specific heldouts after the empirical ratchet, rather than relying only on the initially reserved confirmation cases.

## Required post-build scoring audit, before fresh grading

The user required this correction before any freshpilot grading: the original error cap and clipped-linear skill were saturating. Both caps are removed from `private/evaluator.py`. Each valid group now scores exactly `1 / (1 + 9 * error / max(baseline_error, 1e-8))`; its normalized Frobenius error is unbounded. Missing, nonfinite, or otherwise invalid output groups score zero explicitly. The dimensionless baseline floor is `1e-8`; the existing scientific normalization floors, group weights, family balancing, physical mission, shapes, cases, geometry, and resource limits are unchanged. Reports identify `post_audit_nonsaturating_v1` and record the actual baseline anchors.

Calibration inspection found **all anchors exactly 1.0**, representing dimensionless unit error for the historical baseline's missing transport fields. There is no `MAX_ERROR`, huge failure sentinel, or inflated denominator that makes finite wrong answers score near one. The existing calibration is retained unchanged. A separate executable weak control, `private/reference/weak_zero/solve.py`, reads only the input dimensions and emits finite, correctly shaped zeros for every transport field; it neither imports a transport solver nor reads answers. This measures an actual finite weak prediction instead of reporting only a missing-output failure.

| Post-audit control | Core score | Worst family | Maximum wall time | Maximum RSS |
| --- | --- | --- | --- | --- |
| Strong, test | 0.9999999999998178 | 0.9999999999996673 | 11.72 s | 217.51 MiB |
| Strong, challenge | 0.9999999999999191 | 0.9999999999998263 | 12.46 s | 213.10 MiB |
| Finite zero-transport, test | 0.1107846565821920 | 0.1052868918022583 | 0.524 s | 33.33 MiB |
| Finite zero-transport, challenge | 0.2778311242449396 | 0.1061923734465893 | 0.250 s | 35.02 MiB |

All 16 author-control executions exit successfully with valid finite fields under the unchanged **90 s / 1,024 MiB address-space** limits. The strong route remains official Kwant Green functions versus the stored official scattering reference. Higher weak scores on the InAs three-terminal and Si two-terminal challenge cases are retained honestly: several response components are near zero. No case selection, weight adjustment, or recalibration was used to force weak scores lower.

The new records are `private/reference/post_audit_strong_test.json`, `post_audit_strong_challenge.json`, `post_audit_weak_test.json`, `post_audit_weak_challenge.json`, and `post_audit_summary.json` (all in that reference directory). They contain per-case errors, component scores, runtime, RSS, and resource compliance. Regression sweeps through relative perturbations of `1e6` verify strictly decreasing positive scores beyond error 1, with no clipping; missing/nonfinite checks verify zero scores. The summary hash-checks the original reports/calibration, test/challenge manifests, and frozen participant bundle before and after validation. No active agent attempts/logs or confirmation candidate code were inspected or executed.

**Legacy preservation:** `baseline_report_test.json`, both original `control_report_*.json`, `validation_summary.json`, and `baseline_errors.json` are byte-for-byte unchanged and explicitly hash-listed as legacy in the new summary. Initial score tables and trace-only score diagnostics later in this note describe the old scorer, not current grading. The old `audit.py` command is disabled to prevent accidental overwriting of legacy reports; `post_audit.py` is its current replacement. Frozen public `SCHEMA.md` still contains the original scoring paragraph by instruction; this user-required private grading correction supersedes that paragraph without modifying the participant bundle.

Write scope is exclusively `pilots/03_device_transport/**` and this note. Shared source checkouts and vendors are read-only. No agents or participant pilots were launched.

## Concept and source separation

The public adapter retains bulk Fourier interpolation from TBmodels pre-supercell commit `ab24b723e4b35dd08d86aa098a5cadeacab96e83`. This is explicitly an adapted capability-level starting artifact, not an assertion that all historical Kwant interfaces were absent. No hidden transport modules are public.

The private exact reference uses installed official Kwant 1.5.0, tinyarray 1.2.5, and TBmodels 1.4.3. All installations are under `pilots/03_device_transport/private/reference/vendor`; the shared vendor/source trees were not changed. Kwant compiled successfully with the local Python 3.10 / NumPy 1.21.5 / SciPy 1.8.0 stack. MUMPS is unavailable, so Kwant uses its official SciPy sparse solver, not a new transport implementation.

Data are official InAs symmetrized and Si eight-orbital Wannier models. The builder records upstream file paths, commit, hashes, full hopping counts and dimensions. It expands the stored half-Hamiltonian once; there is no hopping cutoff, synthetic hopping matrix, or fitted toy transport model. The physical task is an ideal finite crystal cut with real onsite gates; surface passivation and experimental device fidelity are not claimed.

## Independent bottlenecks and anti-compression decision

1. Construct finite real-space device couplings and principal-layer interfaces from full long-range Wannier hoppings, oblique crystal coordinates, and non-rectangular three-terminal geometries.
2. Compute the retarded, current-normalized lead solution with exactly rank-deficient inter-layer hopping. Principal layers exceed the minimal hopping range, a legitimate grouping that produces exact nullspaces without changing the underlying lead.
3. Recover channel spectra/noise and the complete multi-terminal conductance matrix. A scalar total transmission does not determine its eigenchannels or partition noise; a two-terminal-only treatment misses a physical contact.

The input does not provide an assembled device matrix or precomputed lead selfenergy. Real-space assembly therefore cannot be compressed away into calling a universal dense inverse on a supplied matrix. The generated devices retain 7,408–11,144 orbitals under an explicit 1,024 MiB process address-space cap. One complex dense matrix already exceeds that cap for InAs; ordinary dense matrix-plus-factor allocations exceed it for Si too. These are allocation estimates, not a measured generic dense failure. The parent will separately measure a generic dense baseline; no such result is fabricated here.

Anti-compression decision: retain this pilot. The geometry/lead construction and causal singular-lead problem are separate from extracting the complete observable set. An intentionally optimistic oracle-assisted ablation leaves all correct outputs untouched except replacing each channel spectrum with equal channels having the exact total transmission, then recomputes noise. Its legacy average scores are approximately 0.860 on test and 0.891 on challenge, with worst cases 0.776 and 0.702. This is not a participant baseline: it is an upper-information diagnostic of whether traces alone determine the other outputs. InAs three-terminal degeneracy and one near-zero-noise Si case make this diagnostic almost exact on some cases; the audit records that rather than claiming every branch defeats it. Noise remains genuinely nontrivial elsewhere, and the balanced/worst-family reporting exposes the difference.

## Strong-reference and validation design

- Main oracle: official `kwant.physics.modes` with its default stabilization selection, followed by official `kwant.smatrix`.
- Independent transport route: official `kwant.greens_function`, default mode stabilization, and contact-space broadening factors to calculate transmission eigenvalues. This is a separate Green-function versus wave-matching route within the same authoritative library, not a wholly independent package.
- Independent geometry: later official `TBmodels.Model.supercell` zero-translation blocks and `Model.hamilton`, compared against the finite Kwant assembly on both real materials.
- Physics checks: current conservation, scattering unitarity, causal broadening, and agreement with official two-terminal shot noise.
- Source-correctness finding: explicitly forcing `(True, True)` stabilization on the real Si smoke lead produced zero propagating modes and noncausal broadening, whereas the official default returned three channels and causal broadening (minimum eigenvalue about `-1.7e-14`). Forced generalized stabilization was rejected, not hidden by loosening tolerances. Both transport routes use the validated official default; a separate surface Dyson residual tests selfenergy consistency.
- Split discipline: four balanced material/contact families in each of test, challenge, confirmation. Confirmation has separate fixed seeds, inputs, and stored references and is not used in tuning/participant trials.
- Baseline: the unchanged bulk-only CLI computes genuine bulk bands but lacks all required transport fields. Its measured zero capability score is missing-feature evidence, not a fabricated inaccurate transport algorithm. All four baseline processes exit successfully inside bwrap. A continuous normalized-error score is calibrated against the measured baseline; it is not a pass count.

## Primary implementation sources

- <https://kwant-project.org/doc/1/reference/generated/kwant.physics.modes>
- <https://kwant-project.org/doc/1/reference/generated/kwant.builder.ModesLead>
- <https://kwant-project.org/doc/1/reference/generated/kwant.solvers.default.smatrix>
- <https://kwant-project.org/doc/1/reference/generated/kwant.solvers.common.GreensFunction>
- <https://kwant-project.org/doc/1/reference/generated/kwant.physics.two_terminal_shotnoise>
- <https://pypi.org/project/kwant/1.5.0/>
- <https://tbmodels.greschd.ch/en/latest/reference.html>
- <https://github.com/Z2PackDev/TBmodels/commit/a613d8e5a8be831b10db7ce4139971120bab675c>

### Exact data and source pins

The data checkout is `authoring/sources/TBmodels` at `39d7eb096d809137373774ef6ba337fdf36349bc`:

- InAs: `tests/samples/InAs_sym_reference.hdf5`, 14 orbitals, 501 full directed hopping translations, maximum translation components 5. Source SHA256 `a758667871fc63855fcdc89676aa14441a86b0875f7ebb2f79ad707419fe32c6`.
- Si: `tests/samples/cli_eigenvals/silicon_model.hdf5`, 8 orbitals, 189 full directed hopping translations, maximum translation components 3. Source SHA256 `443770bd12bae607f9786af8c5e886569176a13ba15f33ae0ff09c1798f6483a`.
- Public starting capability: <https://github.com/Z2PackDev/TBmodels/blob/ab24b723e4b35dd08d86aa098a5cadeacab96e83/tbmodels/_tb_model.py>.
- Exact InAs data: <https://github.com/Z2PackDev/TBmodels/blob/39d7eb096d809137373774ef6ba337fdf36349bc/tests/samples/InAs_sym_reference.hdf5>.
- Exact Si data: <https://github.com/Z2PackDev/TBmodels/blob/39d7eb096d809137373774ef6ba337fdf36349bc/tests/samples/cli_eigenvals/silicon_model.hdf5>.

Private originals, converted NPZs, historical source, and model hashes are in `private/reference/models/`. The package versions and installed implementation SHA256 hashes are recorded in `private/reference/validation_summary.json`. `private/reference/requirements.txt` pins the installable official stack; it is private only. The later geometry check uses released TBmodels 1.4.3; its cited historical supercell introduction is not being misrepresented as the identical released source.

## Isolation

Only `participant/` and `attempt/` may be exposed to a participant. Private reference code, installed Kwant, stored outputs, seeds, manifests, and this note remain author-only. Submitted execution uses the parent's `authoring/sandbox_exec.py` bwrap helper, mounting only participant, submission, a single self-contained NPZ, and its output directory. It removes author package paths and networking. `--trusted-reference` bypasses bwrap only for entrypoints beneath this pilot's private reference directory, enabling author validation against the private installed solver. Sandbox failures are surfaced rather than replaced by unsandboxed submitted execution.

## Execution and final validation

All paths below are relative to `pilots/03_device_transport/` unless stated otherwise.

| Check | Measured result |
| --- | --- |
| Stored splits | 4 test + 4 challenge + 4 confirmation, two energies per case |
| Real device orbitals | 7,408–11,144, unchanged from the generated full-size design |
| InAs 2-lead layer dimension/rank | 168 / 92 |
| InAs 3-lead layer dimensions/ranks | 168 / 62, 168 / 62, 224 / 94 |
| Si lead dimension/rank | 64 / 31 |
| Main official solve runtime | 0.90–2.44 s per full case, excluding interpreter startup |
| Independent test core / worst family | 0.9999999999999798 / 0.999999999999963 |
| Independent challenge core / worst family | 0.9999999999999909 / 0.9999999999999807 |
| Independent full-process runtime / RSS | 1.61–13.04 s / 115.4–215.4 MiB |
| Resource limit for reference controls and submissions | 90 s wall time; 1,024 MiB address space; one BLAS thread |
| Measured unextended baseline | core 0, worst family 0, four successful isolated exits |
| TBmodels bulk convention error | InAs 1.07e-14; Si 4.45e-15 max absolute |
| TBmodels finite supercell block error | exactly 0 for both materials |
| Scattering unitarity error across stored cases | below 3.1e-12 |
| Current conservation error across stored cases | below 1.7e-13 |
| Retarded surface Dyson relative residual | below 5.0e-10 |

`private/reference/validation_summary.json` records the final audit, source hashes, all case dimensions/resources, and the trace-only diagnostic. `baseline_report_test.json`, `control_report_test.json`, and `control_report_challenge.json` in the same directory contain per-case errors, runtime, RSS, and logs. `models/geometry_validation.json` and `models/smoke_validation.json` retain independent geometry and small-case checks. The independent route shares the official lead-mode code with the main reference; the separate surface Dyson residual and causal broadening checks are therefore essential, not redundant claims of package independence.

The near-zero-noise Si challenge case was retained unchanged (maximum noise factor about 8.65e-9), rather than selecting a replacement to manufacture difficulty. Near-zero noise alone does not establish ballistic transmission. An initial positive-noise acceptance assertion was removed in favor of the physically valid nonnegative-noise check. The source models, case seeds, geometries, gates, and energies were not changed. No confirmation submission, independent control, or trace-only diagnostic was run; only authoritative reference generation and file-integrity checking touched confirmation.

### Commands

From the task root:

```bash
P=pilots/03_device_transport
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python "$P/private/evaluator.py" --submission "$P/attempt" --split test --output "$P/private/attempt_test.json"
python "$P/private/evaluator.py" --submission "$P/attempt" --split challenge --output "$P/private/attempt_challenge.json"
```

The parent supplies the participant implementation in `attempt/`; this builder intentionally did not write a participant solution. Use `--split confirmation` only for the final fresh evaluation. If the outer execution sandbox blocks bwrap namespace creation, rerun the evaluator with approved escalation while keeping bwrap enabled; never fall back to unsandboxed submitted execution. This was necessary for the successful baseline audit on this host.

Author-only reproducibility commands:

```bash
python "$P/private/reference/post_audit.py"
```

To regenerate only when intentionally rebuilding the frozen suite, use `python "$P/private/reference/build.py" --prepare --split all`; it reads shared sources without modifying them. Reinstall a missing private stack with `python -m pip install --target "$P/private/reference/vendor" --no-deps -r "$P/private/reference/requirements.txt"` in the recorded compatible Python/NumPy/SciPy environment. No network is needed for normal evaluation or reference execution.
