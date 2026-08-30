# Full-support false convergence on a frustrated Ising torus

Construct one witness demonstrating that a symmetric, full-support, shallow
autoregressive distribution can have small exact variational diagnostics while
missing an important equilibrium sector. This is a witness-construction mission
(mode B), not a request to implement or repair a sampler.

Submit `witness.json` in your output directory. Choose the 32 binary bonds of a
4-by-4 periodic square lattice, inverse temperature, spin order, strictly lower
triangular logistic weights, and an antipodal Hamming sector. The complete JSON
interface and mathematical conventions are in `workspace/SCHEMA.md` and
`workspace/MATH.md`; the frozen numerical specification is `input/spec.json`.

All conditions must hold simultaneously under exhaustive enumeration of all
65,536 states:

- Bonds are +/-1; 4 through 12 elementary plaquettes are frustrated; beta is in [1,3].
- Every weight-row L1 norm is at most log(9999); there are no biases.
- Entropy is at least 3 nats and reverse KL is at least 0.4 nats.
- Total dimensionless reward variance is at most 0.05.
- The exact gradient infinity norm is at most 0.003.
- Mean dimensionless energy error per spin is at most 0.02.
- For a submitted antipodal sector of radius 2, 3, or 4, target probability is at
  least 0.35 and proposal probability is at most 0.001.

You have one 60-minute coding attempt using the CPUs, memory, and installed
software exposed by the runner. The evaluator reads JSON only and executes no
submitted code. Its numerical tolerance, size limits, score, and resource limits
are specified in `input/spec.json` and `workspace/MATH.md`. A structurally valid
witness is not necessarily a passing witness. `python -B workspace/baseline.py
--output OUTPUT_DIRECTORY` creates a runnable, admissible but failing baseline.
No passing witness is promised.
