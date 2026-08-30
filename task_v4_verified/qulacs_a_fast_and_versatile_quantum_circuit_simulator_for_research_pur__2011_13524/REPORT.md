# Empirical hardness decision

**Selected task: `concept_2`, compact full-unitary circuit construction —
`hard_verified_achievable`.**

## Concepts, modes, and scores

| Concept | Primary mode | Baseline / privileged score | Fresh-agent score | Ratchet generations | Final status |
| --- | --- | --- | --- | --- | --- |
| Structure-aware fusion planning | A: baseline improvement | Baseline 1.0000x; private portfolio 1.0013x | 1.1547x aggregate, 1.1083x worst family; target 1.20x / 0.98x | 0 | `hard_open_candidate` |
| Compact inverse unitary compilation | C: witness construction | Identity baseline 0/2; independently verified private witnesses 2/2 | Initial generation 2/2; first ratchet 2/2; second ratchet **0/2** | 2 | `hard_verified_achievable` |
| Budgeted correlated-noise calibration | E: active experiment design | Baseline 82.2066 / 76.8988; private policy 89.1251 / 86.8465 | Champion 90.8469 / 90.5923; target 88 / 85 | 0 | `solved` |

Fusion scores are modeled speedups, not measured Qulacs wall-time improvements.
Calibration pairs are aggregate / worst-family scores on a 0–100 scale.
Compilation generations have different, explicitly frozen public operators;
the earlier champions score 1.0 on their own archived generations.

Five isolated `ultima-alpha` attempts ran, each with a 3,600-second limit.
The final compilation attempt finished in 3,210.759 seconds without timing out.
Its executable is valid and resource-compliant, taking 13.787563 seconds to
evaluate, but both full-operator comparisons fail:

| Target | Legal gate counts | Infidelity | Normalized Frobenius discrepancy |
| --- | --- | --- | --- |
| Seven qubits | 60 CNOT, 127 U3 | 0.8562823463 | 1.1143598048 |
| Eight qubits | 80 CNOT, 168 U3 | 0.9845303913 | 1.3233466049 |

Required maxima are `1e-8` and `2e-4`, respectively. The fusion submission is
also legal, running in 176.851 seconds of its 180-second budget.

## Counterexample and adversarial searches

- **Fusion:** six private search variants over 25 cases, totaling 150 runs,
  produce a best casewise portfolio score of 1.0013214875x. No passing
  implementation is known; the fresh agent is substantially stronger than
  this private portfolio but still misses the fixed 20% improvement target.
- **Compilation:** a 24-case first pool and an eight-case second pool expose
  progressively stronger operator coupling. Bounded historical-gradient
  portfolio probes pass 0/24 and 0/8 cases. These are generation-time probes,
  not additional fresh attempts or exact replays of the latest champion's
  discarded research scripts. Failure of a hardcoded witness on unrelated
  input matrices is never counted as hardness evidence.
- The second compilation pool has eight independently valid private witnesses;
  five satisfy the fixed structural filters. The selected seven- and eight-qubit
  cases remove sparse causal and low-effective-rank shortcuts. Their witnesses
  pass the same full-operator checker with score 1.0; the new fresh agent scores
  0.0 on these exact, public targets.
- **Calibration:** 138 additional private outcomes cover 36 latent configurations,
  including screening, untouched confirmation outcomes, and a 12-outcome
  recheck. The selected balanced cohort confirms at 91.8516 aggregate and
  89.7171 worst family. The initially weakest configuration recovers to
  89.4622 on new outcomes. No reproducible aggregate failure is found, so no
  stochastic-outcome cherry-picking ratchet is installed.

## Solvability and failed capabilities

- **Compilation: demonstrated solvability.** Independently reconstructed private
  witnesses meet all gate, numerical, and resource conditions. The fresh agent
  fails at joint discrete-topology and continuous-angle inverse synthesis for
  strongly mixed operators, not at formatting, execution, legality, or isolation.
- **Fusion: solvability unknown.** The agent finds a 15.47% modeled gain rather
  than the required 20%. The remaining gap concerns global scheduling quality
  across circuit families under the planning budget.
- **Calibration: solved and not retained as hard.** The champion meets the
  original target and survives the private aggregate stress tests; no failed
  capability is claimed for this concept.
