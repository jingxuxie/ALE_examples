# Scientific motivation and scope

The motivating paper is P. Holmvall et al., *SuperConga: an open-source framework
for mesoscopic superconductivity*, arXiv:2205.15000, subsequently Applied Physics
Reviews 10, 011317 (2023). Its mesoscopic vortex examples exhibit competing
metastable vortex configurations and free-energy comparisons. The official
SuperConga documentation's “About” page identifies robustness in high-dimensional
spaces with many minima and metastable states as a central challenge.

References checked during benchmark authoring:

- https://arxiv.org/abs/2205.15000
- https://superconga.gitlab.io/superconga-doc/about.html
- https://superconga.gitlab.io/superconga-doc/guides/abrikosov-vortex-core.html
- The supplied SuperConga source's `include/conga/order_parameter/OrderParameterInitial.h`
  supports vortex phase-winding initial guesses; `tools/vortex_adder.py` provides
  vortex insertion. Its `CHANGELOG.md` records normal inclusions, including metallic
  vortex-pinning sites.

This benchmark borrows the **optimization challenge**, not the microscopic solver
or its physical predictions. The source uses quasiclassical Eilenberger theory;
our independently implemented single-component GL reduction is appropriate as a
near-`Tc` phenomenological model. Positive-alpha patches are its analog of locally
suppressed superconductivity; removed sites are vacuum perforations, not metallic
inclusions. Links come from a prescribed physical vector potential and all
stiffnesses are positive. Magnetic screening is deliberately absent. The exact
finite-lattice energy is authoritative; no mesh-converged continuum accuracy,
true ground state, or equivalence to SuperConga is claimed.
