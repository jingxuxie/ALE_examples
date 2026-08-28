# Pre-build rejection audit

Status: `rejected`

Reason: `no_frontier_hard_workflow_found`

This is the Phase 1 stop condition, not an empirical finding that a particular
frontier model passed or failed a task. Five concepts were screened; zero were
built. There was no redesign, reference evaluation, participant directory, or
fresh-agent session. In particular, the small numerical probe is not an
`ultima-alpha` attempt, a scored reference, or an accepted participant task.

## Substantive shortcut check

`shortcut_probe.py` is a private feasibility probe of the strongest numerical
candidate. It builds physical spin Hamiltonians, uses the same ordinary SciPy
interior eigensolver for all instances, and evaluates the paper's eigenstate
observables with standard probability and tensor operations. It does not use
synthetic scaling labels, hidden parameter vectors, fitted target outputs, or
the original paper's reported numbers as an oracle.

The probe completed 21 configurations in 16.07 seconds in the recorded run:
periodic iid chains, open chains, complex flux rings, quasiperiodic rings, and
two-leg ladders, at sizes 8, 12 and 14, plus weak/strong disorder and off-center
energy targets in the original chain. The five geometry/disorder variants are
tests of shortcut portability, not a claim that these are five datasets from
the original paper. Changing the Hamiltonian construction did not require a
different eigensolver or observable algorithm.

Largest relative eigenpair residual: `1.2861801139731945e-13`.
Largest orthogonality error: `1.0694581596118034e-13`.
Largest independent dense-solver eigenvalue discrepancy at size 8:
`4.6629367034256575e-15`.
An additional four-spin zero-field analytic-spectrum check and Hermiticity
checks for all five physical variants passed. The script and numerical CSV are
preserved so these observations are inspectable.

These measurements do **not** show a mobility edge, certify a thermodynamic
phase, establish the original paper's exponents, or measure frontier-agent
performance. One realization per configuration is insufficient for those
claims. They show why a bounded numerical-repair task built mostly out of these
components would have a credible, reusable standard-method shortcut.

## Why not build a more elaborate version?

- Adding files, figures, or output tables would not remove that shortcut.
- The paper's fitting recipe leads to conventional polynomial collapse and
  resampling. Generating fake collapse data would violate the central-workflow
  requirement. Scoring an unidentifiable asymptotic extrapolation against one
  author's preferred fit would not be method-agnostic scientific evaluation.
- Authentic production-scale sparse factorization and disorder sampling are
  substantial work. They were not tested by this probe. Raising system size or
  reducing a runtime allowance would not, by itself, establish capability-based
  hardness, and the available artifact did not expose a concrete performance
  failure to turn into a fair pilot.
- A reconstructed restart/ETL scenario would be plausible, but the easiest
  valid answer for bounded instances is to recompute the spectra. Artificially
  prohibiting that method or manufacturing many special export errors would
  not satisfy the stated gates.
- No inspected source supplies a full sample-level dataset with an existing
  scientific regression, missing acquisition component, or nontrivial transfer
  failure that survives these shortcuts.

This rejects the five formulated concepts, not the scientific importance or
intrinsic difficulty of many-body-localization research. A different available
artifact or a demonstrated performance regression could change the assessment.
Under the current inputs, no participant task is represented as frontier-hard.

## Reproduction

From the ALE root:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
python tasks_v2/many_body_localization_edge_in_the_random_field_heisenberg_chain__1411_0660/private/shortcut_probe.py \
  --output /tmp/mbl_shortcut_probe
```

Original observations are in `shortcut_probe_results/probe.csv` and
`shortcut_probe_results/summary.json`. Timing is environment-dependent, and
process maximum RSS is cumulative within the run, not per-case incremental
memory. No participant score should be inferred from these records.
