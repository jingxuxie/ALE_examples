# False convergence under an operational exploration floor

Construct a finite, exactly verifiable counterexample to the sufficiency of
small variational optimization diagnostics for equilibrium sector coverage.
Your autoregressive distribution must be symmetric and assign every binary
conditional outcome probability at least 0.001. This is a mode-B witness
construction mission.

Submit `witness.json` in your output directory. Choose 32 binary bonds on a
4-by-4 periodic square lattice, inverse temperature, spin order, strictly lower
triangular logistic weights, and an antipodal Hamming sector. The complete JSON
schema and exact definitions are in `workspace/SCHEMA.md` and `workspace/MATH.md`;
frozen targets are in `input/spec.json`.

All requirements must hold simultaneously under exhaustive enumeration of all
65,536 spin configurations:

- Bonds are +/-1; 4 through 12 elementary plaquettes are frustrated; beta is in [1,3].
- Every weight-row L1 norm is at most log(999); there are no biases.
- Entropy is at least 3 nats and reverse KL is at least 0.4 nats.
- Total dimensionless reward variance is at most 0.05.
- Exact gradient infinity norm is at most 0.003.
- Mean dimensionless energy error per spin is at most 0.02.
- The submitted antipodal sector has radius 2, 3, or 4, target mass at least
  0.35, and proposal mass at most 0.001.

You have one 60-minute coding attempt. The runner supplies up to four CPU cores,
an 8-GiB per-process address-space limit, and no GPU or network. The evaluator
reads JSON only and executes no submitted code; its separate limits and numerical
comparison tolerances are specified in `input/spec.json` and `workspace/MATH.md`.
Run `python -B baseline/run.py --output OUTPUT_DIRECTORY` to emit the supplied
structurally valid but failing baseline. Structural validity is not success.
This is an open construction challenge; no passing witness is promised.
