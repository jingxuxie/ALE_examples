# Private champion stress search — August 28, 2026

## Outcome

**Recommendation: solved, no justified champion ratchet.** This relies on the
main-audited generation-1 fresh pass plus the limited negative evidence here; it
is not a universal guarantee of optimality. No target, public asset, evaluator,
champion, or status file was changed. No fresh agent was launched.

The broad sweep screens 128 cases in eight families; the focused sweep adds 32
cases in four families. All 160 inputs satisfy the original exact schema,
including a in [0.02,5], individual poles in [1e-6,10000], degrees 2–48,
2–6 scenarios and at most 24 poles per scenario. Multiplicities, damping, pole
count and near/far cluster scales vary. No unsupported scalar domain is used.

There are **13 oracle-confirmed case pairs / 26 numerical enclosures**, and
**147 triage-only cases**. There are no verified regressions, invalid champion
outputs, or unresolved selected oracle checks. This distinction is important:
sampled bounds alone do not certify that the other 147 cases have no regression.
Peak diagnostics cover all 160 outputs and find no significant underestimate
relative to the independent sampling grid; this is also not a global certificate.

## Strongest coherent stress family

Six uncertain prefactors with 24 coincident near-origin poles, degree 48 and small
damping create a large separation between boundary and tail node scales. Two
members (`six_scenario_boundary_04` and `_12`) reach the champion's internal
5.8-second refinement limit. Nevertheless, independently enclosed ratios of
champion amplification to baseline amplification are respectively
[0.6885394315,0.6886430384] and [0.6836474231,0.6837518365]. Thus this is a real
runtime stress regime but **not a numerical failure**: the champion still reduces
amplification by roughly 31%. These cases are optional isolated audit inputs, not
proposed generation-2 failure cases.

More antagonistic crossing pole models and dense logarithmic pole ladders can
produce enormous absolute amplification even when the champion dramatically
improves over baseline. Those supported-domain cases are retained in the full
generated datasets rather than silently excluded. A large absolute value alone
does not establish a relative-baseline failure. The closest low-degree case
improves by only approximately 1.7%; tightening thresholds around a nearly
unit-amplification baseline would not demonstrate a meaningful optimizer defect.

## Evidence and reproduction

`handoff.json` is the compact machine-readable root-report handoff.
`final_summary.json` includes the selected exact oracle return objects.
`outcomes/*.json` stores nodes, input, measured imported-function CPU/wall times,
sampled lower estimates and numerical enclosures for both implementations.
`cases/*.json` contains the matching standalone schema-valid inputs.
All other screened inputs and outputs are retained in the two JSONL files;
`generated_cases.json` and `focused_cases.json` retain the reproducible generators'
complete output. `changed_paths.txt` enumerates every changed path.

From the concept root, with the original inspected sources in place:

```
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B adversary/champion_search/sweep.py --wall-seconds 440 --cpu-seconds 240
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B adversary/champion_search/focus.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B adversary/champion_search/peak_audit.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B adversary/champion_search/finalize.py
```

Seeds and source hashes are recorded. CPU-timed optimizers can vary slightly
between runs; saved concrete nodes and enclosures preserve the observed evidence.
The numerical oracle is the existing independent evaluator, unchanged. Its bound
objects are saved verbatim, but they are floating-point enclosures with
high-precision witness checks, not exact arithmetic certificates.

The submitted source was inspected before importing only its computational
functions, as explicitly authorized for privileged generation. Full candidate
executables were not run unrestricted. Imported timings exclude Python startup;
the main worker may perform authoritative isolated selected-case grading through
the corrected supervisor. No failure, resource breach, or hardness claim is based
solely on these imported timing measurements.
