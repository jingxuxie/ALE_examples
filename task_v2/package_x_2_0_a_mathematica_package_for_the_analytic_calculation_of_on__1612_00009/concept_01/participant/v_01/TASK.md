# Release decision: one-loop matching and subtraction engine

You own the release of a portable one-loop coefficient service used for both
real-kinematics amplitudes and low-energy matching. A scalar-only smoke test
passed, but the attached acceptance campaign does not produce a trustworthy
release decision. Investigate the disagreement, repair or replace the numerical
and analytic stages that need it, and determine what the evidence supports.

This is not a request to reproduce a table or implement a prescribed reduction
formula. Different scientifically valid methods are welcome. The release must
handle weighted and tensor coefficients, local multivariate coefficients,
dimensional factors, and infrared subtractions together. Correct generic scalar
answers with incorrect poles, branch signs, or local coefficients do not solve
the release problem.

## Handoff

- `input/CONVENTIONS.md` is the complete scientific and I/O convention.
- `input/release.json` is the unlabeled public acceptance campaign.
- `input/MIGRATION.md` describes the observed migration symptoms and scope.
- `workspace/loopaudit/` contains interacting kinematics, cache, quadrature,
  regularization, local-expansion, observable-assembly, and service modules.
- `workspace/profiles.json` exposes the current numerical controls.
- `workspace/tests/` contains two very small exact normalization checks.
- `workspace/experiments.py` and `workspace/diagnose.py` run and inspect the
  campaign without providing its expected values. A dependency-free plotting
  helper is included; aesthetics are not evaluated.

Treat this participant folder as read-only. Work in the empty output directory
specified by the launch prompt. Python 3, NumPy, SciPy, SymPy, mpmath, a C/C++
compiler, and a Fortran compiler are installed. All required Python modules are
in system directories. No internet, proprietary CAS, external loop library,
or additional downloads are needed. You may use any installed tools and may
replace the starter architecture. The system must run on one CPU with at most
1 GiB resident memory; set numerical library thread counts accordingly.

## Required investigation

1. Run the inherited campaign and inspect its evidence before changing the
   implementation. Separate failures of scientific convention from failures of
   numerical convergence. Record a baseline that can be checked.
2. Make and test the consequential numerical/analytic design choices needed for
   a reliable release. Use the small exact tests, parameter symmetries where
   applicable, dimensional identities, scale covariance, and refinement studies
   as evidence. They are complementary checks, not a complete correctness oracle.
3. Run a meaningful design ablation and a work/accuracy study. At least two
   genuinely distinct configurations must be executable; changing only names
   or duplicating the same results is not an ablation. Show why your final
   choice is appropriate, including limitations where the evidence warrants them.
4. Produce the executable system and the evidence-supported release assessment.
   Do not claim convergence solely from an internal error estimate.

## Executable handoff

Place these directly under the supplied output directory:

```
workspace/                 self-contained repaired system and profiles.json
run.sh                     portable entry point
results.csv                production campaign coefficients and diagnostics
ablation.csv               same measurements for at least two distinct profiles
scaling.csv                work/time/refinement measurements
figures/primary_result.png
figures/robustness_or_scaling.png
claims.json                quantitative comparisons tied to table rows
report.md                  diagnosis, experiments, decision, limitations
baseline/                  measured unmodified campaign and diagnosis
```

The rerun interface is:

```
bash OUTPUT/run.sh --requests REQUESTS.json --output PREDICTIONS.json --profile production
```

The JSON schema is demonstrated by the starter service. Every requested
integral and local coefficient must have all four complex Laurent channels as
`[real, imaginary]`, as well as measured `seconds`, `work`, `estimated_error`,
and a descriptive `strategy`. Observables use the same four channels. It is
fine to change the internal representation. Production must accept previously
unseen requests in the documented domain and may not depend on request IDs.

The supplied experiment driver defines table columns and a simple quantitative
claim schema. You may extend these but retain its columns. Each figure must have
its source CSV saved alongside it. Include the executable configurations used
in every submitted table. Tables, claims, and configuration ablations are rerun
and checked, not graded for their appearance.

## Release criteria

Scientific accuracy and worst-family robustness dominate. Eight to nine correct
relative digits are substantially better than four to five; small residuals
alone are not sufficient if constituent terms are wrong. Runtime/work also
matter: a universal expensive path may be less useful than a justified policy.
Hidden evaluation uses the stated physical/topological regimes, not just larger
instances of a single spacelike generator. A hidden campaign has a generous
240-second execution ceiling; accuracy is scored continuously, and near-reference
speed earns more credit than merely finishing under the ceiling. Report honest
limitations rather than hiding failures behind zeroes or catch-all exceptions.

Do not spend the investigation on clerical presentation. The decisive evidence
is the repaired executable behavior and a real run--inspect--revise--rerun loop.
