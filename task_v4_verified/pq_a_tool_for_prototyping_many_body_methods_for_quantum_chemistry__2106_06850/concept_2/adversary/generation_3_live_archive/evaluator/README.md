# Trusted evaluator

Active generation: `population-witness-v3-robust`, ratchet two. All generation-two
physics gates and the population-violation target now apply at the base and 240
public integral perturbations: both signs of all Frobenius-normalized symmetric
15-by-15 coordinate axes, radius 0.001. Current manifests and audits are under
`adversary/generation_3/`; earlier manifests and snapshots are historical.

`hidden/robust.py` independently constructs the fixed stencil, checks domain
membership without projection, solves neighboring roots from the submitted base
root, and requests every original endpoint and 64-step path check. All 241 paths
are required for a positive score. The score is the minimum population violation.
Endpoint failures may short-circuit path work but cannot earn positive credit.

```
python -I evaluator/evaluate.py /absolute/attempt/submission.json \
  --submission-dir /absolute/attempt --output /trusted/report.json
```

Pass the actual allowed submission directory explicitly when orchestrating a
participant run. An artifact outside that lexical directory is rejected. Without
the option, the literal artifact parent is the declared submission directory.
The evaluator never resolves an untrusted symlink to a target before validation:
every directory component and the final file are opened with `O_NOFOLLOW` using
directory file descriptors. Symlinks in any component, including dangling links
to private witness paths, are rejected. The file must be regular and is read from
the validated descriptor, capped at 65537 bytes to detect oversize input.

The parser rejects duplicate keys, nonfinite values, numeric strings, booleans,
unknown/missing keys, invalid shape/version, invalid UTF-8, and out-of-domain
parameters. Malformed artifacts produce JSON failure reports with score zero.
No participant code, pickle, imported artifact module, or external solver runs.
The parent launches only this trusted script in Python isolated mode, with a
900-second worker timeout, a fixed working directory, and single-threaded BLAS.

All physics is recomputed by `hidden/independent.py`, which builds full-Fock-space
fermion operators and uses `scipy.linalg.expm`; it does not import the public
oracle. The private threshold file is an exact frozen copy of the public one.
The submitted stationary root is checked before the independent continuation
certificate is compared. Submitted amplitudes are never silently corrected.

Only `participant/` may be exposed to fresh solvers. This directory includes
private calibration witnesses and must remain outside the participant sandbox.
`--output` is an operator-controlled trusted path, not an artifact-supplied path.
