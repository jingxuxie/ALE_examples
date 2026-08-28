# Construction and evidence

This pilot instantiates inventory A/F using the two defects that coexist in
the authentic 2026-03-11 source revision immediately before the density sign
fix. `build.py` extracts the complete historical RK4 solver/support modules
and verbatim `ContFlowRK4` and `SpectrumScaling` classes. It alters imports
only to exclude unrelated modules. No artificial arithmetic defect, removed
dependency, stubbed scientific method, or participant-visible fixed source is
introduced. Exact revisions and content hashes are in `provenance.json`.

The private reference uses the same extraction from the inspected official
2026-08-23 HEAD. Reference outputs are generated with four times the specified
steps. Calibration runs the actual historical and official implementations
at the same requested step count, not a fabricated zero-answer baseline.
`evidence.json` records family scores, errors through the calibration files,
and wall times. `reference_validation.json` records a closed-form spectral/
linear-flow check and finite differences of a nonlinear inverse composition.

Scores are continuous rational functions of normalized numerical error,
calibrated separately for primal, endpoint-time, parameter, input-gradient,
density, inverse, and acceptance families. There is no all-or-nothing numeric
tolerance score. Uniform positive spectral scaling gives one real degree of
freedom for DC/Nyquist and two for the other 1D rFFT modes. The sampler trace
adds nonlinear proposal-density composition and retained-rejection behavior;
a fixed density offset can still cancel from acceptance, so absolute density
is separately scored. The acceptance implementation itself is not seeded with
an invented bug.

The March density fix and August duration fix are individually small. This
minimal pilot does not prove frontier difficulty, enforce adjoint memory
scaling, or prohibit differentiating through integration steps. The completed
fresh pilot and challenge results are in `initial_report.json` and
`challenge_report.json`; both are solved. The immutable pre-attempt source is preserved in
`baselines/weak`, separately from participant workspace and reference code.
The main session supplies the dependency-only runtime. Default evaluation
uses bwrap with read-only `/task` (participant tree) and `/submission`, staged
request/output files under writable `/work`, system libraries, isolated
proc/dev/tmp, an empty initial environment, and a four-CPU affinity limit.
The same public directory roots are additionally mounted read-only at their
original absolute paths, including `/home` and `/srv/home` aliases. Only the
public roots themselves are mounted; their parents and private siblings are
not exposed. This preserves absolute public helper/input references from an
attempt without granting access to grading artifacts.
Private references and calibration files are not mounted. Execute the outer
evaluator outside a parent sandbox that blocks bwrap namespace setup.
`--trusted-reference` permits direct execution only of the preserved private
reference implementation or weak baseline; `build.py` uses that explicit
trusted path to regenerate outputs. No participant submission bypasses
isolation by default, and missing bwrap fails closed.

Regenerate with the supplied Python and `build.py --source /tmp/ale_bijx`.
`--scaffold-only` writes snapshots and inputs without numerical evaluation.
Regeneration refuses to overwrite a participant workspace whose recorded
initial files have changed. It never writes outside this pilot directory or
touches an attempt. Evaluate with
`private/evaluator.py --submission DIR --report PATH [--pool challenge]`.
