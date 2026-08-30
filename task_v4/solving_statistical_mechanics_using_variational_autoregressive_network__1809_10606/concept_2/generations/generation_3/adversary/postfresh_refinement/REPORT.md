# Private post-fresh generation-3 refinement

A passing exact witness demonstrates attainability after the two completed fresh failures.

Official score: 1; valid: True; passed: True. The seven scientific gates and epsilon=0.01 are unchanged.
Best source: `extension/best/witness.json`. Canonical witness: `final_best/witness.json`. Official score: `final_best/official_report.json`.

## Exact metrics

| Metric | Measured | Required |
|---|---:|---:|
| Entropy | 4.04876964806 | >=3 |
| Reverse KL | 2.31184524299 | >=0.4 |
| Reward variance | 0.049955115306 | <=0.05 |
| Ambient gradient infinity | 0.00270527683869 | <=0.003 |
| Energy error/spin | 0.000205651319341 | <=0.02 |
| Target sector probability | 0.350536733639 | >=0.35 |
| Proposal sector probability | 0.000247698317941 | <=0.001 |

Failing gates: none. Minimum conditional probability: 0.0100000000001.

## Search and timing

The task began at 22:17:32 UTC on August 28, 2026. Source review, copying, and compilation preceded numerical search. The original conservative 22:37:00 cutoff was extended only to use the remainder of the explicitly authorized 20 minutes of search; the final hard cutoff was 22:43:25 UTC. Counting from five seconds before the numerical driver was created gives a conservative search-time upper bound of 998.6 seconds (within 20 minutes: True). Evidence finalization completed at 2026-08-28T22:40:30.020544+00:00 (1378.0 seconds of total wall time, including setup and reporting).
Completed refinements retained: 124. The static portfolio was intentionally interrupted at 22:31:36 UTC to allocate its cores to a distinct construction; `static_termination.json` lists 4 unfinalized inputs rather than treating them as completed failures.
The completed v2 README and final numerical checks were read before execution. Its actual native wrapper is `search.py`; no separate `fast.py` was present. Reviewed sources were copied byte-for-byte and the numerical C++ kernel rebuilt privately without fast-math.
Branches: fixed-order continuation; exact weighted logistic row refits after adjacent swaps and early insertion of formerly free spins; balanced binary-bond geometry changes; best-first compositions of successful order changes; saturated-parent reassignment; fixed-weight beta profiles; and exact two-root low-energy cluster initializations followed by unrestricted coupled row refinement.
The two-root construction enumerates backbone cuts whose broken-bond cost equals the free-spin field relief. Its initial phase odds include exact conditional free-spin partition factors, rather than assigning equal probabilities to disconnected modes. This is a search initialization, not an extra scientific gate or proof of feasibility.
The fixed-order v2 solve reproduced the original approximately 7.6% scientific deficit. Improvements from order changes are substantive; discrepancies at the 1e-12 level are not treated as resolution of the original failed gates.

## Validation and integrity

Copied-kernel checks: {'maximum_metric_error': 2.3447910280083306e-13, 'maximum_finite_difference_error': 3.968519309477175e-09, 'hessian_action_error': 1.0824674490095276e-15, 'passed': True}. All final acceptance decisions use the unmodified official full-enumeration evaluator, not the accelerated search score.
Frozen-file changes: []. Completed-v2 source changes: []. Copied sources byte-identical: True.
Frozen specification SHA256: `dd13c731a15fa61f8a2c3e92602de9671ad5e2c62c66f76d7cc47b06a46d618f`. Exact source and binary hashes are in `source_hashes.json`; original-source comparisons are in `source_provenance.json`.
No ongoing attempts were read, and no earlier generation, participant, evaluator, target, fresh submission, or main-controlled status was edited. Only this disjoint private directory was written.
Seeds, initial candidates, completed trial witnesses, independent reports, official record improvements, and stopping details are retained. These bounded searches do not establish global infeasibility and do not invalidate either previously solved generation.
