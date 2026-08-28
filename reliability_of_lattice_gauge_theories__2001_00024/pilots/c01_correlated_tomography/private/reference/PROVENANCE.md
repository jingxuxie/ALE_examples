# Provenance and scientific limitations

Recorded on the session's local date, 2026-08-27, **before case construction
and implementation** (UTC date 2026-08-28).

## Anti-compression rationale

This pilot must not collapse to reading a published gauge-violation number,
fitting one sinusoid, or multiplying single-site marginals. It has two separately
scored numerical bottlenecks: recovering occupation-sensitive amplitudes from
actual, imperfect double-well oscillations; and finding extremal, positive joint
occupation distributions consistent with correlated measurements. The latter
must expose non-identifiability rather than manufacture a unique population.
Independent output components and family-level reporting will prevent a good
fit alone from masking an invalid gauge certificate. Multiple measurement
orientations, incomplete protocols, and occupation-support changes will exercise
different information content. Held-out points remain real measurements, not
samples of the reference fitter. No large labeled same-generator development
set is to be released.

## Sources inspected

- Supplied `authoring/sources/experiment_tex/QuantumLink.tex`, arXiv
  2003.08945v2, Yang et al., *Observation of gauge invariance in a 71-site
  Bose-Hubbard quantum simulator*. Measurement subsections and Extended Data
  Figures 8--10 describe spin marking, single-particle tunneling, atom removal,
  doublon splitting, and bounds on gauge-invariant three-site probabilities.
- Supplied `authoring/sources/dataverse.json`: Harvard Dataverse dataset
  DOI 10.7910/DVN/3RXD5F, public figure data deposited 2020-08-08, CC0.
  Important file IDs are 4013031 (Extended Data Fig.9), 4013036 (Extended Data
  Fig.8), 4013032 (Fig.2), and 4013035 (Fig.4).
- Supplied `authoring/sources/experiment_code` contains ED/DMRG and correlation
  calculations. Its presence is **not** evidence of an independent experimental
  tomography fitter or of access to unpublished shots/calibrations.

## Science caveats and independence policy

- Figure tables are aggregated measured signals/errors, not shot-level data.
  No detector covariance, shot counts, or exact original fit calibrations may be
  assumed unless actually present in the downloaded artifact.
- The protocol's sinusoid has a missing time factor in its typeset argument.
  A dimensionally correct oscillatory model must be defined explicitly in the
  participant input; pilot calibration/normalization choices must be labeled.
- The physical gauge projector is onto `010`, `002`, and `200`. A restricted
  occupation support and detection response are assumptions, not discoveries.
  Bounds are conditional on those assumptions and supplied error envelopes.
  They are not unconditional confidence intervals or true underlying populations.
- Marginals and even the available correlated signals need not identify the
  full joint state. Neither a least-squares representative nor an LP extremizer
  is experimental ground truth. Endpoint witnesses certify feasibility only.
- Published Fig.4 results are an external cross-check, never a substitute for
  missing measurements, and must not be used as hidden population labels.
- Numerical references will be independently checked where practical using a
  distinct optimization route and an exactly soluble analytical invariant.
  A reference solver matching its own generated targets is only a harness
  check, not independent scientific validation. These levels will be reported
  separately, along with any unavailable artifacts or calibration assumptions.
- Source-grounded stress variants may remove channels or widen uncertainty;
  they must not be mislabeled as new experimental runs. Confirmation groups
  must be disjoint from screening groups and withheld from participant files.

## Artifact audit and final design

The archival TAB exports contain **only the first worksheet**. In particular,
4013031 TAB has five A tracks, not the complete four-sequence measurement; Fig.2
TAB is a ramp curve, not occupation measurements; Fig.4 TAB contains population
estimates, not its separately stored gauge-violation sheet. Using only those TAB
files would have been insufficient. Original XLSX downloads recover the other
sheets. No external software or author scripts were executed to read them.

| Local source | Dataverse file ID | Used information |
|---|---:|---|
| `source/ed_fig9.xlsx` | 4013031 | `Fig.a`--`Fig.d`: 20 real readout tracks at five ramp times |
| `source/fig2.xlsx` | 4013032 | `Fig.2c Experimental Data`: five matched density rows |
| `source/fig4.xlsx` | 4013035 | `Violation of Gauss law`: independent published cross-check only |
| `source/ed_fig8.tab` | 4013036 | Downloaded control data, inspected but not scored |
| `source/ed_fig9.tab`, `source/fig2.tab`, `source/fig4.tab` | as above | Retained original archival downloads, not substituted for missing sheets |

The download recipe is the Dataverse access-datafile API with the numeric ID;
original workbooks use its `format=original` query. All downloaded artifacts are
inside `private/reference/source`. `manifest.json` records bytes, SHA256, and
MD5 for every downloaded file. All three original XLSX MD5 values match the
supplied Dataverse metadata. The metadata MD5 is for the original workbook,
**not** the corresponding derived TAB export; the different TAB hashes are not
corruption. Dataset DOI: 10.7910/DVN/3RXD5F, CC0.

### Exact mapping and assumptions

- In each ED Fig.9 sheet, `(A,B,C)`, `(D,E,F)`, `(G,H,I)`, `(J,K,L)`, and
  `(M,N,O)` are `(time,signal,standard deviation)` for ramp times 0,30,60,90,120
  ms. Actual numeric rows are used, including their irregular times and negative
  signals. Every fifth numeric sample is withheld. Per-case lineage records
  exact worksheet names, columns, and visible/withheld row numbers.
- Fig.2c columns A--E are ramp time, mean matter occupation, its standard
  deviation, gauge-link doublon probability, and its standard deviation. Column
  D's workbook header incorrectly says "Doublon on even sites"; the supplied
  Fig.2 caption and accompanying detection description identify the doublons
  on the **odd/gauge** sites. This interpretation is explicit, not hidden
  metadata trivia. Only the average of the two link indicators is constrained;
  no unmeasured separate left/right marginal equality is imposed.
- The 64-state split-signal-sum response is transcribed from supplied ED Fig.10.
  For left/right occupation 0--3 its rows are `[0,.5,1,.5]`,
  `[.5,.5,.5,.5]`, `[1,.5,0,0]`, `[.5,.5,0,0]`, independent of the central
  occupation. Pixel-center inspection confirms the checkerboard transcription.
  The unsplit responses are `1[m=1,r=0]` for A and `1[m=1,l=0]` for B;
  this fixes the local orientation convention. C and D are only used as a sum,
  avoiding an unsupported separate 64-state response derivation.
- The checkerboard lower-bound inequality is checked pointwise on all 64
  states by `validate.py`. The figure image and `QuantumLink.tex` remain in the
  supplied authoring sources; they are not copied into participant input.
- Reported errors are treated as absolute heteroscedastic weights. The free
  offset and fixed zero phase are pilot conventions. The 7.2-ms period and
  96-ms decay are source calibrations. Neither the original fixed offset nor
  inter-channel covariance is in the artifacts. Uncertainty envelopes use
  2.5 times the reported/propagated error plus a declared additive systematic
  radius (0.015 for densities; 0.025 per amplitude in a correlated sum).
  Those radii are design assumptions, not measured detector efficiencies.
- Fig.2b's named occupation sheets are numerical image arrays, not a labeled
  table of all seven tomography observables. Those raw observables and the
  shot-level data remain unavailable. We therefore **cannot reproduce the
  full original population extraction or its claimed precision**. We use only
  available means, doublon probabilities, and correlated oscillations; other
  information is deliberately unconstrained. For example, at 60 ms the
  64-state gauge-valid interval is approximately `[0.116,1]`, not a precise
  estimate of the published physical population. This weakness is scientifically
  real and is part of the identifiability challenge, not hidden ground truth.
- Eight-state `projected` cases additionally exclude all other occupations;
  this is a counterfactual/restricted-model certificate. The other three
  families retain all 64 states. None controls occupations above three atoms.

### References, independence, and scoring

Frozen references fit weighted observations using QR and solve finite-support
linear programs with HiGHS dual simplex. Every inflation/endpoint LP stores a
primal and dual optimality certificate. The strong solver is a separate code
path using weighted centered moments and HiGHS interior point; it reads only
the case, never reference JSON or source data. These two LP paths still share
HiGHS and are **not claimed to be fully independent reference implementations**.

Additional checks use SciPy's separate legacy revised-simplex implementation
for 16 endpoints across all four screening families, Levenberg--Marquardt fits
for all screening/challenge tracks, and direct primal/dual algebra for every
screening/challenge reference. A separate exact Frechet example has identical
link marginals but gauge-valid probability anywhere in `[0,1]`; adding an XOR
observation fixes it to 0.6. That synthetic analytical test is not a scored
experimental case or participant training data. Fig.4 is an external
cross-check of interval compatibility, **not an independent exact oracle for
our different conditional optimization problem**. Compatibility alone is weak
evidence when intervals are broad. The author ED/DMRG scripts are not used as
experimental tomography reference solvers.

The weak baseline omits damping and heteroscedastic weights, then replaces joint
occupation probabilities by products of clipped density marginals and reports
point intervals. Frozen per-case weak losses set the two independent continuous
score scales; each baseline component is consequently 0.5 by construction
(unless at the positive scale floor). Absolute losses are retained for audit.
This is relative calibration, not evidence that the task's absolute difficulty
has been measured on fresh participants. No fresh agent was run.

Screening uses three ramp-time blocks (12 cases), challenge uses 30 ms (4), and
confirmation reserves 120 ms (4). Repeated families within a time block are not
new independent experiments. Four additional sparse, source-row-preserving
challenge candidates are unactivated. Confirmation inputs and targets are
precomputed and hashed, but no participant/strong solver is evaluated on them
during pilot validation. The public release contains one **unlabeled** example.

The evaluator always uses the main-owned isolated runner; submissions are never
imported into the evaluator process. Initial nested-sandbox attempts failed
before worker launch. Host tests revealed namespace startup exceeding 20 seconds
while reference computation took about 0.175 seconds. The wall budget is now
120 seconds, and reports distinguish worker compute time from total wall time.
Final measured scores/runtimes and validation evidence are in
`private/reference/validation/` and
the pilot readiness note; infrastructure timeouts must not be presented as
numerical reference failures.
