# concept_3: spectral-center proxy falsification

Mode **B COUNTEREXAMPLE/FALSIFICATION**, seeded by Pal–Huse arXiv:1010.1992.
The proxy claim is task-authored, not attributed to the seed paper. The
participant produces a twelve-field static JSON witness. The evaluator
recomputes the entire zero-magnetization spectrum for the base and all 32
public perturbations. This task does not use the dynamical fraction `f` or
histogram-preserving permutations.

## Runner contract

- Expose **only `participant/`** to a fresh participant session.
- Keep `evaluator/` trusted and read-only; do not expose `adversary/` or
  author witness artifacts to participants.
- Use `python -I -B evaluator/evaluate.py /absolute/path/witness.json --output /absolute/path/report.json`.
- The evaluator reads only JSON, never calls a participant solver, and
  reports `core`, `worst_family`, `resource`, `pass`, `valid`, and `reason`.
- `attempts/` and `champions/` are reserved for fresh main-runner sessions.
  Author pilots, baselines, audits, and witnesses live under `adversary/`.
- The main-runner participant search allowance is 3,600 seconds, up to
  eight generator workers, one BLAS thread each. No agents were launched
  by this authoring run.

## Freeze and validation

`status.json` records readiness, the fixed targets, existing validation, and
baseline/privileged feasibility evidence. The main runner owns the final
freeze and launch. No primary target, offset, or admissibility changes were
made during the final documentation and report-alias edits. Once the main
runner freezes this package, do not change participant or evaluator files
during the independent attempts. The CLI uses a positional witness file,
not a submission directory.

The author witness and its reproducible evaluation are in
`adversary/champions/`. `adversary/validation.json` records 40 malformed-input
controls, exact repeated scores, and numerical cross-checks. The final
documentation and report aliases were not revalidated, as explicitly
requested. `adversary/REPORT.md` explains search provenance and limitations.
No fresh-agent success rate or difficulty conclusion is claimed before the
main runner's independent sessions.
