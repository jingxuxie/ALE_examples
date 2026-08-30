# Discovery record

Paper seed: Efficient tensor network simulation of IBM's Eagle kicked Ising
experiment, arXiv:2306.14887v3; PRX Quantum 5, 010308. Discovery date: 2026-08-28.

Eight concepts considered before the tournament:

1. **A: memory-bounded exact heavy-hex contraction planning.** Jointly choose
   indices to slice and a binary contraction tree. Objective is an independently
   checkable arithmetic/storage model, not agreement with a reference solver.
   Selected: many local optima and a genuine time-memory tradeoff beyond BP.
2. **B: false finite-bond convergence in real kicked-Ising dynamics.** Construct
   a bounded pulse schedule for which several MPS estimates agree but an exact
   state-vector computation disagrees. Selected: a scientifically useful
   counterexample to a supplied convergence heuristic, not to the paper itself.
3. **C: calibration-robust many-body state preparation.** Construct a bounded
   kicked-Ising control schedule satisfying independently verified global-state
   fidelity constraints. Selected: coherent nonconvex design across uncertainty.
4. **D: extrapolating finite-chi Eagle observables.** Hold out large-chi values
   from the authors' data. Not selected: the released dataset is small and
   extrapolated labels are not independently exact; leakage is also easy.
5. **E: adaptive calibration of inhomogeneous kicks.** Budgeted noisy quantum
   measurement design. Not selected: substantial simulator/API engineering and
   the risk that the target is limited by identifiability rather than reasoning.
6. **F: robust BP gauge repair.** Repair rank-deficient complex message updates.
   Not selected: could collapse to standard PSD projection/pseudoinverse fixes.
7. **B: BP fixed-point residual as an error certificate.** Search positive
   heavy-hex tensors with converged messages and wrong local marginals. Not
   selected: symmetry-broken ferromagnets give familiar, relatively easy examples.
8. **C: cycle-region diagnostic allocation.** Optimize exact local corrections
   under budgets. Not selected: prior six variants of this paper's task were
   solved at approximately 98--100 points, including complicated diagnostic
   trees; more bookkeeping would not be substantive hardness.

Generation privileges remain outside participant directories. The original
paper, original data, newer libraries and prior submissions were inspected, but
are not copied into the tested agents' allowlists. The three packages are
independent, and no tested agent sees another concept or another submission.

Source inspection:
- https://arxiv.org/html/2306.14887v3 : gate convention, decorated honeycomb,
  uncontrolled loop approximation, finite-chi extrapolation, Appendix A.
- https://github.com/JoeyT1994/BP-TNS-Data : five released Eagle data archives.
- https://github.com/ITensor/ITensorNetworks.jl : original graph-TN implementation.
- https://github.com/JoeyT1994/TensorNetworkQuantumSimulator.jl : follow-up library,
  current examples, loop-expansion references and issue/commit inspection.
- Local previous task, tasks/efficient_tensor_network_simulation_of_ibm_s_eagle_kicked_ising_experi__2306_14887:
  status and successful v_06 solver were inspected; no code copied.

Retention requires empirical failure, evaluator audits and fixed pre-attempt
targets. A missing passing construction is recorded as unknown achievability,
never as evidence that a target is achievable.
