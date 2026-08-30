# Hardness discovery

## Concepts and verification modes

| Concept | Verification mode | Final generation | Status |
|---|---|---|---|
| Reliable compact equilibrium proposals | A: baseline improvement | concept_1/generations/generation_3 | solved |
| Full-support false convergence | B: counterexample/falsification | concept_2/generations/generation_3 | hard_verified_achievable |
| Hidden-spin material response | D: hidden prediction | concept_3/generations/generation_2 | hard_verified_achievable |

## Baseline, champion, and fresh-agent scores

All scientific attempts use isolated ultima-alpha sessions with a 3,600-second limit.

9 scientific attempts are scored. One pre-session infrastructure failure is excluded from hardness evidence.

| Concept / generation | Baseline or incoming champion | Fresh attempt | Fresh score | Decision |
|---|---|---|---|---|
| concept_1 | KL 0.0169707; worst-family 0.0281047; min ESS 0.0429275 | v_2 | KL 0.00219742; worst-family 0.00360446; min ESS 0.973918 | solved |
| concept_1/generations/generation_2 | KL 0.107321; worst-family 0.137164; min ESS 0.809858 | v_1 | KL 0.00321653; worst-family 0.00637904; min ESS 0.859169 | solved |
| concept_1/generations/generation_3 | KL 1.92157; worst-family 5.68081; min ESS 0.300209 | v_1 | KL 0.000953251; worst-family 0.00280831; min ESS 0.860456 | solved |
| concept_1/generations/generation_3 private control | KL 0.00199906; worst-family 0.004396; min ESS 0.520555 | — | — | passing control |
| concept_2 | gate-score 0.0015625; variance 32; gradient 0.5 | v_1 | gate-score 1; variance 0.0169945; gradient 0.000484875 | solved |
| concept_2/generations/generation_2 | gate-score 0.247729; variance 0.201834; gradient 0.0047936 | v_1 | gate-score 1; variance 0.00844492; gradient 0.00081204 | solved |
| concept_2/generations/generation_3 | gate-score 0.0574925; variance 0.869679; gradient 0.0280587 | v_1 | gate-score 0.789486; variance 0.0633323; gradient 0.00379994 | hard_verified_achievable |
| concept_2/generations/generation_3 | gate-score 0.0574925; variance 0.869679; gradient 0.0280587 | v_2 | gate-score 0.929155; variance 0.0538123; gradient 0.00322874 | hard_verified_achievable |
| concept_2/generations/generation_3 private control | gate-score 1; variance 0.0499551; gradient 0.00270528 | — | — | passing control |
| concept_3 | KL 0.0646614; worst-family 0.0770856; max TV 0.217534 | v_1 | KL 0.000673266; worst-family 0.000800691; max TV 0.0240848 | solved |
| concept_3/generations/generation_2 | KL 0.0245595; worst-family 0.0412088; max TV 0.395827 | v_1 | KL 0.0309514; worst-family 0.0523531; max TV 0.464495 | hard_verified_achievable |
| concept_3/generations/generation_2 private control | KL 0.00733559; worst-family 0.00738499; max TV 0.0726507 | — | — | passing control |

## Counterexample search results

- Concept 1: The initial champion passes 32 ordinary stress cases but fails 2/12 modular cases (peak KL 0.16373). Generation2 passes the unchanged-source official replay; its initial single timeout does not reproduce in two case repeats and earns no hardness credit. Its 36-case connected-material audit finds three KL gaps above 0.04, including a cold-cycle KL of 16.5691. Generation3 combines these failures with retained local-sector controls; the new fresh agent passes, mean KL 0.00095325 / worst-family 0.00280831 / minimum ESS 0.86046. Its final 32-case broad audit has no failures, worst KL 0.00227353 and minimum ESS 0.99542. The official report retains a 120.004-second measurement and zero auxiliary runtime headroom score on one case: the timer includes Popen setup, whereas the hard wait deadline starts afterward. Two unchanged-source repeats run in 113.27 and 112.80 seconds; no evaluator gate or official score is changed.
- Concept 2: The 0.0001 and 0.001 generations are solved; scalar and coupled robustness audits motivate the unchanged seven gates at 0.01. Both one-hour fresh attempts fail. An initial 50-report private portfolio fails; 124 post-fresh refinements then find variance0.0499551153, gradient0.00270527684, all seven gates passing under independent official reevaluation.
- Concept 3: The initial prediction task is solved. A 120-query broad audit is followed by all 48 preregistered cold queries; the source-faithful predecessor replay (not bitwise identical to the archived original fit) fails with full 9600-draw max TV 0.39583. Independent dense transfer verifies every cold label. The new fresh attempt also fails all three targets. Ten public-data fitting controls fail; privileged hidden-score selection among 1024 frozen global posterior-draw mixtures finds 16 passing artifacts, best mean KL 0.0073356 / worst-family 0.0073850 / max TV 0.072651. Independent label-free reconstruction from two fitted parameter vectors reproduces the passing artifact within 2.6e-15. No blind statistical-identifiability claim is made.

## Ratchet generations

- Concept 1: 2 ratchets after the initial tournament.
- Concept 2: 2 ratchets after the initial tournament.
- Concept 3: 1 ratchet after the initial tournament.

## Final status

- Status: `hard_verified_achievable`.
- Selected task: `concept_2/generations/generation_3`.
- Solvability: demonstrated.

## Substantive capability

- Concept 1: The final fresh agent closes the compact-proposal accuracy and tail-coverage gap across cold cycles, coupled regions, and local sectors. It meets every frozen scientific target; no surviving hardness is claimed for mode A.
- Concept 2: Both independent fresh agents fail the simultaneous exact witness conditions at 1% exploration. The best misses variance and gradient by 7.62%; privileged order/initialization search subsequently constructs a passing full-support witness without changing any gate.
- Concept 3: The fresh agent fails calibrated cold extrapolation from partially observed warm-equilibrium data: mean KL 0.03095, worst-family KL 0.05235, and max TV 0.46450 exceed all fixed targets. Achievability is demonstrated only by organizer-assisted selection of one global physical-model mixture from a frozen public-data-fitted portfolio, not by a blind identifiability guarantee.
