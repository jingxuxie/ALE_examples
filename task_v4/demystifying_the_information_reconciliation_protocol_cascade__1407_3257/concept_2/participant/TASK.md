# Audit fixed-shuffle reconciliation reliability

A deployment of Cascade uses fixed interleavers for reproducible low-latency
operation. Audit its claim that sparse discrepancies cannot survive an activated
reconciliation run. This is a worst-case deployment audit, not a claim about
the failure probability of independently randomized Cascade.

`input/deployment.json` contains the complete six-pass deployment: 8,192 positions
and 128-bit top-level blocks. The readable simulator in `workspace/replay.py`
defines two supported correction priorities.
`workspace/INTERFACE.md` specifies the replay contract. `baseline/solve.py` is a
runnable unsuccessful witness search, not a required method.

Submit `witness.json` containing `{"errors": [distinct zero-based bit positions]}`.
Your single discrepancy set must have between 1 and 24 bits. For **both**
`earliest` and `shortest` priorities, at least six bits must be corrected and
at least eight must remain after every pass has finished. At least six first-pass
top-level blocks must initially have odd discrepancy parity. All conditions are
mandatory; there is no credit for a malformed artifact or a different deployment.

You have one hour, may use installed offline tools, and may keep working files
in your writable output directory. The final JSON must be at most 64 KiB.
The checker independently replays the protocol, reports surviving errors,
corrections, initial activation and runtime, and accepts only a genuine witness.

Local replay: `python3 workspace/replay.py --deployment input/deployment.json --witness /path/to/witness.json`.
Baseline: `python3 baseline/solve.py --input input/deployment.json --output /path/to/witness.json`.
