# Generation 2: sealed and ready for parent activation

Pending task: `package/concept_1/`, with the required sibling
`package/authoring/sandbox_runner.py`. Its
`evaluator/hidden/prelaunch_seal.json` contains 96 verified file hashes.
The builder has not activated this task or launched a new fresh trial.

## Post-activation attainability update — August 29, 2026

The parent has activated generation two and launched fresh v4. Independently,
the parent found a private, fixture-free same-budget achiever: actual v3 with
only the frequency-reduction activation threshold changed from 1024 to 8192.
Byte comparison confirms this is the only source change. Moderate grids use
the existing full-grid solve; the existing large-grid method is retained.

Under the unchanged active evaluator and all original quality/resource gates,
this variant passes all 20 cases: core score 1.00, worst-family score 1.00,
total child CPU 13.545587 seconds, maximum child CPU 1.748676 seconds. Thus
generation-two joint speed/quality attainability is demonstrated, not open.
The parent plans a repeat; this record describes the first verified passing run.
Fresh-trial hardness remains pending v4 and is not determined by this private run.

Artifacts are `../privileged_generation2/solve.py`,
`../privileged_generation2/protocol.json`, and
`../privileged_generation2/evaluation.json`. The protocol explicitly excludes
fixture IDs, lookup, and truth initialization. Recorded solver SHA-256:
`1e4d7d9fec4219417439aa968189a05858f632bbaffc891748d0c9bc0c400748`;
first evaluation SHA-256:
`25e567c9dabc2beffef7a13fcc0140af30c3438365f29dc57746695360cfaa63`.
The variant remains private. No frozen participant, evaluator, status, or
pending-package asset was changed for this handoff update, and no duplicate
portfolio or replay was launched by this builder.

## Fixed objective and privacy

The target remains core score >= 0.90 (18/20), worst-family score >= 0.75
(3/4 in every family), and worst-family improvement >= 0.25 over the original
public baseline. The measured baseline anchor is 0.00, so the improvement gate
is feasible. Residual gates remain 2e-8 for the gap and 2e-9 for Z, with branch
distance <= 0.002 and correct relative low-frequency signs up to a global sign.

Each case still receives 12 parent-measured child CPU seconds, 2048 MiB,
one process/thread, and an 1800-second wall safety ceiling. Output allowance
remains 32 MiB. Scoring code, independent verifier, shared sandbox, baseline,
and workspace starting solve.py are byte-identical to active generation one.
No previous fresh code or private reference is exposed to participants.

## Measured result

| Solver | Accepted | Core | Worst family | Target |
| --- | ---: | ---: | ---: | --- |
| Original public weak baseline | 10/20 | 0.50 | 0.00 | Fails |
| Actual successful generation-one fresh v3 | 16/20 | 0.80 | 0.50 | Fails |

The unchanged v3 solver fails exactly four replacements, all with normal exit
codes rather than resource failures. The complete replay uses 16.282169 CPU
seconds, maximum 3.040172 CPU seconds per case. Existing large-grid cases
case_08, case_09, case_16, and case_17 remain unchanged and pass.

| Replacement | Probe | v3 branch error | v3 gap residual |
| --- | --- | ---: | ---: |
| case_10 | critical_b | approximately 1 | 4.32515e-10 |
| case_11 | critical_c | approximately 1 | 4.39051e-11 |
| case_18 | sheets_b | 0.77848 | 9.78532e-7 |
| case_19 | sheets_c | 0.040581 | 3.70439e-8 |

These new cases have only 9–15 patches and 1536–4096 frequencies. The two
critical outputs are near-normal positive gaps that meet the residual gates
but fail the independently certified nonzero branch. The weak-sheet outputs
have significant branch errors despite a well-developed dominant gap.

## Root cause and certification

Isolated diagnostics using the exact archived v3 code confirm that reduced
frequency collocation moves physical pairing instabilities across unity:

- critical_b: full leading eigenvalue 1.0000000100; reduced 0.9999999320.
- critical_c: full leading eigenvalue 1.0000000030; reduced 0.9999999752.
- sheets_b: three full eigenvalues exceed one, but only one reduced eigenvalue
  exceeds one; both weaker supercritical sheet modes are shifted below unity.
- sheets_c: two full eigenvalues exceed one, but only one reduced eigenvalue
  does. The weak sheet is shifted across its isolated instability.

This is a compression-induced instability/branch-loss cluster, not patch-rank
compression, dimension inflation, paths, or timing jitter. The full matrices
have independently varied anisotropy; nonzero intraband Coulomb repulsion
produces high-frequency sign changes. Weak-interband, sheet-selective
conditioning and the expanded public parameter ranges are documented in FORMAT.

All four new references use builder-owned full-grid Newton solves from two
starting amplitudes, independent full-signed convolution verification at every
frequency, and direct signed sums on distributed rows. Maximum new all-frequency
gap residual is 1.078e-14; maximum cross-start branch discrepancy is 4.793e-9.
All target low-frequency gaps are positive and all new patches exhibit allowed
high-frequency sign changes. These offline certificates alone did not establish
a fixture-free 12-CPU-second solver at prelaunch. That former uncertainty is
superseded by the parent's passing same-budget witness recorded above.

Two independent public draws are supplied as `critical_coulomb_3072.npz` and
`competing_sheets_2304.npz`. They contain only the seven original input arrays.
The complete private 12-case sweep and controls are retained in `cases/` and
`probe_report.json`; generation and measurement cost about 108.66 CPU seconds.

## Audits and retained artifacts

- 27/27 tests pass: 16 physics/package/ratchet tests and 11 security tests.
- Actual normal-state false success is rejected by the branch guard.
- Private filesystem/network/process/thread restrictions and output symlink,
  hardlink, object-array, oversized-header, and NPZ-expansion guards remain tested.
- All original generation-one bytes and its runner match the 93-file snapshot
  manifest. `generation_1_runnable_snapshot.tar.gz` contains `concept_1/` and
  sibling `authoring/sandbox_runner.py`; its archived evaluator passes case_00
  with the original public baseline.
- Actual v3 is archived verbatim at `../../champions/generation_2/`, with its
  original passing generation-one report and provenance. The earlier private
  portfolio remains unsuccessful historical evidence, superseded by v3.
- Structured handoff: `ratchet_evidence.json`, `linear_diagnostic.json`, pending
  `status.json`, pending `adversary/audit_result.json`, and pending `attempts/`.

Recommend a 3600-second fresh trial plus 900 seconds typical evaluation allowance.
Observed full evaluations took 85.24 seconds for the public baseline and
49.94 seconds for v3. Parent alone handles activation and the next fresh launch.

## Deferred idea, generation 3 only if needed

If the next fresh trial solves generation two, consider smooth positive
multimodal alpha2F quadrature with 32–96 distinct phonon bins, fixed integrated
coupling and physical frequency window, and smoothly varying noncommuting patch
matrices. Such a proposal would require genuine quadrature convergence evidence,
an independent public example, new declared ranges, and actual champion failures.
No duplicated modes, padding, new fixtures, or scope expansion were added here.
