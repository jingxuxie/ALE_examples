# Pinned superconducting grains: robust low-energy search

Build a CPU solver that reliably escapes metastable vortex configurations in
pinned and perforated mesoscopic grains. This task uses an explicitly defined,
gauge-covariant finite-lattice, near-`Tc` Ginzburg–Landau model with a prescribed magnetic
field. It is a reduced optimization benchmark, **not** an implementation of or
equivalence claim to SuperConga's self-consistent Eilenberger theory.

## Assets and interface

`input/MODEL.md` defines the energy, boundary conditions, and gradient convention.
`input/API.md` specifies JSON inputs and NPZ outputs. `input/gl_model.py` supplies
energy and analytic gradients. Three development cases are in `input/cases`.
`baseline/solve.py` is a runnable two-start local optimizer; `workspace/solve.py`
is a read-only starter that delegates to it. Write your implementation to the
designated **output artifact directory**, with **`solve.py` at its root**. Do not
modify participant assets. Development baseline and attained witness energies
are published in `input/development_targets.json`.

Run one case per process:

```sh
python OUTPUT_ARTIFACT_DIR/solve.py --input input/cases/dev_pinning.json --output result.npz
```

Return a full-grid complex order parameter `psi` in the NPZ. Submitted energies
are never trusted: the evaluator independently recomputes energy and stationarity.

## Objective and limits

Close the energy gap from the frozen baseline to privately attained lower-energy
**witness fields**, without treating any witness as a true ground state. Six
held-out cases cover strong pinning, multi-hole grains, and high-vortex frustration.
Pass requires mean family gap closure at least **0.65**, worst family at least
**0.45**, no energy regression on any case, valid outputs, and gradient RMS at most
**0.002**. Scores are capped at one; beating a witness is welcome. See
`input/SCORING.md` for exact definitions.

Each case has **60 seconds wall time and CPU time, one CPU core, 2 GiB memory,
256 MiB scratch, and a 4 MiB output limit**. Python standard library, NumPy, and
SciPy only; no GPU, network, external executables, or private evaluator access.
Process startup and input/output count. No state persists between cases. Runtime
score is reported separately and cannot compensate for poor energies.
