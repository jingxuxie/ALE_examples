# Private concept selection

Seed: Rubin and DePrince, arXiv:2106.06850, especially Sections II.B, II.C, III and the RDM appendices. Follow-up: arXiv:2501.08882, especially unitary cluster operators and graph optimization. Official source pinned to `843b11aad9cbea253b233c2fcdb7049c1fec7266` (2026-08-27).

Eight concepts considered before the tournament:

1. **A: Joint contraction planning under a scratch-memory cap. Selected.** Source-native CC/response/RDM contraction batches; exact algebraic certificates, dimension-dependent costs, cross-term reuse, and liveness/recomputation interact. Per-term optimal planning is provided, so implementing that standard algorithm is insufficient.
2. **B: Falsify a constrained CCSD reliability screen. Selected.** A stationary, ground-related CCSD solution must pass useful physical diagnostics but fail an RDM/response property. A determinant-space oracle makes the physical claims reproducible without a reference witness.
3. **C: Compact fermionic excitation-circuit synthesis. Selected.** Invert noncommuting disentangled UCC state preparations with a strict excitation count. Hidden planted circuits certify achievability; complete target states prevent hidden-information impossibility.
4. **F: Repair the native graph optimizer across fusion, aliasing, and printing. Rejected.** The official issue tracker and recent fixes make direct patch reconstruction too plausible; file count is not difficulty.
5. **D: Predict CCSD breakdown from low-cost integral diagnostics. Rejected.** Dataset construction and conditional irreducible error would dominate interpretation of one-agent hardness.
6. **E: Query-budget Hamiltonian tomography from determinant energies. Rejected.** For a fixed two-body operator basis this collapses to a standard linear design/regression problem.
7. **C: Construct a PQG-positive but higher-order-infeasible RDM. Rejected.** In a straightforward formulation a single standard semidefinite optimization suffices.
8. **B: Find a numerical disagreement between generated and unoptimized kernels. Rejected.** This risks testing memorized source defects or mere fuzzing rather than a difficult scientific capability.

The three selected concepts are built once. Source, generation seeds, exact certificates, hidden distributions, evaluations and other agents' submissions stay outside participant directories. No private artifact may be used by a fresh session. A solved concept is retained for a champion/challenger ratchet, at most three champion generations.

The source inspection included the repository's current README, graph README, development guide, generated full-CC examples, and public optimizer issues #115 and #118. The latter motivate the resource-aware global objective, not an implementation to copy. The API issue archive request returned HTTP 403; no contents from that request are claimed. Prior unrelated task launchers were inspected only to validate local runner invocation; no previous pdaggerq submission was available.
