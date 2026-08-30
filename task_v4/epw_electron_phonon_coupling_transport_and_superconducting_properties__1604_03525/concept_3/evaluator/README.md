# Trusted evaluator

Run `python3 evaluator/evaluate.py --submission DIR --output result.json` from the concept root. Only `DIR/witness.json` is opened. Candidate Python, imports, pickle, claimed scores, paths in JSON, and submitted executable helpers are never used. Trusted numerical code is entirely under `evaluator/hidden`, not imported from the participant tree.

The target is frozen at trace ratio 1.75. Continuum positivity uses a second-derivative interpolation enclosure. Degree, full Dirichlet, spectral-moment, symmetry, null-mode, and residual checks are separately computed from dense sampled kernels. The last refinement is shifted to provide an additional independent quadrature check. The finite Fourier solve provides an exact continuum result for this particular constant-degree reduced model, not a reference optimizer.

Use `python3 -m unittest discover -s evaluator -p 'test_*.py'` for numerical and malformed-artifact regression tests. A valid baseline below the target is expected, not a failed evaluator.

Do not expose `adversary/` or `evaluator/` to fresh agents. Give them only `participant/` and their writable attempt directory. No fresh agent is launched by this package.
