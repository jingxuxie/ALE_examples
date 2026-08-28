# Ready for the fresh c01 pilot

- `attempt/` is completely empty. All author solvers, outputs, and historical
  logs are under `private/reference/`; none are participant-mounted.
- Evaluator uses the common `authoring/isolated_eval.py`, never imports a
  submission itself, supports `--participant DIR`, and requires host-side
  execution when nested sandbox namespace setup is prohibited.
- Final screening, 12/12 successful cases: strong `mean_core=1.0`,
  `worst_family=1.0`; weak `mean_core=0.5`, `worst_family=0.5`.
  Every family and both bottlenecks achieve those respective scores.
- Screening runtime: strong 2.085 seconds worker total / 108.660 seconds wall;
  weak 4.051 seconds worker total / 61.658 seconds wall. Namespace setup
  dominates wall time on this host. Strong peak RSS is 56,504 KiB.
- Strong challenge, 4/4: mean/worst 1.0, 0.759 seconds worker total /
  10.628 seconds wall. Author reports are in `validation/`; earlier
  infrastructure-affected runs are retained separately in `validation/pre_affinity/`.
- Independent checks pass: 16 revised-simplex endpoints, LM readout fits,
  primal/dual certificates, all 64 source-inequality states, and the exact
  marginal/XOR identifiability invariant. LP discrepancies are below 3e-16;
  independent fit discrepancy is below 3e-9. No fresh agent was run.
- Cases and references are precomputed: 12 screening, 4 challenge, 4 reserved
  confirmation, plus 4 unactivated source-grounded ratchet candidates.
  Confirmation has not been solver-evaluated. All split hashes were checked
  against `manifest.json` before handoff.
- Sources provide 20 real oscillatory tracks plus matched density data.
  Missing raw tomography observables mean these are conditional sharp bounds,
  not recovered true populations or a reproduction of the original precision.
  Full source and independence caveats are in `PROVENANCE.md`.

Frozen split SHA256:

```text
screening    fa74f92ed8b0b200ada270ca1b8bf9b70a51c0f76ed7a56cd538b87c09530cec
challenge    f453526cab0e837a1cb1673b57a1f6af8b7e9be8ec8094fd6a55e6963a59c9ff
confirmation 252817140dde8638f02802cc1a22c181a38ae44cbbda69cbdff85d35b5575e69
```
