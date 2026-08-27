# Source inspection and concept screen

Source: arXiv 1412.3460 v6, official source archive downloaded August 27, 2026.
The seven ancillary files implement an 838-line Python 2 research workflow:
occupation-state enumeration, reflection-orbit normalization, normal-ordered
operators, sparse matrix assembly and persistence, eigensystems, local UV
renormalization, and state-dependent subleading corrections. Sections 2, 3,
4.3–4.4 and appendices A–B are the relevant source. The paper and original
unredacted files remain private, outside every participant allowlist.

## 1. Restore a finite-volume spectrum campaign under physical shifts (A)

Selected for construction, subject to reference and empirical screening.

- Contribution/claim: energy-truncated Fock-space spectra with integrated-out
  high-energy contributions; improved cutoff convergence of vacuum and gaps.
- Artifacts: retain real occupation/mode/operator decomposition, official-code
  cross-checks, and genuine finite-volume operator archives generated from that
  workflow. New physics branches are explicitly benchmark-authored extensions,
  not represented as author artifacts or experimental data.
- Decisions: distinguish normal-ordering/vacuum conventions from UV errors;
  choose local versus state-dependent or explicit-shell elimination; decide
  which stability controls and cutoff experiments support a transfer claim.
  Bare extrapolation, local subtraction, shell elimination, and hybrid methods
  are plausible but need not work equally on all branches.
- Loop: baseline cutoff scan, inspect vacuum/gap and symmetry diagnostics,
  repair/replace, rerun, compare against a distinct ablation.
- Public evidence: exact Gaussian identities, matrix invariants, unlabelled
  low-energy operator archives, a very small calibration, baseline diagnostics.
- Hidden families: Gaussian quadratic field; homogeneous periodic quartic;
  antiperiodic quartic (no zero mode, half-integer momenta); source-deformed
  quartic with cubic/linear terms (no field parity); spatially modulated
  interaction (momentum not conserved). These are model/geometry changes, not
  five coupling values or five seeds.
- Objectives: predictive spectral accuracy, worst-family transfer, measured
  runtime/memory, reproducibility and evidence validity.
- Shortcut audit: diagonalizing the supplied largest matrix only produces the
  raw cutoff baseline. A common scalar energy correction cannot repair gaps.
  A universal least-squares cutoff fit has no labels and must survive physical
  changes. A general local-OPE implementation is possible, but does not alone
  settle finite-volume conventions, nonlocal/state dependence, stability, or
  validity of the experimental inference. Empirical screening must decide
  whether this remaining workflow is genuinely hard.
- Rejection triggers: inaccurate/uncontrolled reference; no substantive
  improvement over raw; one library eigensolve or prescribed formula reaches
  near-reference performance; public interface/infrastructure failure.

## 2. Re-estimate the critical coupling from finite-size scaling (B)

Central claim and official spectra are relevant. Decisions: scaling window,
cutoff extrapolation, competing correction-to-scaling models. Loop: fit, inspect
residuals, collect a new volume/cutoff, refit. Public evidence could be scans and
Ising consistency relations. Hidden families would need independent geometries,
symmetry breaking, and normal-ordering schemes. A bounded scan of the paper's
actual periodic model supplies only parameter changes, however. Likely shortcut:
standard joint regression and a crossing plot. Rejected before construction:
the genuinely heterogeneous version would require a largely new research
dataset, while the faithful bounded version fails the five-family gate.

## 3. Reconstruct the UV spectral measure (D)

Central asymptotic spectral-density argument; official operator matrix elements.
Decisions: smoothing, off-diagonal basis handling, threshold treatment. Loop:
compare shell sums to short-distance predictions, refine smoothing/thresholds.
Public data: shell-resolved transition strengths. Hidden families: quadratic,
quartic, mixed interactions. Objectives: error, positivity, runtime. Shortcut:
the provided transition blocks make a Schur complement or direct shell sum a
complete solution. Rejected: matrix-algorithm exercise rather than research
ownership; five genuine families do not remove that shortcut.

## 4. Modernize and accelerate the official code (A)

Central workflow and real seven-file workspace. Decisions: orbit versus full
basis, sparse assembly strategy, eigensolver selection. Loop: profile, fix,
benchmark. Public evidence: original executable and tiny matrix tests. Hidden
families: persistence formats, degenerate sectors, sparse large-volume regime.
Objectives: correctness, memory, time. Shortcut: mechanical Python 3 port,
vectorized COO assembly, scipy eigsh. Rejected: complete visible implementation
already reveals the physics; heterogeneous files are not heterogeneous science.

## 5. Resum weak-coupling series into the transition (C)

Perturbative appendix and mass-gap claim. Decisions: resummation family,
large-order constraints, uncertainty model. Loop: calibration, held-out strong
coupling, revision. Public evidence: low-order coefficients and small spectra
subset. Hidden families: vacuum, gap, scattering, backgrounds. Objectives:
accuracy/calibration/runtime. Shortcut: Padé/Borel fitting; more importantly the
paper does not supply enough coefficients or heterogeneous real artifacts.
Rejected: would replace the central workflow with benchmark-authored inference.

Only concept 1 survives the source-level screen. No second concept is built
unless evidence supports a genuinely different workflow rather than mutation.
