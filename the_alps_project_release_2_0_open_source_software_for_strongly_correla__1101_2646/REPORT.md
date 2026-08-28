# ALPS solution-gap tournament

## Decision

**Rejected: no built concept qualifies as a frontier-hard task. No task is accepted or promoted.**

Four isolated `ultima-alpha` attempts solve all **70 distinct hidden cases**, including both additional source-grounded stress regions. The lowest reported hidden-family score is **0.999989105**, far above the required fresh-agent score below 0.70. No tested central component remains incorrect. A low score from a weak baseline, a sophisticated paper, or an expensive authoring computation is not being counted as evidence of frontier hardness. `selection.json` records the machine-readable rejection; `private/FINAL_AUDIT.json` records the final integrity and reference checks.

## Sources and candidate directions

The target paper, official ALPS history, later ALPS MPS paper and ancillary archive, ALPSCore Alea, and the official matrix-continuation implementation were inspected. Exact repository pins and source-file hashes are in `private/source_ledger.json`. Detailed candidate briefs, including starting artifact, privileged artifact, outcome, shortcut, independent bottlenecks, and checking method, are in `CANDIDATES.md`; additional research evidence is under `research_stats/` and `research_mps/`.

| Direction | Candidate gap | Disposition |
|---|---|---|
| A: pre/post behavior | Signed, correlated nonlinear statistics versus legacy scalar/iid handling | Built as c01; later unchanged ALEA code supplies the private oracle. |
| B: adjacent improvement | Release-era ED/DMRG interfaces versus later general MPS spectroscopy | Built as c03; independent pinned TeNPy supplies converged references. |
| C: realistic scale | Barrier-spanning extended-ensemble quantum sampling | Not built; executable reference/calibration cost, not a prediction of agent success. |
| D: physical-family transfer | Segment impurity sampling versus general complex multiorbital CT-HYB | Not built; a larger solver-build and stochastic-validation project. |
| E: real-data discrepancy | Isotropic ladder fitting versus anisotropy/additional experimental observables | Not build-ready: no validated privileged fit and sufficiently characterized raw data established. A later bosonic-antiferromagnet dataset was also located, but its custom theory code was author-request-only. |
| F: integration | Multiband AFM, fermionic transforms, and signed Legendre measurement faults | Built as c02 using exact upstream fix provenance and independent numerical checks. |
| G: missing ablation | Sign-free checks conceal the CT-HYB Legendre double-sign error | Incorporated into c02, not counted as a fifth concept. |
| H: accuracy/correctness | Scalar continuation versus causal full-matrix reconstruction and Dyson consistency | Built as c04 with privileged real-axis resolvent references. |

Attribution distinctions matter. The public Python adapters are explicitly authored interfaces, not falsely labeled verbatim ALPS release code. **The original ALPS 2.0 paper already describes binning and jackknife analysis of cross-correlations**, including Python exposure; c01 is not evidence that these capabilities were introduced later. Its unequal-count propagation executes unchanged later ALEA code, while replica-preserving partitioning is an authored task policy. Its original pre/post hypothesis therefore weakens to a participant-hidden-library/adapted-interface gap. Likewise, c03's initial spin/boson task does not establish that those physical families were unsupported in 2011. c02's matrix-Fourier extension is not presented as a production ALPS cluster solver. The three-moment guard is not treated as a physical theorem that a Green function vanishes. c04 uses high-quality precomputed resolvents; the full TRIQS stack was not compiled and is not claimed to have been.

The 192-site doped Hubbard ladder in the later MPS paper remains an untested direction, not an unavailable reference. A late audit corrected an incomplete initial inspection: the small arXiv ancillary archive has an empty results directory, but its README links the complete author archive at DOI `10.6084/m9.figshare.1092509`. That archive was downloaded, checksum-verified, and inspected. Its seven runs use the **same** 96-rung Hubbard Hamiltonian, `U=8`, hopping 1, and `Nup=Ndown=84`, with bond dimensions 800 through 3600. Different truncations of one physical system are not fresh independently varied physical holdouts. Applying the already-submitted spin/boson program to an unsupported Hubbard schema would be an out-of-contract failure, not a valid counterexample. This report does not claim to have reproduced the author's calculation or substitute the present spin/boson cases for it. The complete source and HDF audit is retained under `private/sources/supplement_audit/`.

All seven author HDF5 files contain observables and optimization diagnostics, **not full MPS checkpoints** or alternate-sector gap references. Their final two bond dimensions differ by about 12.52% and 13.10% in the long-distance singlet-pair correlations at rung distances 80 and 84; those outputs must not be described as uniformly converged exact answers. The audit also identifies a reordered measurement channel, incomplete/inconsistent XML copies, and a zero-filled iteration diagnostic. These source-data cautions are documented, not silently repaired or turned into hidden trivia. See `private/sources/supplement_audit/MPS_HDF5_AUDIT.md` and its accompanying machine-readable evidence.

The target paper's three original VisTrails ancillary files were also parsed, including their base64/XML and embedded ZIP provenance, without executing workflow code or opening their database connections. They document simulation/analysis workflows rather than supply a new demonstrated failure of these submissions. Their inventory and the original-paper attribution correction are in `private/sources/supplement_audit/target_source_audit.json`.

## Four minimal pilots

Each pilot has a concise paper-free `participant/TASK.md`, a separate complete interface contract, unlabeled small examples, a runnable weak workspace, private references and challenge inputs, an evaluator, and an initially empty `attempt/`. No solution-bearing repository or private numerical labels were mounted for the fresh agents.

| Pilot | Core / original challenge cases | Independently scored scientific outcomes |
|---|---:|---|
| c01_stats | 8 / 12 | Signed nonlinear means, joint covariance, partial batches, replica boundaries and results. |
| c02_dmft | 6 / 9 | Fourier tails/endpoints and active channels; every AFM band and Weiss update; signed Legendre coefficients and frequency reconstruction. |
| c03_mps | 6 / 6 | Fixed-sector energy, sector/charge gap, and nonlocal/string or connected correlations across three physical families. |
| c04_continuation | 6 / 9 | Full propagator, off-diagonal coherence, self-energy, matrix causality, and Dyson consistency. |

### Reference qualification

| Pilot | Weak core score | Strong/reference core score | Independent checks |
|---|---:|---:|---|
| c01 | 0.250000 | 0.999999954 | Native ALEA versus independent implementation, analytic and symmetry checks; maximum covariance discrepancy about 1.49e-12 relative. |
| c02 | 0.288889 | 0.999999993 | Independent quadrature and invariances; maximum cross-check discrepancy 5.75e-11. |
| c03 | 0.000214 | 1.000000 | Six ED comparisons; chi 64→128 checks on all original references; charge, norm, sweep, and artifact audits. |
| c04 | 0.058824 | 1.000000 | Spectral decomposition versus full matrix inverse for finite systems; moments/positivity; independent band-grid refinement. |

The c03 and c04 value 1.0 is the stored-reference score, not a claim that an inverse solver was independently rebuilt. Their additional numerical qualification is separately recorded. For c03 the original maximum chi differences are 4.69e-7 in energy per site, 1.75e-5 in gaps, and 1.29e-4 in correlations. All four critical-chain references pass chi 128→256 checks; their maximum differences are 1.89e-7, 4.91e-5, and 2.10e-5 respectively. Regrading the lower-chi outputs against the stronger references across all 16 c03 cases gives a minimum score of **0.999977469**, independently exceeding 0.90. For c04 tested 160×160 versus 256×256 band-grid differences are of order 1e-14.

Realistic-size protection is explicit for c03: original hidden chains/ladders have 32–64 sites, and the further audit reaches 80. Exact conserved-sector dimensions and the memory lower bound for even three real Lanczos vectors are recorded in `c03_mps/private/reference/validation/direct_method_memory_lower_bounds.json`. Every original case exceeds the 8 GiB direct-method memory allowance. The reference is a precomputed specialized MPS calculation, not hidden small ED. The actual weak baseline is also run and fails scientifically.

## Fresh-agent tournament

Every run uses the requested `ultima-alpha` model, high effort, the supplied `run_allowlisted_codex.sh`, an ephemeral session, a read-only participant directory, and a distinct initially empty attempt directory. The limit is 3,600 seconds. All four return normally before the limit, and participant hashes are unchanged.

| Pilot | Run minutes | Core mean | Core worst family | Original challenge mean | Original challenge worst family |
|---|---:|---:|---:|---:|---:|
| c01_stats | 12.73 | 0.999999894 | 0.999999708 | 0.999999758 | 0.999999176 |
| c02_dmft | 14.03 | 0.999999986 | 0.999999958 | 0.999999882 | 0.999999645 |
| c03_mps | 50.84 | 0.999999995 | 0.999999986 | 0.999999999 | 0.999999998 |
| c04_continuation | 53.89 | 0.999999541 | 0.999998624 | 0.999999289 | 0.999997867 |

All exceed the 0.90 solved threshold by a large margin, including their worst families. Differences at the last decimal places are numerical agreement, not substantive difficulty. The raw initial-core ordering from lowest worst-family score is c04, c01, c02, c03; none qualifies as a hard finalist on those results. c01 additionally fails the useful anti-compression test after implementation: one general weighted vector block-jackknife routine covers every case. c02 is a complete multi-module repair rather than a hard remaining research component.

### Solvers and shortcuts observed

- c01 implements the general count-weighted, joint delete-one-batch calculation; cross-correlations and partial batches do not defeat it.
- c02 implements the exact transform, pairwise lattice integration, and signed polynomial-estimator conventions. All source-grounded branches generalize correctly.
- c03 builds a charge-conserving DMRG engine with model construction, sector calculations, and all specified measurements. Merely excluding ED is therefore insufficient to make the initial task hard.
- c04 builds an adaptive matrix-rational reconstruction portfolio with moments, discrete-spectrum treatment, band handling, and causality/Dyson correction. The independent scalar-AAA diagnostic had a continuum case score near 0.003, but the fresh agent repairs that deficiency. That weak-method failure is not counted as a surviving counterexample.

The submissions are complete implementations, not empty or malformed attempts. Each is evaluated on private numerical outcomes, not on its self-reported unit-test claims.

## Counterexample search and ratchet decision

The successful submissions were tested against the original private challenge pools. Two additional source-grounded stress regions were then examined without changing any scoring threshold, precision, output schema, or runtime allowance:

1. **Intrinsically complex dispersive matrices:** three- and four-orbital Hermitian tight-binding models with a complex hopping loop and momentum-dependent mixing. A nonzero imaginary triple-product trace certifies the absence of one common real orbital representation. Grid refinement and spectral/moment checks qualify the references. The completed c04 submission scores **0.999993223 mean**, **0.999989105 worst family** across four new cases. No surviving counterexample is found.
2. **Critical-chain adaptation:** weak-rung spin-half ladders and near-Mott Bose-Hubbard chains at 64–80 sites, inside the existing public parameter bounds. This probes entanglement, canonical-sector convergence, and finite-size gaps rather than adding random edge cases. All four references converge, and the completed c03 submission scores **0.999999993 mean**, **0.999999986 worst family**. The slowest case takes **494.188 seconds**, within its unchanged 600-second limit; peak RSS is **1,522.67 MiB**, below 8 GiB. The largest ladder gap discrepancy is about 1.25e-6, and the boson gap discrepancies are at most 4.24e-10. No scientific or efficiency failure remains.

The search therefore finds **no reference-success/submission-failure region** for either extended concept. There is no meaningful failure cluster to target. The original challenge pools likewise contain no failures. The weak scalar-AAA diagnostic's continuum failure is repaired by the actual c04 submission and cannot justify a ratchet against that submission.

**Ratchets built: 0. Second fresh-agent tests: 0.** All concepts are rejected at the no-natural-counterexample gate; there are no eligible finalists to promote. c03 and c04 receive the deeper source-grounded challenge search because their scale and physical-family adaptation offer plausible remaining bottlenecks, not because their nearly identical initial scores establish a significant ranking. No ratchet is manufactured by adding rows, reducing tolerances, counting an unsupported physical schema as a failure, or silently building a fifth concept. Phase-7 confirmation of ratcheted concepts is consequently inapplicable. The final confirmation scores in this report are repeated grading of the same frozen submissions, **not** additional fresh agents or claims of second-model confirmation.

## Isolation, scoring, and resource audit

- Evaluation copies only the physical input into a temporary work area. Bubblewrap mounts the system runtime, the relevant participant/submission, and that work area; private answers and other attempts are not mounted. Network access is disabled.
- Scores are continuous functions of numerical error, calibrated against weak and strong outputs. Family and component results remain available; a severe branch failure is not concealed by a rounded overall mean.
- Limits are 120 seconds for c01/c02/c04, and 600 seconds with four threads and an 8 GiB target for c03. Independent c03 cases can run concurrently; each retains its own limits and isolated scratch space.
- An infrastructure audit found that outer bubblewrap-launcher `getrusage` did not measure the inner numerical process's peak RSS. The wrapper was corrected to run GNU `time` **inside** the namespace. Completed evaluations were repeated without changing submissions or numerical scoring; earlier reports are retained with `_pre_resource_fix` names. Those old launcher-only memory numbers must not be used as solver memory measurements.
- Explicit closed stdin was added to subsequent runner launches. The original continuation run was not restarted; its log confirms it was working normally. No extra fresh attempt is hidden as an infrastructure retry.

Exact reports are under each concept's `private/runs/`; references and validation evidence are under `private/reference/`. Model, prompt, elapsed time, return code, before/after hashes, and deliverable hashes are retained in each run's `initial.json`.

Final resource-instrumented maxima across core, challenge, and stress evaluations are:

| Pilot | Maximum case wall seconds | Peak inner-process RSS (MiB) | Final worst reported family |
|---|---:|---:|---:|
| c01_stats | 18.879 | 44.84 | 0.999999176 |
| c02_dmft | 18.980 | 44.81 | 0.999999645 |
| c03_mps | 494.188 | 1,522.67 | 0.999999986 |
| c04_continuation | 76.503 | 243.91 | 0.999989105 |

No submission times out or exceeds its measured memory allowance. Runtime and memory are reported separately from numerical scores rather than averaged into a high overall score that could conceal an efficiency failure.

## Reproduction

From the requested output directory, with Linux user namespaces/bubblewrap available:

```bash
export ALPS_EVAL_WRAPPER="$PWD/private/sandbox_exec.py"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python c01_stats/private/evaluator.py --submission "$PWD/c01_stats/attempt/solve.py" --split core --report /tmp/c01-core.json
python c02_dmft/private/evaluator.py --submission "$PWD/c02_dmft/attempt/solve.py" --split core --report /tmp/c02-core.json
python c03_mps/private/evaluator.py --submission "$PWD/c03_mps/attempt/solve.py" --split core --jobs 6 --report /tmp/c03-core.json
python c04_continuation/private/evaluator.py --submission "$PWD/c04_continuation/attempt/solve.py" --split core --report /tmp/c04-core.json
```

The applicable Codex sandbox may require escalation to create nested network/PID namespaces. The submitted process itself still receives only the allowlisted mounts. Change `core` to `challenge` for the original challenge pools, or to a recorded stress split where supported. Do not rerun `run_pilot.py` into a populated attempt directory; it deliberately refuses to reuse an attempt.

Run `python private/audit_supplements.py` to regenerate the source inventory and archive checks, and `python private/finalize.py` to verify the frozen submissions, all recorded scores, reference cross-checks, and final decision. These commands do not launch another fresh agent. Stored report paths, full-precision family scores, and counts are included in `selection.json`.

## Scope of the conclusion

This is an empirical result for the four built concepts and the inspected challenge regions, not a claim that the paper has no harder possible solution gap. Unbuilt general-impurity, extended-ensemble, experimental-mismatch, and large doped-Hubbard directions remain untested. The four-concept budget is respected; none is silently replaced with a fifth concept or promoted on paper complexity alone.
