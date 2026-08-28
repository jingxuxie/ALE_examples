# c01_stats authoring and reference record

## Scope

This pilot implements direction A in the main CANDIDATES.md. No participant agent has been launched by this sidecar. `attempt/` was left empty for main, which may now populate it. Public files are only the mission, contract, one small unlabeled input, and the runnable weak baseline. Family names, source pins, reference outputs, calibration, and scoring internals remain private.

## Real later reference

The numerical oracle compiles unmodified ALPSCore v2.3.2 source at commit `fccd5403b08c4e5c450229714d28be5ca4a07229`:

- https://github.com/ALPSCore/ALPSCore/blob/fccd5403b08c4e5c450229714d28be5ca4a07229/alea/test/transform.cpp — existing joint `transformer_ratio` and `TEST(twogauss, ratio)`.
- https://github.com/ALPSCore/ALPSCore/blob/fccd5403b08c4e5c450229714d28be5ca4a07229/alea/src/propagation.cpp — actual weighted jackknife pseudovalue implementation.
- https://github.com/ALPSCore/ALPSCore/blob/fccd5403b08c4e5c450229714d28be5ca4a07229/alea/src/batch.cpp — accumulation, weighted means, covariance, and standard errors.
- https://github.com/ALPSCore/ALPSCore/blob/fccd5403b08c4e5c450229714d28be5ca4a07229/alea/src/covariance.cpp — weighted covariance normalization.
- https://arxiv.org/abs/1811.08331 — later core-library followup.

`reference/oracle.cpp` is a thin JSON/expression adapter. It calls upstream `batch_acc`, retains nonempty native batches separately for each replica, combines those batch records without forming cross-replica blocks, and calls upstream `transform(jackknife_prop(), ...)`. Its reported covariance is the native transformed batch covariance divided by native effective observation count. No numerical upstream source is edited. The public contract states this exact finite-sample estimand, including partial-block weighting; nothing about estimator choice is secret.

The build uses only the seven needed numerical translation units and their headers, with linker dead-section elimination. It is not a claim to install the full library or HDF5/MPI functionality. Eigen 3.3.9 headers are fetched from https://gitlab.com/libeigen/eigen/-/archive/3.3.9/eigen-3.3.9.tar.gz. The host's Boost headers parse JSON. Archive SHA-256 hashes, source-file hashes, and the exact compiler command are in `reference/provenance.json`. Upstream license and attribution files are retained in both source trees.

The signed streams and physical expression fixtures are newly authored inputs, not misrepresented as upstream test datasets. The source-backed generic estimator is the privileged artifact. The old `mc/test/signed_obs.cpp`, whose two measurements are both constant one, is not used as a signed oracle. This is a later-method application pilot, not an asserted exact reproduction of a specific 2011 or 2013 defect.

### Unequal-block attribution, precisely

The upstream implementation is not restricted to equal-count batches. In pinned `alea/src/propagation.cpp`, `jackknife` copies the input count vector and stores, for every batch, `N*F(S/N) - (N-n_b)*F((S-S_b)/(N-n_b))`. A native batch stores a sum, so this is `n_b*p_b`, not an unweighted pseudovalue. Native `batch_result::mean()` divides the sum of these records by total count. Native `batch_result::cov()` feeds both each stored sum and its actual count to `cov_acc`; `observations()` is `N^2/sum(n_b^2)`. Dividing native covariance by that observation count produces exactly the disclosed `q/(1-q)` covariance expression. These operations are compiled unchanged, not ported into the oracle.

Author-defined choices are the explicit requested block sizes, preserving independent-replica boundaries, joining the resulting nonempty native batch records, and the physical expression trees. Those choices are disclosed and are not represented as an upstream ready-made replica workflow. No ALPS MPI reduction or arbitrary inverse-variance replica weighting is used. Implementation equivalence does not claim this count-weighted pooling is an optimal infinite-sample estimator when replica autocorrelation times differ.

## Cases and checks

Core: 8 fixed cases, two each of thermodynamic responses, magnetic cumulants, coupled susceptibilities, and effective gaps. Challenge: 12 separately stored fixed cases across the same four families at changed sign persistence, temporal correlation, replica length, and physical parameters. Each case requests three blocking scales, including unequal partial batches and unequal replica lengths. No case or family labels are put in submitted inputs. Reference outputs are precomputed, not generated during evaluation.

`reference/independent.py` independently evaluates the disclosed pseudovalue formula in NumPy with explicit contiguous blocks and centered covariance arithmetic. Every stored native output is compared to it. Additional checks cover analytic iid linear covariance, ordinary equal-block jackknife covariance, global sign reversal, partial batches, missing/malformed outputs, and the inability of exact means to hide absent cross-covariance. These are deterministic estimator checks; they do not assert that a finite block estimate is the infinite-run covariance.

## Evaluation

From the pilot root:

```
python3 private/evaluator.py --submission participant/workspace --split core --report private/weak_core.json
python3 private/evaluator.py --submission participant/workspace --split challenge --report private/weak_challenge.json
```

`--submission` accepts a Python file or a directory containing `solve.py`. A directory is copied with its local files; symlinks are rejected. Inputs are copied to an unrelated temporary `input.json`, and child arguments contain only the staged code and temporary input/output paths. Stored answers, manifests, case IDs, families, calibration, and reference source paths are never passed to the submitted program.

When `ALPS_EVAL_WRAPPER` is set, the evaluator invokes that wrapper with the prescribed participant/submission/work/timeout arguments, also setting its memory limit to 2048 MiB. It collects `_resource.json` before temporary cleanup, including `seconds` and `max_rss_kib`, also on child failure. Do not wrap a private reference folder as a participant submission: author verification uses the self-contained independent script without granting a contestant access to reference artifacts. Main owns actual bubblewrap isolation and participant execution. Without the wrapper, staging and a sanitized environment are convenience boundaries, not a filesystem or network security sandbox.

Each component score is `1/(1+3*error/max(weak_error,floor))`, anchored to the stored native answer (exact score one) and measured weak baseline (usually one quarter). Floors only stabilize a component where the weak baseline is accidentally almost exact. Finite nonzero errors never saturate to one. Errors cover whitened means, log diagonal variances, off-diagonal correlations, and worst-replica mean/full-covariance differences. Each case is capped by its variance, correlation, and replica-covariance components and by its hardest blocking scale. Mean accuracy cannot average away covariance failure. Invalid, missing, nonfinite, timed-out, or malformed outputs receive zero and remain in every denominator.

The report has `mean_core_score`, `worst_family_score`, `families`, `cases`, component scores/errors, timing, and failures. For compatibility, `mean_core_score` is the mean of the requested split; the `split` and `mean_score` fields disambiguate challenge reports.

## Reproduction

```
python3 private/reference/build_reference.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 private/reference/generate.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 private/reference/verify.py
env -u ALPS_EVAL_WRAPPER python3 private/evaluator.py --submission private/reference/independent.py --split core --report private/independent_core.json
```

The last command is an author-only independent implementation check, not a participant run. The evaluator stages that one self-contained file, not its private siblings. Generation records are in `reference/generation_checks.json`; extra-check results are in `reference/verification.json`.

## Anti-compression judgment

There are genuinely independent sign/ratio, temporal-blocking, boundary/count-weighting, and full-joint-covariance failure modes. Nevertheless, one correct general vector weighted block-jackknife kernel can solve all four physical families. This is a substantial compression risk, openly acknowledged rather than hidden through ambiguous estimator semantics. The iid/diagonal baseline is meaningfully weaker, but no intrinsic difficulty claim follows. Main's isolated empirical attempt should decide whether to retain this candidate.
