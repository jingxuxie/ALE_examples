# Trusted evaluation and isolation

From the concept root, evaluate a regular artifact with:

```
/usr/bin/python3 -B evaluator/evaluate.py /absolute/path/witness.json --output result.json
```

`--submission /absolute/path/witness.json` is also accepted. The evaluator runs
only trusted NumPy code; it never imports submitted code or the participant
checker, graph, or specification. `hidden/oracle.py` reconstructs the fixed graph
and constants independently. All 21 anchors use full-state nonnegative and
min-plus recurrences. There is no reference-witness dependency.

The participant sees ONLY a clean copy of `participant/`. Do not merely hide
private directory names in instructions while leaving sibling files readable.
In particular never bind the whole concept root, its parent, adversary files,
evaluator code, or attempts into a fresh coding environment. Run the trusted
evaluator afterward in a clean process, with trusted Python/NumPy and without
participant-controlled PYTHONPATH or module shadowing. The public checker is
editable for exploration, but edits cannot alter official evaluation.

Allow 3,600 seconds and 1 GiB for evaluation on the heavily loaded host; this is
independent of each fresh model's fixed one-hour wall budget. Do not introduce a
brief wall watchdog that mistakes scheduler delay for a failed artifact. A JSON
report's `passed` field, not process exit status, determines acceptance. Invalid
artifacts produce `valid:false`, `passed:false`, and score zero. Missing trusted
dependencies or internal unexpected exceptions are infrastructure errors, not
scientific failures. No runner is launched by this build.

`hidden/frozen_manifest.json` records the assets and thresholds frozen before any
fresh attempt. `adversary/audit.py` is a privileged audit and must remain private.
