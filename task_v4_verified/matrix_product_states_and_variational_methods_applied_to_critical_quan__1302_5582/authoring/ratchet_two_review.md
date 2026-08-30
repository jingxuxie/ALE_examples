# Bounded independent A G2 review

**Verdict: no concrete blocking issue found. Final G2 freeze verified.**
Verification completed August 28, 2026, at 21:23:00 UTC. This is a static,
provenance and hash review, not a new numerical grade or hardness certification.

## Final bindings

- Launch freeze: `concept_1/adversary/ratchet_2_admission/freeze_manifest.json`,
  frozen at **2026-08-28 21:20:39 UTC**; SHA-256
  `b1d9c9deb0f1384ef816a85b224f6b6b21550132e2da6c25aaf5ebe6d6738ff6`.
- **51/51 asset pins match**, including all 24 retained states. The complete
  16-file public tree matches the freeze, without symlinks, special files,
  bytecode or caches. Calibration matches admission, independent validation
  and freeze hashes; case IDs, requests and families also agree.
- Calibration SHA-256:
  `e11ed03ca6ab38cf42c2afc61660793bcc8d0013e4bf22b52b64cf60ec5b2b14`.
  The bound validation report records eight cases and 24 remeasured states.
  **This reviewer did not repeat those contractions.**
- Runner, harness and freeze-builder hashes match. The planned ultima-alpha,
  high-effort, 3600-second v5/v6 declarations are checked as manifest data,
  **not actual new-run provenance**. No new attempt artifacts were read.

## Public contract and provenance

Baseline and workspace each contain the same four production Python files,
byte-identical to the archived passing v4 champion: `solve.py`, `fast.py`,
`optimizer.py`, `contractor.py`. The old `mps.py`, development logs, experimental
states and alternative solvers are absent. Imports are the released production
modules, standard library, NumPy and SciPy; no private construction dependency
is exposed. Three public examples have no optimization-objective overlap with
the eight private cases.

The new G2 contract explicitly narrows the previous domain to even/odd parity
and zero field, without changing N32–64, d8–14, cap12–24 or coefficient bounds.
All eight proposals are in-domain and distinct, including cap, local dimension
and sector in identity. Seven objectives match the tranche-three proposal;
the eighth is the N32 edge-preserving dimer. Four families contain two cases
each. All reference paths are regular, concept-contained and symlink-free.
This is a targeted suite, not uniform domain coverage: seven N64, one N32,
all d14, caps12/14, four even and four odd.

The scoring file is byte-identical to archived G1. Numeric targets match G0,
G1 and G2: **80 / core .80 / worst .70 / every long quality .55 / all16 valid**.
CPU6/40, worker wall30/120, 2GiB memory, 8MiB states and 16MiB submissions are
unchanged. The finite projected-power Hamiltonian contract is coherent; evaluator,
trusted contractor, suite, runner, worker and validator match archived G1 bytes.

## Admission and infrastructure

Completed report:
`concept_1/adversary/ratchet_2_admission/reports/57549ce569974ebdb0e5946732d62cde.json`.
All **16 cold stages** have complete source/request-bound checkpoints, matching
process/state hashes, accounted CPU, normal exit, and no timeout. All 16
baseline-reference gaps exceed `1e-7*N`; the smallest is **1.596531019e-5**.
Short CPU spans **2.627867–5.870169s**; long CPU **2.672048–20.255516s**.
Recorded baseline score/core/worst are zero, with all outputs valid. Zero is
expected for improvement measured against the baseline's own frozen outputs;
it is not itself a hardness result.

Static admission checks cover strict JSON/schema/bounds, duplicate/public
objectives, safe reference loading and measurement, fixed targets and budgets,
production and infra5 pins, source/request/environment-fingerprinted caches,
retained failures without automatic retry, both gap floors, and before/after
source/proposal/reference consistency. Publication preserves old cases and
calibration and rolls back on caught failure. The two JSON replacements are
not one atomic transaction: a crash between them is incomplete publication,
not launch-ready. The reviewed final pair and validation bindings are coherent.

The final freeze requires a valid calibration-bound 24-state validation report,
all immutable hashes, a clean public surface, no precreated fresh outputs,
unchanged archived solved G1 status and a new, non-overwritten manifest.
Infra5 has all **six certificate source pins matching** and records 15 passed
runtime checks. Fifteen admission mock-test methods are present and were
reported passing. Neither test set was rerun here. Prior resource/isolation
reviews and their historical cache/network qualifications remain unchanged.

## Interpretation and limits

These references are attainable same-cap states, not exact ground energies or
proof of a complete budget-feasible solver. Formal long baselines exit normally
well below 40 CPU seconds and remain energetically above references. For the
N32 completion, the recorded repeated champion energy is 19.90040480903323
versus v3's 19.900387111523973, a gap of 1.769750926e-5; search CPU was 3.238111s
and 2.403551s respectively. This supports an energetic optimizer shortfall,
consistent with a local minimum, not a demonstrated mechanism or hardness proof.
Larger-domain prospective controls are not part of G2.

`full_passing_algorithm_known_at_admission=false` is explicitly historical.
A later unchanged-v3 full-target grade may establish a complete passing program
without altering that admission fact or the target. This review does not certify
that no such program exists. The old parent-poll CPU event, underbudget SIGXCPU
and inconclusive 17.117624s anomaly are excluded from difficulty evidence.
The short CPU margin remains narrow and future resource anomalies require
separate assessment, not a scientific hardness inference.

**Only this Markdown file and `authoring/ratchet_two_review.json` are written.**
No numerical runs, tests, grades, launches, public/core/status/attempt edits,
old-report changes or v5/v6 artifact reads were performed. This is not an
extension of the accepted 13-run isolation audit to 15 runs.
