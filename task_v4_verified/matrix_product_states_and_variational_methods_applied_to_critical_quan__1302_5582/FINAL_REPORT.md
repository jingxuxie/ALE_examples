# Hardness-discovery outcome

| Concept | Verification mode | Baseline / private solver | Fresh-agent scores | Ratchets | Final status |
| --- | --- | --- | --- | --- | --- |
| Robust parity-constrained phi4 MPS optimization | A: baseline improvement | Frozen baseline 0/100; private full solver 89.586281/100 | v5 42.443832/100; v6 37.021653/100 | 2 | hard_verified_achievable |
| Multiscale critical-vacuum tensor witness | C: witness construction | Final-generation baseline core 0.677944/1 | v7 and v8 core 1/1; all eight fresh attempts pass their generations | 3 | solved |
| Finite-chain spectral prediction | D: hidden prediction | Baseline 0.085936331/1 | v1 0.999999997059/1 | 0 | solved |

## Baseline and champion history

- A generation 0: corrected intended-accounting fresh scores 99.695453 and 99.776331, both passing. Generation 1: v3 87.316574, all quality gates met but two short resource failures; v4 94.505564, passing. These earlier resource episodes are not hardness evidence.
- C final challenger v8 has maximum three-interval relative error 0.041949 against the fixed 0.10 limit; the preceding champion has error 1.029998 on the ratcheted target.
- D champion remains passing on 360 independently certified private challenges, pooled score approximately 0.999999999155/1.

## Counterexample search results

- A: eight repeated same-cap energy failures across four physical families were admitted. Fresh v5 and v6 each fail four of eight long-quality gates, concentrated in competing edge-island odd states and quartic-interface even states. All 16 outputs per submission are valid; maximum long CPU is 22.805s and 20.917s against 40s.
- C: private searches expose long-distance correlation failures, connected four-spin errors, and a wrong-sign connected six-spin moment. Fresh challengers solve every resulting generation; the three-ratchet limit is exhausted without a retained hard witness task.
- D: no failure on 360 certified in-domain cases. Prospective larger-chain probes are outside the frozen prediction task and are not counted as failures.

## Final status and solvability

- Retain concept_1 as **hard_verified_achievable**. Both fresh attempts finish voluntarily within one hour and miss the fixed score >=80, core >=0.80 and worst-family >=0.70 targets substantially: cores 0.555972/0.476200; worst families 0.066284/0.068904.
- Solvability is **demonstrated**, not inferred from reference tensors: an unchanged historical solver, withheld from the current challengers, passes all 16 frozen runs with core 0.909445, worst family 0.875000, and every long quality equal to 1. No exact ground-energy or global-optimality claim is made.
- Substantive capability failed: Robust low-energy variational search across virtual-parity allocations in nonuniform finite-cap MPS. Both fresh implementations add local allocation searches but retain higher-energy edge-island and quartic-interface states; each fails four long-budget quality gates with every output valid. The same-cap private solver attains all long-quality targets.
