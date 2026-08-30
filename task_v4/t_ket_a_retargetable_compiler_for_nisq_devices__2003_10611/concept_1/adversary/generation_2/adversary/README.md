# Private generation-2 construction and audit

This directory, `evaluator/`, the root validation/freeze/status files, and all certificates are private. Deliver **only `participant/`** to a fresh solver. Its whitelist contains the unmodified original baseline, twelve public inputs and their reference scores, TASK, and FORMAT. It contains no champion, witness, generator, or search history.

Quality targets were fixed before construction at 0.40 core and 0.30 worst-family improvement. Before any generation-2 fresh launch, the user authorized only a resource adjustment to 12 seconds per case and 360 seconds per suite because of observed generation-1 host/startup timing variance. See `../targets.json`. Timing jitter is not the justification for generation 2.

## Coupled construction

Each case has nine active logical wires in one connected interaction graph, at least ten distinct interacting pairs, and vertices of interaction degree at least three. Six activity phases each involve four connected wires. Dominant phases shift between overlapping windows and regions; the final overlapping phases couple the regions and include paid physical exchanges that change the active logical interactions. These are not independent persistent pairs or two-token routing tasks.

The private constructor locates edge-disjoint calibrated regions and routes a nine-token partial placement using legal spanning-tree SWAP traces. It then emits coupled opaque gates and additional paid phase-transition SWAPs. This placement information is a private planting aid, not an input-only solver. Every operation is preserved; the initial placement is fixed; all SWAP work and depth are charged. All 48 private certificate routes must improve their original-baseline reference by at least 50%. Cases remain within the public n/gate/weight bounds.

The old champion's eager-closure mechanism incurs the costly initial activity before it can improve the suffix. The private construction records an analytical upper bound for that specific champion mechanism, but **the original unchanged champion is also executed on all 36 new hidden cases in the unchanged shared sandbox**. The quality gap, not runtime failure, justifies the ratchet. The existence of a full input-only solver meeting resources is not established by planted certificates.

## Reproduction

Run from generation_2:

```
PYTHONDONTWRITEBYTECODE=1 python3 -B adversary/generate.py
PYTHONDONTWRITEBYTECODE=1 python3 -B adversary/validate.py
PYTHONDONTWRITEBYTECODE=1 python3 -B evaluator/evaluate.py /path/to/submission --output /private/path/result.json
```

Do not regenerate a frozen dataset or change targets after launch. The freeze inventory binds all inputs, certificates, code, audit results, and public assets. `evaluator/evaluate.py` defines `G2ROOT = Path(__file__).resolve().parents[1]` and imports the shared sandbox from **`G2ROOT.parents[2] / "authoring"`**. The exact location and import are tested in validation.

`evaluator/hidden/certificates.json` holds each full input, witness route, and original-baseline route. `adversary/design.json` contains phase/placement-construction metadata and certificate margins. `validation.json` records exact route checks, structural coupling checks, negative checker tests, and the participant whitelist. `adversary/champion_audit.json` is the actual old-champion evaluation; external source/binary/sandbox hashes are in its provenance file. No fresh solver is launched by these scripts.
