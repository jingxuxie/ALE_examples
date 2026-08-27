# Pilot evaluator and reference validity

The participant is an anonymized, benchmark-authored extraction and extension
of a real finite-volume Hamiltonian-truncation workflow. The private source
archive contains the official seven-file ancillary implementation. Public
matrices are actual oscillator matrix elements, not fabricated spectra. The
paper, counterterm implementation, targets, and high-cutoff matrices are not
inside the participant allowlist.

## Five independent families

The hidden campaign contains one new instance each of a Gaussian field,
homogeneous periodic quartic field, antiperiodic quartic field, parity-broken
source-deformed quartic field, and spatially modulated field. These change the
physical model, mode geometry, conserved quantities and operator content.
Additional cutoff rows are convergence experiments, not counted as families.

## Numerical oracle and uncertainty

Gaussian energies are exact in the stated infinite-line normal-ordering
convention. Interacting targets use a substantially larger free-energy
projection (28 rather than the available 16), with analytic UV improvement.
The target uncertainty is the difference between improved cutoffs 26 and 28,
plus one quarter of the local/nonlocal difference at 28, plus 1e-4. This is a
conservative numerical screening envelope, not a rigorous continuum error
bound. Low-cutoff reference errors are evaluated against this independently
computed higher-cutoff target, not asserted to be zero.

`private/official_crosscheck.json` verifies all V0/V2/V4 matrix elements in two
small sectors against the original code after reflection projection; maximum
disagreement is below 1e-14. Separate tests cover zero-mode combinatorics,
antiperiodic momentum and Fourier-transfer adjoints. The accuracy audit shows
how much of the raw spectral error remains after the reference repair. A
reference must improve every family and pass isolated replay before an agent
is launched. The source-broken and inhomogeneous branches are explicitly new
extensions, not claims that the original authors studied those cases.

## Continuous core score

Each case/cutoff yields the common vacuum and every requested gap, retaining
multiplicities. Loss is the mean absolute error outside the numerical oracle
envelope. A row's accuracy score is

    clip(0.97 * (raw_loss - submission_loss) /
                   (raw_loss - strong_reference_loss), 0, 1).

The strong reference scores 0.97, not a modest pass threshold; a genuinely
better answer may score higher. A raw eigensolve scores zero. Scores are
averaged across cutoffs within each family. Core score is 65% mean-family and
35% worst-family accuracy. No report/figure penalty enters the core score.

The overall score is 85% core, 10% evidence consistency, and 5% measured
resource score. The latter decreases continuously with wall time and actual
child-process peak RSS. Replay has a 1.5-GiB address-space limit and a
five-minute safety limit. The reference finishes in seconds, not near the
limit. Evidence checks independently replay both spectrum tables, distinguish
ablation configurations, recompute row-linked claims, and verify figure source
data. The report receives a separate human/agent scientific review; its mere
existence is not proof of a valid conclusion.

The executable runs in a new bubblewrap mount namespace with only system
libraries, the submission, an input projection, and its output. Neither the
hidden target file nor the reference workspace is mounted. No network is
mounted. The fresh research agent uses the separately supplied allowlisted
Codex launcher, exact requested model and a new session.

## Hardness interpretation (frozen before screening)

The requested score bands are applied to the core score. A sub-0.60 result is
not sufficient by itself: inspect the transcript for broken infrastructure,
missing conventions, near-complete correct methods, and merely clerical
failure. In particular, failure only on the easily solved Gaussian control
does not establish frontier-hard interacting-field research. A retained task
must show substantive scientific failure in the interacting/shifted branches.
Do not tighten thresholds, add edge cases or change targets after observing
an easy attempt. A moderate result may be rejected without spending the one
permitted fundamental redesign.
