# Frozen-solver physical counterexample search

Only this directory is writable. The completed solver, pilot cases, reference,
and evaluator remain unchanged. No existing initial/challenge runs are repeated.
No model agents are launched. All candidate cases keep N=2048 and the exact
published Hamiltonian, directional ensemble, output angles, and evaluator score.

## Structural risks being tested, not presumed failures

The submission's `sampler.cpp:249` makes globally projected exchange-equilibrium
proposals and accepts them using the extensive anisotropy-energy difference.
`sampler.cpp:315` carries one chain forward through fifteen angular windows;
there are no independent production restarts or angular replica exchanges.
`reweight.py:25` solves MBAR, but no overlap-matrix connectivity or minimum target
effective-sample-size gate controls acceptance of the resulting predictions.

1. Compensated surface/bulk anisotropy: easy-z bulk K=.10 and easy-plane surface
   K=.40 cancel under uniform rotation for an eight-layer slab. Surface canting
   and thermal renormalization remain physical, and can expose correlated
   global-proposal rejection rather than a mere change of signal magnitude.
2. Bulk two-ion/easy-plane competition: b=.12 on nearest-neighbor bonds competes
   with onsite easy-plane K=.24 at T=1.12. This is the existing Hamiltonian, not a
   new ensemble, and probes angle-dependent moment suppression and hard-axis
   free-energy flattening rather than a single-harmonic fit.
3. Weak exchange-spring interface: orthogonal layer easy axes K=.18, interface
   J=.18, upper-layer J=.65 and interface b=.10 at T=.65. Local canting/domain
   states test angular continuation and sampling overlap across an inhomogeneous
   film. No claim of metastability or of solver failure is made without data.
4. Single-/two-ion compensation: b=.25 and Qxx=Qyy=b*coordination/2 at T=1.05.
   The anisotropy equals a constant plus (b/2) sum_bonds (s_iz-s_jz)^2.
   Uniform zero-temperature rotation is degenerate, while thermal gradients
   can retain directional free energy. These are stress-model parameters,
   not the weak-anisotropy material parameters in the source study.

## Primary sources and locations

- Asselin et al., https://arxiv.org/pdf/1006.3507 : Eq. (1), Sec. IV pp. 7–9
  (strong-anisotropy/non-sinusoidal torque), Sec. V Eq. (3) and Fig. 3 pp. 9–10
  (competing two-ion anisotropy and hard-axis moment suppression), Sec. VI
  (surface/bulk competition). These are generic model units, not a fit to FePt.
- Exchange-spring primary study:
  https://www.nature.com/articles/ncomms11931 , Results: competing anisotropy,
  interfacial coupling, and spatial magnetization profiles.
- MBAR primary error analysis:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC10845960/ , Sec. II, Eqs. (21)–(24),
  discusses overlap/irreducibility and slow sampling modes. Numerical convergence
  of the MBAR equations alone is not evidence of thermodynamic convergence.
- Evans et al., https://arxiv.org/pdf/2002.02548 : Eqs. (1), (5), (10), (11)
  and p. 3, discussion following Fig. 2. Opposite single-/two-ion terms can
  cancel at zero temperature without canceling finite-temperature anisotropy.

## Reference and acceptance policy

Use byte-identical copies of the frozen official CMC source. The wrapper changes
only initial configurations and adds layer/surface magnetization diagnostics.
Starts include aligned, hot, and transverse x/z domains; all preserve the same
global directional constraint. An initial five-angle, four-chain scout checks
whether a longer reference is plausible. Final references, if pursued, use
independent long chains, a refined 33-angle integration, reflection tests, and
separate doubled-burn strong trajectories. No region is accepted as a
counterexample unless its large-system reference demonstrably converges and
the independent strong score exceeds .9 under the unmodified scoring rule.
An unconverged reference is a rejected candidate, not evidence against the solver.

`inspection.json` reports metadata-stripped duplication and snapshots available
main scores. `manifest.json` freezes these new candidates before running them.
All source copies, inputs, raw trajectories, sandbox outputs, and rejection
reasons are retained here.
