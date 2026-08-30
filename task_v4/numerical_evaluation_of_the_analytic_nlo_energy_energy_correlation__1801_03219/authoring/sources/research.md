# EEC source research and independent formula audit

Research date: 2026-08-28. This note records primary-source evidence, authoring cautions, and the provenance of the independently retrieved numerical source. It does not change any concept package.

## Authoring scope and clarified concepts

- **A** is a static, shared, piecewise-Chebyshev artifact with **320 total scalars**, assessed jointly on point values, finite-bin quantities, derivatives, and color combinations. Dense cached formula evaluation is disallowed. The earlier concern about an unconstrained lookup-table surrogate does not describe this clarified contract. The approximation/resource constraint is an authoring choice, not a performance claim from the paper.
- **B** seeks false confidence in adaptive quadrature of weighted EEC moments. Source-reported cancellation motivates testing; it does not establish that a particular strong quadrature method fails.
- **C** is prescribed, complete discrete-autocorrelation inversion on **1024 directions**, with a fixed ternary energy multiset and many antipodal pairs. It is not the task of finding any pair of nonunique events. The previously discussed four-particle/six-particle example violates the fixed-multiset premise and is not a solution or hardness assessment for C.
- The three verification contracts should remain distinct: constrained artifact quality, independently checked numerical error claims, and exact prescribed-data reconstruction. No package reproduction or direct formula implementation is proposed as the participant deliverable.

## Primary-source map

### 1. Original calculation and official ancillary

- Paper: <https://arxiv.org/abs/1801.03219>
- Version-pinned text, including supplement: <https://arxiv.org/html/1801.03219v2>
- PDF: <https://arxiv.org/pdf/1801.03219v2>
- Published article: <https://doi.org/10.1103/PhysRevLett.120.102001>
- Official source archive actually retrieved: <https://arxiv.org/src/1801.03219v2>

Dixon, Luo, Shtabovenko, Yang, and Zhu give the analytic NLO EEC. The arXiv record identifies `EEC_NLO_supplemental.m` as added in v2 on **January 11, 2018**. The artifact is a Mathematica expression file, not a separately verified GitHub package.

Source-native numerical cautions:

- Equations (9)--(11): individual collinear terms have poles as severe as `z^-5`, while the combined result scales as `log(z)/z`. The rough conditioning scale `z^-4/abs(log(z))` implies approximately 23 digits of cancellation at `z=10^-6`; this is an estimate, not a measured quadrature failure.
- Supplement, Figures 3--4: the `C_F^2` channel has strong real--virtual cancellation for `-0.5 < cos(chi) < 0`, or `0.5 < z < 0.75`, despite over `10^10` Event2 samples and cutoff `10^-14`.
- Figure 1: the rightmost-bin discrepancy is mainly a finite-bin-width effect.
- Equations (7)--(8) normalize the coefficient to `sigma_0` and use `dSigma/dcos(chi)`, not `dSigma/dz`; changing density variables introduces a factor of two.
- Equation (28)'s color basis differs from Equation (8): `B_CF = Blc - 2*Bnlc`, `B_CA = Bnlc`.

### 2. Spectral uniqueness and its exceptions

- Larkoski and Thaler, *A Spectral Metric for Collider Geometry*: <https://arxiv.org/abs/2305.03751>
- Gambhir, Larkoski, and Thaler, *SPECTER*, Section 2.4: <https://arxiv.org/html/2410.05379v2#S2.SS4>
- Official follow-up repository: <https://github.com/rikab/SPECTER>
- Paper's analysis artifacts: <https://github.com/rikab/SPECTER/tree/main/studies>

The spectral-metric paper qualifies uniqueness by excluding isometries and measure-zero event sets. SPECTER supplies an explicit degeneracy: an equilateral triangle with energies `(2/3, 1/6, 1/6)` and a two-particle configuration with energies `(1/2, 1/2)` share a spectral distribution. Nearby degeneracies can also strongly separate spectral distance from energy-flow distance. These are motivation for inverse-observable limitations, not proofs about the selected integer inversion instance.

For C, preserve the complete prescribed autocorrelation, energy multiset, momentum constraints, and the specified equivalence relation. Do not substitute histogram agreement, a subset of Fourier data, or an arbitrary collision in the representation. Account explicitly for the identification of opposite cyclic lags by the angular observable and for any additional identifications imposed by antipodal constraints. A solution's exact algebraic certificate and its physical noncongruence are different checks. No claim that the 2018 NLO coefficient itself is wrong follows from event nonuniqueness.

SPECTER Section 3.1 also documents a separate implementation limitation: fixed-size inputs discard least-energetic particles above the capacity, which is not IRC safe; the authors recommend IRC-safe clustering beforehand. This is contextual evidence, not a selected task or a claim about every repository version.

### 3. Archived ALEPH measurement constraints

- Detailed analysis note, pinned version: <https://arxiv.org/html/2505.11828v1>
- Main official analysis code, Appendix A: <https://github.com/FHead/PhysicsEEJetEEC>
- Independent cross-check code, Appendix D: <https://github.com/jingyucms/AnalysisLEP>
- Later experimental/theoretical paper, pinned version: <https://arxiv.org/html/2511.00149v1>

The analysis note provides concrete experimental failure surfaces:

- Sections 4.3--4.4.2: energy-bin-center projection of a two-dimensional unfolded histogram requires an approximately **4%** correction.
- Section 6: three-digit archival precision motivates `0.006 < theta < pi - 0.006`, equivalent to endpoint distances approximately `9e-6` in `z`.
- Appendix D: unfolding introduces off-diagonal covariance and can increase statistical uncertainties by **50%**. Sub-percent central-value agreement between independent workflows does not itself establish uncertainty coverage.
- Appendix B: tightening the sphericity-axis selection deepens the efficiency dip near `z=1/2`; corrected distributions should close under selection changes.
- Section 7: self-pair conventions, pair double counting, charged-only versus all-particle measurements, and fixed collision energy versus event-visible-energy normalization obstruct naive OPAL/ALEPH comparisons.

The later paper reports prior-dependence effects around **5% centrally and 10% near endpoints**, relying on the available archival detector simulation. Its charged-track predictions require track-function information. Therefore the inclusive, fixed-order partonic NLO coefficient is not an experimental truth oracle over the entire measured spectrum, particularly in confinement regions. These version-pinned facts should not be relabeled as a review of the latest releases or measurements.

### 4. Event-level covariance and an upstream issue

- EnergyEnergyCorrelators author documentation: <https://github.com/pkomiske/EnergyEnergyCorrelators/blob/main/README.md>
- Associated CMS Open Data paper: <https://arxiv.org/abs/2201.07800>
- RooUnfold issue 16: <https://gitlab.cern.ch/RooUnfold/RooUnfold/-/issues/16>
- Public issue metadata used to verify the report: <https://gitlab.cern.ch/api/v4/projects/65369/issues/16>

EnergyEnergyCorrelators documents event-by-event histograms, optional bin covariance, a separate crude variance upper bound, and overflow-dependent treatment of that bound. These distinctions motivate event-level uncertainty checks; they do not demonstrate a package defect. Pair entries from one physical event must not silently become independent experimental events.

RooUnfold issue 16, opened **October 27, 2022**, reports a 2D Bayesian example putting many entries into one bin despite variations in binning, smearing, and sample size. The ALEPH note Section 4.2 cites this issue when explaining its use of version 2.0.0. The issue description was independently retrieved through the public API. This is a historical report, not a reproduced bug, resolved-version determination, or statement that current RooUnfold releases are broken. No source-relevant corrective commit was verified.

## Numerical verification warnings

These are audit/authoring recommendations, not claims of demonstrated participant failure:

1. Separate integrand-evaluation error, quadrature error, finite-bin conventions, and approximation error. An accurately integrated inaccurate callback is not evidence against the quadrature rule.
2. Near channel or color-combination zeros, distinguish absolute/scaled error from pure relative error. An accurate QCD sum can conceal inaccurate individual channels.
3. For A, validate derivatives and bin integrals in addition to point samples, including piece boundaries. Passing sampled values alone is not a certificate for the joint 320-scalar contract.
4. Treat endpoint expansions as controlled asymptotic expressions, not arbitrary-accuracy values at a fixed switching point. An endpoint shift and unknown-coefficient recovery are not established by source agreement alone.
5. Numerical endpoint integration needs a well-defined convergent observable. Do not integrate the open-interval coefficient as an ordinary density over endpoints and silently infer the full distributional normalization, which also involves endpoint contributions.
6. Agreement of formulas does not validate a derivative oracle that returns binary64 numbers, a fixed precision budget at arbitrarily small `z`, resummation, detector corrections, or the selected concepts' achievable difficulty.

## Retrieved artifact provenance

All downloaded material is confined to this `authoring/sources` directory. Only the ancillary member was extracted; the other archive members were not installed or executed.

| Artifact | Size | SHA-256 |
| --- | ---: | --- |
| `arxiv-1801.03219v2.tar` | 612811 bytes | `8f992e1dee08f41d312fb0e5410bd5c9390934a3abbe98a6de44733025a336a6` |
| `EEC_NLO_supplemental.m` | 13543 bytes | `2995c05e1e8fe500fd63ecd66e0b6e63a7def2ca48aeef77c476ab719856c4e8` |

The direct URL `https://arxiv.org/src/1801.03219v2/anc/EEC_NLO_supplemental.m` returned HTTP 404. The successful official archive URL above returned HTTP 200. Its ancillary member is named `EEC_NLO_supplemental.m` at the archive root, not inside `anc/`. The unchanged file header contains the draft placeholder `arXiv:1801.nnnnn`; provenance is established by the version-pinned official archive, not that placeholder.

Authorized local comparison target:

`tasks/numerical_evaluation_of_the_analytic_nlo_energy_energy_correlation__1801_03219/solution/v_01/solve.py`

SHA-256: `2fecc7eb7b2cec38c92f8cc1a2716377a3d2a90b931fd1b44c9a0887a572a2c5`.

No other prior-task content or concept-package content is used as the source oracle. The official Mathematica expressions, rather than the previous implementation or printed HTML transcription, are the audit reference.

## Independent comparison results

**Result: no formula mismatches found.** The original comparison target remained byte-for-byte unchanged.

The audit ran with Python 3.10.12, SymPy 1.12, and mpmath 1.3.0. The official Mathematica expressions were parsed independently with SymPy's Mathematica parser; `g[weight,index]` names and zeta/polylogarithm heads were mapped to their symbolic counterparts. The local Python function definitions were taken from its AST without running its main block. For the algebraic audit, Horner accumulation used exact rational arithmetic and each basis function was treated as an independent symbol. This checks all coefficients, signs, denominators, powers, and the constant term, rather than relying on selected numerical samples.

| Official channel | Ancillary start line | Local channel start line | Nonzero basis/constant coefficients | Exact result |
| --- | ---: | ---: | ---: | --- |
| `Blc` | 25 | 41 | 10 | identical |
| `Bnlc` | 42 | 52 | 11 | identical |
| `BNf` | 62 | 64 | 8 | identical |

- The local channel expressions contain **25 Horner arrays with 190 integer entries**. Their full rational prefactors match the independent official expressions exactly.
- **36 coefficient slots** were compared: the constant and 11 possible basis coefficients in each of three channels, including zero slots. All differences simplify to zero.
- **All 11 used basis definitions** match exactly: `g11`, `g12`, `g21`, `g22`, `g23`, `g24`, `g31`, `g32`, `g33`, `g34`, and `g35`. Logarithmic simplifications are understood on the physical real domain `0 < z < 1`, not as assertions about arbitrary complex branches.
- The color assembly in local line 82 matches paper Equation (8) exactly: `cf**2*blc + cf*(ca-2*cf)*bnlc + cf*nf*tf*bnf`.

For a separate numerical check, the parsed official basis and channel expressions were lambdified independently to mpmath, without common-subexpression elimination, and compared with local `_components` at **160 decimal digits**. The 15 points were `0.125`, `0.5`, `0.625`, `0.75`, `0.9`, and both `10^-k` and `1-10^-k` for `k = 2, 4, 6, 10, 14`. All **45 channel comparisons** passed the scaled-error threshold `1e-90`, with error defined as `abs(local-official)/max(1,abs(official))`.

| Channel | Maximum scaled discrepancy over the 15 points | Value at `z = 1/2` |
| --- | --- | --- |
| `Blc` | `2.70223852245e-105` | `37.9802361799721698324107345771` |
| `Bnlc` | `4.33021557513e-106` | `19.3523064590746233644526598336` |
| `BNf` | `5.05072281994e-106` | `-7.54065731790173766584578167731` |

### Verified wrapper limitation, not a formula mismatch

The public `nlo_coefficient` in local lines 75--83 enters `mp.workdps(70)` and returns `float(mp.re(ans))`. Its output is binary64, even when the input is an arbitrary-precision number. In a diagnostic at 80 working decimal digits, `z = 1/2`, and `(ca, cf, tf, nf) = (3, 4/3, 1/2, 5)`:

- Differentiating the internal high-precision channel combination gives `13.2502559397316111828843691358`.
- Applying `mp.diff` directly to the public float-returning wrapper gives **`0.0`**.

This does not make the existing binary64 API a transcription error, but it rules out using that wrapper directly as the arbitrary-precision derivative oracle for A. Use the internal expressions under a controlled precision policy for such an oracle; derivative construction and precision selection remain the main session's responsibility. Fixed 70-digit evaluation is also not a uniform relative-accuracy guarantee arbitrarily close to a cancellation endpoint.

### Audit boundaries and reproducibility

The audit verifies the three channel formulas used by the prior solution, their 11 basis functions, and the documented color combination. It does not certify the ancillary's separate LO expression, `Bqq`, unused basis functions, or endpoint-series coefficients; it does not execute Mathematica. It also does not validate any concept package's surrogate, derivative implementation, bin quadrature, verifier, or prescribed autocorrelation target. Both numerical paths use mpmath, so their numerical agreement alone is not an independent special-function-library validation; the exact algebraic comparison is the stronger transcription check.

The source archive, extracted ancillary, original local-file hash, parser/library versions, comparison dimensions, complete numerical test grid, error convention, and results are recorded above. Audit programs ran in memory with bytecode writing disabled; no audit implementation or downloaded material was placed outside `authoring/sources`. Follow-up repository links are contextual and were not pinned to a corrective commit or executed as numerical oracles. Only this research note and the two explicitly requested source artifacts were written by this audit.
