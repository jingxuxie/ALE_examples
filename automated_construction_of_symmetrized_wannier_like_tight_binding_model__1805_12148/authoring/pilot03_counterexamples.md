# Pilot03 bounded natural-counterexample audit

## Decision

**No admissible natural counterexample found. Stop; do not build ratchet_1.** The valid initial03 solution already implements the requested rank-aware lead reduction, exact finite-device assembly, and channel-resolved multi-terminal transport. Four physically equivalent over-grouping probes with a resource-compliant official reference all pass essentially exactly. The two largest probes hit the unchanged official reference's own address-space limit before a valid answer is produced; they cannot be used as participant failures.

Under the parent's stated criterion, recommend rejecting pilot03 as a remaining hard candidate rather than forcing a new convention, tuned threshold, different model, or resource-ineligible case. This is a bounded negative result, not a proof of correctness for every imaginable device or energy.

Only the valid `pilots/03_device_transport/attempt/{solve.py,transport.py,leads.py}` and its specified initial03 reports were inspected. No archived/interrupted attempts, other pilots' attempts, or other concepts were inspected. No models/agents were launched.

## Actual valid method

Paths in this section are relative to `pilots/03_device_transport/`:

- `attempt/leads.py:85` selects the exact nonzero row/column support of the inter-layer hopping, factors that support, and uses its structural rank to reduce the factors further when possible. It is **not** a normal-path full `2*N` generalized-Schur solver.
- `attempt/leads.py:117` solves the full intra-layer Hermitian system against only the two reduced hopping factors, then constructs a `2*rank_bound` pencil. Increasing the group length increases the dense intra-layer solve, but not this reduced pencil's order.
- `attempt/leads.py:11` separates decaying Schur vectors and positive-current propagating modes, including current diagonalization within degenerate mode groups.
- `attempt/leads.py:163` checks the surface Dyson residual. `attempt/leads.py:146` provides a full-size pencil fallback for an inaccurate/singular compressed solve; `attempt/leads.py:170` uses it only after the compressed route raises or fails its residual check. No energy was tuned to manufacture this fallback or a hidden numerical-threshold failure.
- `attempt/transport.py:22` constructs actual long-range lead blocks from the supplied ordered geometric interfaces. `attempt/transport.py:46` restricts device contacts to the hopping-active orbitals.
- `attempt/transport.py:50` assembles the full finite crystal using sparse storage; `attempt/transport.py:152` factors its sparse open-device operator and `attempt/transport.py:155` solves channel-source batches, rather than forming a dense device inverse. The output is the full contact scattering matrix and its eigenchannel/noise observables, not a single universal transmission trace.

The measured support reduction is especially decisive:

| Lead | Enlarged orbital dimensions tested | Actual hopping rank | Submitted structural rank bound | Reduced pencil order |
| --- | --- | --- | --- | --- |
| Si longitudinal | 704, 1,152, 1,600 | 31 | 32 | 64 |
| InAs longitudinal, both directions | 728, 1,120, 1,568 | 62 | 62 | 124 |
| InAs third lead, unchanged | 224 | 94 | 96 | 192 |

These distinguish numerical rank from the submitted algorithm's structural upper bound. No claim is made that they are always identical.

## Source-grounded physical construction

The six probes use two of the existing, valid test systems: Si two-terminal `fbfba4b4d71a` and InAs three-terminal `8d04db336a4b`. Their device sizes remain **7,584 and 10,696 orbitals**, respectively. Both original energies per case, every full Wannier hopping, orbital position, crystal cell, device cell, onsite gate, and lead shift remain byte-identical as arrays.

Only `lead_cells_0`, `lead_cells_1`, `lead_period_0`, and `lead_period_1` change. Si groups contain 44, 72, or 100 longitudinal primitive cells; InAs groups contain 26, 40, or 56. Each longitudinal group retains the original two-cell narrow-wire transverse section. The InAs main direction remains the original oblique `[1,1,0]` direction, and its genuine third contact is unchanged. There are no synthetic hopping matrices, extra vacuum orbitals, new material fits, cropped ranges, randomized edge cases, energy shifts, or silent device-size reductions.

For the left contact, the interface group spans the first `P` device cells and its period is `-P` along the same wire direction. The union of exterior translated groups is exactly the original semi-infinite negative wire. The right contact analogously covers exactly the original positive exterior wire. Therefore the regrouping does not add, remove, or change a physical exterior site or bond; it only changes the periodic cell representation. Device gates are not reset when an interface becomes larger.

The generator checks interface membership, disjointness, all exterior-to-device couplings, and absence of beyond-neighbor grouped-layer hopping. It also checks that the numerical hopping rank remains fixed. For each successful official computation, it compares mode counts, transmission, eigenchannels, noise, conductance, and the correctly embedded selfenergy against the original official reference. Added selfenergy rows/columns outside the old interface are checked as zero. Maximum regrouping-equivalence discrepancy across all four admissible probes is **4.53e-8**, below the unchanged scientific consistency checks; no score tolerance was relaxed.

The source models remain the official TBmodels checkout at `39d7eb096d809137373774ef6ba337fdf36349bc`: `tests/samples/cli_eigenvals/silicon_model.hdf5` (8 orbitals, 189 full directed translations) and `tests/samples/InAs_sym_reference.hdf5` (14 orbitals, 501 full directed translations). Exact original/probe input hashes, submitted source hashes, and installed official lead-source hash are recorded in the private probe records.

## Measured results

All runs use the unchanged **90-second wall-time / 1,024 MiB address-space limit** and one BLAS thread. Submitted runs use the parent's bwrap helper, with only the current participant tree, the valid attempt, one input NPZ, and its output directory mounted. Author reference runs use the existing unchanged official Kwant 1.5.0 `smatrix` oracle under the same resource cap. No private packages are exposed to the submission.

| Probe | Lead dimensions | Official seconds / peak MiB | Submitted seconds / peak MiB | Submitted score | Admissible counter? |
| --- | --- | --- | --- | --- | --- |
| Si, P=44 | 704, 704 | 7.295 / 213.28 | 1.148 / 107.08 | 0.9999999999976212 | No; passes |
| InAs, P=26 | 728, 728, 224 | 6.242 / 296.89 | 2.719 / 154.24 | 0.9999999997782202 | No; passes |
| Si, P=72 | 1,152, 1,152 | 19.713 / 445.07 | 4.232 / 138.92 | 0.9999999999947632 | No; passes |
| InAs, P=40 | 1,120, 1,120, 224 | 17.572 / 450.39 | 3.723 / 196.16 | 0.9999999977626134 | No; passes |
| Si, P=100 | 1,600, 1,600 | 17.264 / 558.25, failed | Not run: reference ineligible | Not graded | No valid capped reference |
| InAs, P=56 | 1,568, 1,568, 224 | 10.569 / 592.31, failed | Not run: reference ineligible | Not graded | No valid capped reference |

On admissible probes, official scattering unitarity error is at most `1.30e-12`, current-conservation error at most `9.13e-14`, and surface Dyson relative residual at most `4.93e-10`; causal broadening checks pass. The two-terminal noise agrees with official Kwant's noise routine within `4.88e-14`. Every submitted execution on these probes exits successfully. Scoring uses the existing post-audit nonsaturating evaluator, without changing cases, weights, or calibration.

The upper two failures are **oracle-side full-SVD workspace allocations**, not a submitted-solver failure and not evidence of a full `2*N` QZ in Kwant. `private/reference/vendor/kwant/physics/leads.py:260` calls `scipy.linalg.svd(h_hop)` before the singular-value reduction. Under the address-space cap, SciPy cannot allocate approximately 97.7 MiB (Si) or 93.9 MiB (InAs) of additional real workspace. The trace subsequently includes an exception-construction `TypeError`; the preceding `_ArrayMemoryError` and allocation dimensions identify the underlying resource failure. RSS below 1,024 MiB does not contradict an address-space-limit failure: the limit also covers mapped/reserved virtual space. The cap was not increased, and no alternate optimized oracle was invented to force retention of these sizes.

## Official implementation basis

- <https://kwant-project.org/doc/1/reference/generated/kwant.physics.modes>
- <https://kwant-project.org/doc/1/reference/generated/kwant.physics.StabilizedModes>
- Installed exact source: `pilots/03_device_transport/private/reference/vendor/kwant/physics/leads.py:200`. Its singular-value decomposition determines the nonsingular hopping subspace, and lines beginning at `:345` construct the reduced pencil. This agrees with the official stabilized-mode documentation's singular-hopping basis.
- Original source data: <https://github.com/Z2PackDev/TBmodels/tree/39d7eb096d809137373774ef6ba337fdf36349bc/tests/samples>.

The current submitted solver independently implements an analogous support-aware reduction. The intended stress therefore does not reveal a missing second computational bottleneck; its real-space construction and rank-aware transport are both working on these material-backed cases.

## Artifacts, fidelity, and stopping rule

New artifacts are confined to `pilots/03_device_transport/private/reference/overgroup_probes/` and this note. The directory contains `probe.py`, `summary.json`, and six probe subdirectories, each with the self-contained `input.npz` and `report.json`; successful official/submitted computations additionally have their `official/result.npz` and `submitted/result.npz`. Invalid-reference probes are expressly marked ineligible, not counted as participant failures or retained challenge cases.

The current participant bundle and valid submitted source hashes were checked unchanged across this search. A pre-existing difference between the initial freeze manifest and the current `participant/workspace/SCHEMA.md` was recorded, not reverted or edited; all other initial participant file hashes match. Current participant hashes are separately stored. No scored input/reference, public file, evaluator, baseline, initial report, or participant implementation was modified.

The fixed six-point grid is exhausted. No follow-up random search, exact mode-threshold tuning, isolated-cell resonance targeting, alternative convention, or confirmation-candidate run was performed. No meaningful region was found, so there are **no retained counterexamples, no fresh ratchet heldouts, and no ratchet_1 directory**. The conditional requirement to mount a bounds-checked sibling ratchet participant is therefore not activated; the evaluator was left untouched.

From the task root, the cached, source-hash-checked audit is reproducible with:

```bash
P=pilots/03_device_transport
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python "$P/private/reference/overgroup_probes/probe.py"
```

When execution is needed, use approved escalation if the outer sandbox prevents the helper's bwrap namespaces; bwrap remains enabled for submitted execution. The driver refuses to reuse completed probe records for changed submitted source.
