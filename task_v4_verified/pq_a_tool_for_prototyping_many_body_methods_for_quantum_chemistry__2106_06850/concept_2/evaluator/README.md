# Trusted evaluator

Generation: `population-witness-v4-adaptive`, final ratchet three. All original
physics gates and the population-violation target apply at 243 labeled points:
the unchanged 241 coordinate points and two normalized base signed-energy-error
gradient probes. Every displacement retains Frobenius radius 0.001. This staging
packet does not replace the active generation until the main worker installs it.

`hidden/robust.py` independently constructs the fixed stencil, checks domain
membership without projection, solves neighboring roots from the submitted base
root, and requests every original endpoint and 64-step path check. All 243 paths
are required for a positive score. The score is the minimum population violation.
Endpoint failures may short-circuit path work but cannot earn positive credit.

`hidden/adaptive_response.py` independently computes the stationary CC Lagrangian
derivative minus the exact Hellmann-Feynman derivative in all 120 orthonormal
coordinates, including the one-body counterterm. Both finite probes are recomputed
from the base root; neither a submitted direction nor a linear derivative bound
can substitute for a neighboring-root certificate. A norm at most 1e-12 selects
the first diagonal coordinate as a deterministic fallback. This is a finite
test, not a theorem about a continuum ball. The public helper is never imported.

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

Only `participant/` may be exposed to fresh solvers. The evaluator and sibling
`authoring/` directory must remain outside the participant sandbox.
`--output` is an operator-controlled trusted path, not an artifact-supplied path.
