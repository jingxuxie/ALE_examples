# Private phase-competition stress pool

This is a prospective audit pool, not generation 3 and not evidence that the ongoing A2 solver fails. No unfinished attempt or champion is read or executed. The immutable G2 participant/evaluator remain unchanged. Only this directory is written. The existing 0.40 core / 0.30 worst-family objectives and 12-second case / 360-second suite contract are not changed.

## Workload mechanism

Each candidate uses one of the six existing architecture families with random physical relabeling and a fixed random initial logical mapping. There are 240 opaque two-wire gates. Two connected source blocks contain five and four initially active wires on correlated high-cost edges (2.76--2.80). A nine-vertex path provides the calibrated low-cost region (0.45--0.47); all other edges cost 0.55--0.70. These are within the original bounds, not native uniform-weight objective floors.

Four 48-gate epochs alternate overlapping four-wire windows of those blocks. Each epoch evenly exercises all three edges of its connected four-wire interaction path. A paid cross-block exchange precedes a 12-gate coupling epoch, introducing additional cross-block interactions. A final 36-gate epoch brings three previously inactive wires into an already used four-vertex region together with an earlier active anchor. Incoming wires are selected from the region's reachable periphery, representing a changed active working set rather than independent pair traffic. Their placement is performed by explicitly paid legal SWAPs. Each incoming wire participates in at least twelve gates; none is added for a one-gate active-wire count trick.

There are exactly twelve active wires in one connected interaction graph, six connected four-wire epochs, and at least two nonempty inter-epoch placement changes. The last epoch reuses physical capacity occupied by earlier active wires. The only edges of weight at most 0.50 form a nine-vertex component: no single injective static placement can put the connected twelve-wire interaction graph entirely on those edges. This is a capacity proof of cheap-region competition, **not** a claim that a static-layout algorithm cannot meet the 40% target. Exact certificates, not a claimed lower bound or a timing failure, establish objective feasibility.

## Construction and acceptance

Private generation reuses the frozen G2 architecture/region helpers and 24-candidate weighted spanning-tree token-routing constructor. Initial nine-wire placement is paid. For late entry, four endpoint/anchor alternatives each receive a 24-route portfolio. The minimum paid-work late route is retained. The four-configuration original weak baseline is unchanged and evaluated exactly on the resulting input.

A case is accepted only after the original exact routing checker validates both complete routes and the certificate improves baseline cost by at least 50%. The cost includes every SWAP, every gate, and the original 0.05 depth term. Case bounds, connected twelve-wire traffic, equal per-edge epoch traffic, per-wire participation, low-cost capacity, and inter-epoch SWAPs are independently rechecked. This is generation-only witness construction, not an input-only resource-qualified solver.

The bounded search seeks four cases per family, with a 480-second substantive generation budget and at most 64 candidates per family. A partial pool is reported honestly if it cannot fill all slots; no acceptance threshold is lowered. `generation_report.json` records every seed, rejection, and accepted count. `manifest.json` contains original baseline costs keyed by case ID for main's later audit. The pool never executes a submitted solver.

## Assets and replay

- `cases.json`: private input-only cases using the unchanged interface.
- `certificates.json`: legal private route, original baseline route, and complete phase design for each case.
- `manifest.json`: costs, bounds/contracts, source hashes, and completeness.
- `validation.json`: exact costs and structural proof checks per case.
- `generation_report.json`: provenance, bounded search counts, and all candidate outcomes.
- `freeze.json`: private inventory hashes, frozen before any champion audit.

Run `PYTHONDONTWRITEBYTECODE=1 python3 -B validate.py` from this directory to independently recheck certificates, structure, source provenance, and inventory hashes. Only main should run a subsequent champion audit. These cases are not designated failures until such an audit supplies genuine quality evidence.
