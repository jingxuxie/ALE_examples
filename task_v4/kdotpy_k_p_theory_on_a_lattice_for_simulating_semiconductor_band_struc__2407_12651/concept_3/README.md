# Concept 3: generation 2, four-band remote-mixing witness task

Generation 1 is preserved under the parent author's generation snapshots and
its frozen champion remains in champions/generation_1. Generation 2 keeps all
thresholds, 30 controls, and the eight-channel budget, but includes two fixed
C4-compatible remote orbitals above the active bands. No author-launched agents.
Until a pass is independently scored, generation 2 is a hard_open_candidate.

Expose ONLY `participant/` to scientific agents. All other directories contain
private evaluators, authoring witnesses, controls, and logs. No agents were launched.

Run from this concept directory:

```
python participant/baseline/design.py --output attempts/baseline/witness.json
python evaluator/evaluate.py --candidate attempts/baseline/witness.json --output attempts/baseline/result.json
python evaluator/evaluate.py --submission-dir /path/to/agent/output --output /path/to/result.json
python evaluator/test_validation.py
```

The submission directory must contain `witness.json`; no submitted code is run.
The public target is fixed before the saved fresh baseline/private evaluations.
`evaluator/hidden/freeze.json` hashes the full scientific contract and evaluator.
The generation-1 authoring witness is `attempts/topological_search/trial_7.json`;
it is not a generation-2 pass. Current frozen reports are under
`attempts/generation_2/`. Probe and compensation evidence is under
`adversary/remote_band_probe/`. Status and scores are in `status.json`.

This is an independently implemented sparse Fourier/BHZ spin-block surrogate,
not calibrated HgTe and not copied kdotpy. Nonlinear robust optimization and
support selection are required; guaranteed one-hour hardness has NOT been tested.
Any later champion ratchet must create a separately versioned public challenge.

Primary sources: https://arxiv.org/html/2407.12651v1 sections 2.8.1, 3.5.3, 3.9.4;
https://arxiv.org/pdf/cond-mat/0503172 (lattice topology and patching);
https://arxiv.org/abs/1311.4956 (finite-range exact-flatness obstruction).

The checker certifies the full public uncertainty box with explicit continuum
and homotopy bounds, cross-checks FHS against spherical degree, and independently
assembles full matrix spectra. Float64 safety padding is documented; this is not
formal interval arithmetic. Private stress points add no hidden restrictions.
