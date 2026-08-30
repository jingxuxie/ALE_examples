# Spectroscopically matched, transport-distinct scattering

Construct two reciprocal, nonnegative, smooth Fermi-surface scattering kernels whose quasiparticle linewidths and transport spectral moments agree, but whose exact linearized-Boltzmann conductivities disagree substantially.

Falsify the supplied moment-closure claim: these matched observables determine the conductivity trace to within a factor of 1.75. This is a benchmark claim under test, not a claim attributed to the EPW authors.

The supplied model fixes a circular Fermi surface, a three-line phonon spectrum, the complete angular degree profile, and the **full 2×2 velocity-projected Dirichlet matrix**. Both kernels must obey the same constraints, including inversion symmetry, finite Fourier bandwidth, and uniform lower and upper scattering bounds. Matching only a scalar transport average is insufficient.

- Read `input/MODEL.md` and `input/model.json` for the complete executable mathematical contract.
- `workspace/model.py` supplies numerical model utilities and a non-authoritative local check.
- `baseline/search.py` writes a valid but weak baseline; it can also run a bounded random search.
- Submit `witness.json` in your output directory. Its two coefficient matrices are the only scored artifact. The evaluator never executes submitted code.
- The fixed goal is a **conductivity-trace ratio of at least 1.75**, with every admissibility and numerical-consistency check passing.
- Design budget: one hour. Witness size: at most 131072 bytes. NumPy and SciPy are available.

This is a reduced, quasielastic electron–phonon transport model, not a first-principles material prediction or an EPW reproduction task.
