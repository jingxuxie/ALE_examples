# Longer-range counterexample search: negative result

## Decision

Reject a longer-range ratchet on this evidence. The completed submitted solver
matches all three validated privileged references within the existing 180-second,
8192-MiB budget. There is no demonstrated correctness or performance failure and
no reason to launch fresh confirmation cases or increase the public budget.
No fresh model was launched. Silicon was not investigated. Initial manifests,
data, participant files, scoring code, and the submitted solver were not edited.

## Cases and measured resources

The seed is 9082716. Every displacement and force is an unchanged official stored
observation. Each case uses disjoint training/heldout indices recorded in its
metadata. NaCl retains the 512-atom harmonic fit and 64-atom cubic fit; GaN and
SnO2 use simultaneous second/third-order fits on 128 and 72 atoms, respectively.

| Case | fc2 / fc3 basis dimensions | Reference seconds / peak KiB | Submitted solver seconds / peak KiB | Relative fc2 / fc3 error |
| --- | --- | --- | --- | --- |
| NaCl64, full cubic range | 166 / 758 | 15.376 / 664028 | 12.914 / 221420 | 2.87e-15 / 7.38e-15 |
| GaN128, 5.5 Angstrom | 220 / 1859 | 26.738 / 3434108 | 10.967 / 623772 | 1.21e-9 / 1.21e-8 |
| SnO272, 5.5 Angstrom | 158 / 3217 | 18.524 / 788532 | 32.961 / 830148 | 5.31e-15 / 5.64e-13 |

NaCl's finite numeric cutoff, 16.80986343116426 Angstrom, is an all-triplet
supercell bound: its entire cubic support mask is true. This is the ordinary
full-supercell objective, not a chosen distance-boundary perturbation.

Reference timings include imports, fitting, native full-tensor contractions,
rank/stationarity audits, a matched short-range control fit, and serialization.
The private worker enforces a 180-second wall limit and an 8192-MiB RLIMIT_AS.
Submitted and starter programs run through the unchanged common bwrap runner at
180 seconds / 8192 MiB. The first reference-run timings are also retained in each
comparison record; the table uses the rerun that includes explicit rank checks.

## Independent reference validity

The official symfc 1.5.4 basis and native solver are used without a replacement
fitting algorithm. Normal-equation eigenspectra certify full numerical rank well
above their dimension-scaled roundoff thresholds:

- NaCl harmonic: 166/166; estimated design condition 8.18.
- NaCl cubic: 758/758; estimated design condition 1.74.
- GaN joint: 2079/2079; estimated design condition 776.19.
- SnO2 joint: 3375/3375; estimated design condition 2840.84.

These are Gram-spectrum rank checks, not claims of an independently computed
design SVD. Native normal-equation stationarity is cross-checked by projecting
the gradient of directly contracted forces into every official basis direction.
The largest relative direct gradient is 2.02e-15. Direct training SSE also agrees
with the native normal-equation quadratic objective. Full native force constants
are contracted independently of the public compact implementation; staged
harmonic folding uses a separate Cartesian/species atom match. Native/compact
predictions and acoustic, permutation, crystal and support constraints pass.
The maximum submitted-versus-native heldout prediction RMSE is 1.75e-10 eV/Angstrom.
No rank defect or nonoptimal native solution was found, so the newer official
sparse solver was not needed and no custom oracle repair was introduced.

## Physical relevance and heldout results

Short-range controls use the same training/heldout observations and native
objectives, with only the cubic support changed. All RMSE values are against
real heldout forces in eV/Angstrom, not synthetic reference-generated targets.

| Case | Short / long cutoff | Short / long heldout force RMSE | Cubic norm outside short support |
| --- | --- | --- | --- |
| NaCl64 | 4.5 / full | 9.26453e-4 / 9.30426e-4 | 10.023% |
| GaN128 | 4.0 / 5.5 | 1.18386e-4 / 8.72786e-5 | 2.724% |
| SnO272 | 4.0 / 5.5 | 1.99677e-4 / 2.05899e-4 | 7.560% |

GaN demonstrates a meaningful longer-range predictive improvement, approximately
26%, but is still solved successfully. The larger NaCl and SnO2 supports do not
improve heldout prediction on these splits; increasing their range solely to
seek failure would not be supported by these physical validation results.

The unchanged core awards zero tensors 0.74908, 0.72799, and 0.72625 on these
three cases. Those scores are recorded only to document the known normalization
loophole. They are not used as evidence of hardness or of solver success.

## Provenance and reproduction

The evaluated solver SHA256 is
`1efe257d6162ebf4fe4c603657c5e87c855f0346b179400e30c710c8feebc71f`.
Oracle pins are symfc 1.5.4, phonopy 2.43.4, phono3py 3.19.2 and spglib 2.5.0.
The official symfc v1.5.4 commit is
`7b774611f10a5930c9e760a759e304020217c087`.
Each case metadata records source URLs pinned to repository commits and SHA256:

- `phono3py/example/NaCl-rd/phono3py_params_NaCl.yaml.xz`, source commit
  `49e7d7225a8931df59ed2f4603344ea8d89846f2`.
- `symfc/tests/dfset_GaN_442_rd.xz` and the `ph_gan_442` official fixture,
  source commit `f207947715166f5307b7cc7b8738c309b7e2fe3f`.
- `symfc/tests/dfset_SnO2_223_rd.xz` and the `ph_sno2_223` official fixture,
  the same pinned symfc source commit.

The separate list manifest is `../../challenge_pool/counterexamples_manifest.json`.
Each entry points to its new input, reference, baseline and metadata. Per-case
subdirectories here contain native predictions, long/short references, submitted
outputs, stdout/stderr, resource records and raw comparisons. Aggregate results
are in `search_results.json`.

From the target directory:

```
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  python -B concepts/fitting/private/reference/counterexample_search.py
```

`--seed INTEGER` selects another deterministic split; it was not used to search
additional cases. `--reference-only` reruns the objective/rank audit while keeping
stored submitted outputs. `--compare-only` reuses existing oracle files. A subset
can be selected with repeated `--case nacl64_full`, `--case gan128_r55`, or
`--case sno272_r55`. Fresh seeds are not recommended without a justified new
hypothesis and approval; this search supplies no counterexample to confirm.
