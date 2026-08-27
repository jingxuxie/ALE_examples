# Private provenance and scope

- Source paper: arXiv:2103.02403v2, downloaded as `source/paper.pdf`.
- Correction: Phys. Rev. Research 6, 049001 (October 16, 2024). Generic
  Gaussian exactness is not valid for noncommuting operator cumulants.
- Official repository: qutech/filter_functions, inspected at
  5f8175f3998f9bfab085cac9946e7796595082e3. The public vendored package is
  the real v1.2.1 snapshot. No fabricated modifications to its numerical
  internals were needed; its later second-order limiting-case fix is
  f24933c306ea7124bfc430cbba9b5655a13daf93.
- Pulse assets are the real X2ID, Y2ID and CNOT MATLAB files. Only controls
  and physical coefficients are publicly extracted; published fidelity
  labels are deliberately omitted. Six-state Hamiltonians follow the
  repository's tests/testutil.py construction, including leakage levels.
- The integration layer, incident narrative, shifted controls/noise laws,
  low-sample diagnostics, hidden experiments and evaluator are benchmark
  authored. They are not misrepresented as historical upstream defects.
- Central technical workflow: full quadratic quantum-process response,
  coherent versus dissipative error, and sequence-level bath memory.
  Central scientific/engineering claim under audit: useful accuracy and
  speed relative to ensemble propagation, with an honest validity domain.
- Public workspace excludes the paper, erratum, bibliography, known-good
  solvers, hidden cases and reference labels. Existing upstream license
  notices are retained. Repository code and pulse names remain visible;
  this is blinding of the paper/solution, not a claim of anonymous authorship.
- Reference: independent moment response plus converged Gaussian quadrature,
  Hermite stochastic-Liouville hierarchy, finite-state switching, and white
  noise propagation. It is checked by 17 tests, finite-amplitude response
  extrapolation, physical invariants, and 13 reference convergence studies.
  Public many-component weak-noise forecasts are also compared against
  higher-hierarchy calculations; their observed relative channel residuals
  are below 2e-7. This validation cost is not charged as participant runtime.
- Five independent physical families are represented by driven static
  noise, finite Gaussian memory, non-Gaussian switching, white noise, and
  the real six-state leakage device. Broadband multiscale noise is retained
  as an additional computational-regime stress test; it is not counted as
  an independent noise law merely because it has more latent components.
- No run time or artifact-completion failure alone is evidence of hardness.
  Core scoring is purely channel/response accuracy with worst-family
  pressure. Runtime and evidence are separate reported dimensions.
