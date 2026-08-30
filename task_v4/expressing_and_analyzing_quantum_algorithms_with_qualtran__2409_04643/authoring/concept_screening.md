# Private hardness-discovery record

Seed: Harrigan et al., *Expressing and Analyzing Quantum Algorithms with
Qualtran*, arXiv:2409.04643v1. Inspection date: 2026-08-28.

## Candidate screening before the first tournament

1. **Resource-aware bloq scheduling (A, selected).** The paper explicitly leaves
   better qubit allocation without full flattening as an open engineering
   direction. Current source uses a stable local net-width priority. Search over
   globally coupled live-register frontiers, unequal internal workspaces and
   operation durations is not a formula implementation or package reproduction.
   Evaluation is exact schedule validation and integer resource accounting.
2. **Numerical GQSP falsification (B, selected).** Independently certify a valid
   signal polynomial or Hamiltonian-simulation approximation, then reproduce a
   substantive numerical failure of the supplied classical preprocessing method.
   This has a strong generation/solution asymmetry: later upstream issues and
   expensive numerical searches are private. Invalid inputs and harmless roundoff
   must not count as witnesses.
3. **Shared nonlinear coherent lookup synthesis (C, selected).** Reconstruct a
   compact multi-output XOR/AND implementation from complete table semantics.
   The challenge is shared nonlinear structure under simultaneous exactness and
   resource constraints, not lookup-table enumeration. Private constructive
   circuits can certify achievability while an independent exhaustive checker
   needs no reference implementation.
4. **Joint lowering and physical-factory provisioning (A, not built).** A previous
   task and passing reference exist in the old task bank. Its previous fresh
   attempt timed out and crashed. It is too close to implementing fully specified
   cost formulas followed by a finite search; extrapolating that old failure to
   a one-hour current-model attempt would not establish new hardness.
5. **Tensor-contraction ordering for arithmetic bloqs (A, not built).** Rich search
   space and exact cost accounting, but a participant could wrap one standard
   tensor-network optimizer. The selected scheduling task targets the explicit
   library-level allocation gap instead.
6. **Symbolic and adjoint resource-accounting repair (F, not built).** Real issues
   involving symbolic calls, caches and signatures are plausible, but recreating
   the package's existing tests or applying known upstream patches risks testing
   package reproduction rather than a difficult substantive capability.
7. **Adaptive robust phase-estimation experiments (E, not built).** Could test
   multimodal posterior control, nuisance noise and query allocation. However,
   calibrating a scientifically meaningful target would require an additional
   simulator study unrelated to the clearest gaps exposed by this paper.
8. **Held-out physical resource prediction (D, not built).** Would require credible
   architecture-dependent ground-truth outcomes unavailable in this repository;
   labels generated from a disclosed analytic model reduce to formulas, whereas
   arbitrary hidden noise would not justify hardness.
9. **Ancilla-constrained reversible arithmetic circuits (C, not built).** Strong
   exact verifier possible, but known adders and modular multipliers often make
   this direct literature reproduction. The selected lookup synthesis removes
   such a direct correspondence while retaining exact coherent-oracle semantics.
10. **Block-encoding normalization counterexamples (B, not built).** Tensor checks
    are reliable at small sizes but trivial padding/type mistakes would be
    shallow. High-degree numerical GQSP has a more substantive stability gap.

## Privilege boundary

Everything under `authoring/`, `evaluator/`, `adversary/`, `champions/`, other
attempts, the official source snapshot, prior submissions and numerical witnesses
is generation-only. Fresh agents receive only their immutable `participant/`
tree and an initially empty output directory. A failed infrastructure probe is
not an agent capability failure. Passing source-native or private witnesses are
not part of the participant assets.

For scheduling, the abstract resource contracts and every workload are public;
the hidden checker independently simulates live edge objects. This is a finite
artifact-improvement task, not an unseen-instance prediction task. A solved
static champion can be adversarially tested across a broad range of register
width/workspace/duration contracts on the same compute graphs. Any ratchet must
publish the changed contracts and baseline and freeze its target before the
next fresh attempt.
