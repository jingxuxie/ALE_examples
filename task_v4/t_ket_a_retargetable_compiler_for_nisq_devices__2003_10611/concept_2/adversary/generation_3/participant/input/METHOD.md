# Supplied method and scope

Primary sources:

- Sivarajah et al., *t|ket>: A Retargetable Compiler for NISQ Devices*,
  arXiv:2003.10611v3, section 7, especially 7.2.
  https://arxiv.org/html/2003.10611v3#S7.SS2
- Cowtan et al., *On the qubit routing problem*, arXiv:1902.08091v2,
  section III.3 and Appendix A. This routing paper predates the compiler paper.
  https://arxiv.org/html/1902.08091v2#S3.SS3

The papers motivate dynamic distance-based routing, finite lookahead, and
shortest-path progress. They do not establish the approximation guarantee being
falsified here. The benchmark is a transparent SWAP-only adaptation and portfolio
extension, not a bit-for-bit implementation of either paper or current tket.

## Distance-based policies

Drain all ready adjacent gates using the true per-wire dependency DAG. Build
future layers after deleting executed gates. Consider hardware edges incident to
ready-gate operands, score each resulting placement by average excess graph
distance in each layer, and combine those values geometrically or lexicographically.
Resolve ties by the specified edge ordering. Do not revisit a placement without
executing a gate. After 32 nonexecuting SWAPs, or when no unvisited candidate remains,
shortest-path route a closest ready pair and execute it. This guarantees progress.

In addition to the retained local and long-horizon settings, future-emphasis
settings use positive factors greater than one. They prioritize deeper layers
rather than discounting them. The exact 62-setting list, seeded ties, all six
relabelings, and all numeric limits are public in `FORMAT.md` and source.

## Embedding policies

Route a prefix using the fixed horizon-16/factor-0.9/ascending setting. Seek a
bounded hardware embedding of the remaining interaction graph. Physically route
tokens from the resulting prefix placement to that embedding, accounting for
every adjacent SWAP, and then execute the suffix natively. Keep the cheapest
complete feasible route found, including the ordinary routing incumbent.

The retained policy uses six early cuts. The added policy examines every fourth
gate boundary throughout the entire circuit, so its boundary range scales with
the supplied circuit rather than ending at a fixed prefix position. Both policies
use identical embedding and token-planning routines. Search visits, returned
embeddings, token expansions, and spanning-tree construction are explicitly
bounded and documented in `FORMAT.md` and `embedding.py`.

The new policy skips only candidates already unable to beat its incumbent:
prefix cost alone, or prefix cost plus the admissible half-total-hop-distance
lower bound. These are efficiency cuts, not instance-specific restrictions.

## Interpretation

The methods receive only demands, hardware, initial placement, and public settings;
they cannot read a submitted reference route or a private case library. Both sides
have the same fixed initial placement, SWAP-only operations, and free final
permutation. There is no free initial remapping. Initial-placement optimization,
CX bridges, algebraic circuit simplification, and native-gate cleanup remain out
of scope. The cheapest policy wins in each family, so retaining the older settings
prevents the enlarged portfolio from worsening its cost on any input.
