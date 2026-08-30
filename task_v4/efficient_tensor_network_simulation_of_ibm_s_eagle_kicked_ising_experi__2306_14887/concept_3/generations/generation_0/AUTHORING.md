# Privileged builder handoff — not participant material

This is mode C, **WITNESS / DESIGN CONSTRUCTION**, not a fresh-agent run.
No model has been launched here. Main owns fresh-launch logging and final
hardness status. `status.json` records only the initial builder handoff.

## Isolation boundary

Expose **only** `participant/` and the fresh `attempts/v_1/` to the agent.
The participant package contains `TASK.md`, `input/`, `workspace/`, and
`baseline/`. Create a separate staged working directory; do not merely
tell an agent to avoid private paths in a shared readable tree. Do not expose
this file, `evaluator/`, `champions/`, `adversary/`, `attempts/`, `status.json`,
or `freeze_manifest.json`; the fresh attempt directory is the only exception
to withholding `attempts/`. In particular, the private numerical witness is
an immediate solution and MUST NOT be mounted into the fresh environment.
Run the trusted evaluator from an isolated unchanged copy, never from a
participant-modifiable evaluator directory.

The hidden suite is stored at `evaluator/hidden/scenarios.json`. The provided
public baseline submission is `participant/baseline/`; its runner is
`participant/baseline/run_baseline.py`. `attempts/v_1/` is reserved for main;
the builder neither launches an agent nor writes fresh results there.

The task gives public family/ranges and finite-suite composition, not the
hidden samples. The trusted checker imports neither workspace code nor
submission code and reads no participant problem/config files. Its scenario
hash is embedded in its source. `freeze_manifest.json` additionally fixes
the checker, scoring contract, public assets, and scenario bytes. Verify
the manifest before and after fresh evaluation. Do not regenerate scenarios,
change the target, or tune thresholds in response to a fresh result.

## Fixed scientific choice

The target remains **0.95 in all 63 scenarios**. Nominal ZZ exponent is
`+i*pi/4`; group gain errors extend to +/-2.5%, common bond errors to +/-1.5%,
and each edge residual to +/-0.5% (including +/-2% total bond stress).
There are exactly 24 alternating perfect-matching ZZ layers and two bounded
RX groups on the 12-cycle, initially `|+>^12`.

The split matching schedule is an explicit physical generalization of the
paper, required because a full simultaneous fixed-Clifford cycle has an
extra conserved sublattice parity. The audit verifies the resulting 1/2
upper bound for the unsplit GHZ problem and verifies its removal by the
matching schedule. The final witness establishes actual reachability,
not just absence of one symmetry obstruction.

## Reproduction and evidence

- `champions/builder_witness/pulses.json`: privileged optimized witness.
- `champions/builder_witness/evaluation.json`: independent full-suite score.
- `champions/private_search/`: single-thread C++ adjoint and SciPy search;
  no model/API calls. The optimizer's library is builder-only, not needed
  for checking or for the public baseline.
- `participant/baseline/`: runnable weak baseline and precomputed artifact.
- `attempts/baseline_nominal/`: private baseline evaluation evidence.
- `adversary/audit.py`: dense Kronecker gates, independent full-state circuit
  comparisons, invariants, and malformed-artifact rejection.
- `adversary/audit_report.json`: numerical audit evidence.
- `adversary/search_audit.json`: finite-difference adjoint and additional
  uncertainty-envelope spot checks, not a continuum certificate.
- `BUILD_REPORT.md`: measured scores, resources, and feasibility evidence.

Compile the builder optimizer, if needed, with `g++ -O3 -std=c++17 -fPIC
-shared champions/private_search/adjoint.cpp -o
champions/private_search/adjoint.so`. Run its two stages from the task root:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python champions/private_search/search.py --starts 3 --iterations 300 --global-kicks --scale 0.35 --seed 44 --label low_nominal
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python champions/private_search/search.py --starts 1 --iterations 450 --robust --resume champions/private_search/low_nominal_best.json --label low_robust
```

The first stage uses tied global controls only at the nominal calibration;
the second unties the two groups and optimizes a smooth minimum over
nominal plus eight common-channel corners. It does not optimize the 24
structured residual scenarios or 24 held-out disorder scenarios. The
passing artifact is then checked with independent exact contractions.
Numerical optimizer paths can vary by SciPy/compiler version; the saved
witness and trusted score are the feasibility certificate.

No claim that a fresh solver fails, or that the task is empirically hard,
has been made. This remains a hardness-discovery candidate with a failing
nominal-only baseline and an independently passing robust construction.
