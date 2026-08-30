# Trusted evaluator

Active generation: `population-witness-v2-dad`. The only scientific change from
generation one is the endpoint bound `rdm_dad <= 0.001`, computed as
`norm(gamma-gamma.T, 'fro')/sqrt(3)` from the unsymmetrized density. Original
thresholds and the sole population-violation target are unchanged. Current
manifests and audits are under `adversary/generation_2/`; root generation-one
manifests and the generation-one snapshot are historical, not active manifests.

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
45-second worker timeout, a fixed working directory, and single-threaded BLAS.

All physics is recomputed by `hidden/independent.py`, which builds full-Fock-space
fermion operators and uses `scipy.linalg.expm`; it does not import the public
oracle. The private threshold file is an exact frozen copy of the public one.
The submitted stationary root is checked before the independent continuation
certificate is compared. Submitted amplitudes are never silently corrected.

Only `participant/` may be exposed to fresh solvers. This directory includes
private calibration witnesses and must remain outside the participant sandbox.
`--output` is an operator-controlled trusted path, not an artifact-supplied path.
