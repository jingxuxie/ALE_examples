# Hardness decision

**Selected: concept_2 — hard_verified_achievable.** Solvability is demonstrated
by a private artifact. All fresh runs use `ultima-alpha` with a one-hour limit.
Scores below are core / worst-family; scales differ between concepts.

| Concept and primary mode | Baseline | Initial fresh champion | Final qualifying fresh | Final status | Ratchets |
|---|---:|---:|---:|---|---:|
| Robust rare-sign Hubbard witness — B, counterexample | 0 / 0 | 1 / 1 at beta=1.6 | 0 / 0 at beta=0.75 | hard_open_candidate | 1 |
| Positive checkerboard schedule — C, design construction | 1 / 1 | 2.9776 / 2.6003 | 2.1044 / 1.6825 | hard_verified_achievable | 1 |
| Fermionic spectral reconstruction — D, hidden prediction | 75.2339 / 48.7355 | 95.7608 / 87.2427 | 95.7608 / 87.2427 | solved | 0 |

## Champion and counterexample searches

- **Sign:** 1,632 parameter cells invalidate the original fixed witness in 1,533
  cells. A 597,504-case structured search finds no beta=0.75 witness; broader
  private continuation certifies beta=0.786, not the target. The clean fresh
  artifact is valid but positive at all three certification points. All 20
  distinct saved discrete candidates are nominally positive at 65/95 digits.
  Target solvability remains **unknown**; no nonexistence claim is made.
- **Schedule:** 7,680 independent cases and 1,108 controlled configurations expose
  genuine finite-step regressions, including a 1.5328x error ratio confirmed at
  70 digits. The old champion on the ratcheted target scores 2.0250 / 1.5158,
  but its maximum error ratio is 1.3627. The new fresh submission scores well
  in aggregate but has a **1.1701565** maximum ratio, failing the frozen <=1.00
  no-regression gate. Its worst-point failure is independently reproduced at
  70 digits. A private 65-word search produces **1.801879 / 1.372175**, maximum
  ratio **0.9812035**, passing every frozen gate. Solvability is **demonstrated**.
- **Prediction:** The final champion uses 76.35 of the allowed 120 seconds on the
  official batch. A further 448-case final-code audit includes two independent
  balanced batches scoring 95.8779 / 88.2034 and 95.9744 / 89.7548, plus 64
  conditional confirmations. No substantial final-champion failure survives;
  no new generation is justified. Solvability is **demonstrated**.

## Substantive failures

The retained design task defeats simultaneous control of aggregate accuracy,
family accuracy, and worst-case finite-step Green-function error under a fixed
positive 33-stage work budget. The open sign task defeats rare correlated-field
search, not JSON formatting. One champion-assisted sign control is excluded;
the reported final sign score comes from the clean retest. All five qualifying
attempts match their exit/deadline submission hashes.
